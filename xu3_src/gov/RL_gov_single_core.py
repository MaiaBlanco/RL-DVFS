import numpy as np
import multiprocessing as mp
import subprocess, os, sys
import ctypes
import time
import random
import atexit
from collections import deque

# Local imports:
import sysfs_paths_xu3 as sfs
import devfreq_utils_xu3 as dvfs
from state_space_params_xu3_single_core import *
from state_space_params_xu3_single_core import freq_to_bucket

# TODO: resolve redundant frequency in action and state space
# Idea: make action space only five choices: go up 1 or 2 or go down 1 or 2?
num_buckets = np.array([BUCKETS[k] for k in LABELS], dtype=np.double)
if FREQ_IN_STATE:
	dims = [int(b) for b in num_buckets] + [FREQS] + [ACTIONS]  
else:
	dims = [int(b) for b in num_buckets] + [ACTIONS]
print(dims)
Q = np.zeros( dims ) 
# Note: C is no longer used to keep track of exact counts, but if a state action has been seen ever.
C = np.zeros( dims ) 
# For bucketing stats:
all_mins = np.array([MINS[k] for k in LABELS], dtype=np.double)
all_maxs = np.array([MAXS[k] for k in LABELS], dtype=np.double)
scaled_bounds = [(np.log(x), np.log(y)) if s else (x,y) for x,y,s in zip(all_mins, all_maxs, SCALING)]
scaled_mins, scaled_maxs = zip(*scaled_bounds)
scaled_widths = np.divide( np.array(scaled_maxs) - np.array(scaled_mins), num_buckets)

def checkpoint_statespace():
	global Q
	yn = str(raw_input("Save statespace? (y/n)") ).lower()
	while yn != 'y' and yn != 'n':
		yn = str(raw_input("Enter y/n: ")).lower()
	if yn == 'n':
		return
	ms_period = int(PERIOD*1000)
	np.save("Q_{}ms.npy".format(ms_period), Q)
	#np.save("C_{}ms.npy".format(ms_period), C)

def load_statespace():
	global Q, C
	ms_period = int(PERIOD*1000)
	try:
		Q_t = np.load("Q_{}ms.npy".format(ms_period))
		#C_t = np.load("C_{}ms.npy".format(ms_period))
	except:
		raise Exception("Could not read previous statespace")
		return
	Q = Q_t
	#C = C_t

# XU3 has built-in sensors, so use them:
def get_power():
	# Just return big cluster power:
	return dvfs.getPowerComponents()[0]

def init():
	# Make sure perf counter module is loaded:
	process = subprocess.Popen(['lsmod'], stdout=subprocess.PIPE)
	output, err = process.communicate()
	loaded = "perfmod" in output
	if not loaded:
		print("WARNING: perf-counters module not loaded. Loading...")
		process = subprocess.Popen(['sudo', 'insmod', 'perfmod.ko'])
		output, err = process.communicate()
	ms_period = int(PERIOD*1000)
	print("Running with period: {} ms".format(ms_period))
	set_period(ms_period)

def get_counter_value(cpu_num, attr_name):
	with open("/sys/kernel/performance_counters/cpu{}/{}".format(cpu_num, attr_name), 
				'r') as f:
		val = float(f.readline().strip())
	return val

def set_period(p):
	cpu_num = 4
	with open("/sys/kernel/performance_counters/cpu{}/sample_period_ms".format(cpu_num), 
				'w') as f:
		f.write("{}\n".format(p))

'''
Returns state figures, non-quantized.
Includes branch misses per Kinstruction, IPC, and l2miss, data memory accesses 
per Kinstruction for each core, plus core temp and big cluster power. 
(BMPKI, IPC, CMPKI, DAPKI, celsius, watts, frequency)
TODO: add leakage power?
TODO: add thermal predictions?
'''
def get_raw_state():	
	# Get the change in counter values:
	cpu = 4
		
	cpu_freq = dvfs.getClusterFreq(cpu)
	# Multiply by period and frequency by 1000 to get total
	# possible cpu cycles.
	cycles_possible = int(cpu_freq * 1000 *  PERIOD)
	cycles_used = get_counter_value(cpu, "cycles")
	bmisses = get_counter_value(cpu, "branch_mispredictions")
	instructions = get_counter_value(cpu, "instructions_retired")
	l2misses = get_counter_value(cpu, "l2_data_refills")
	dmemaccesses = get_counter_value(cpu, "data_memory_accesses")
	T = [float(x) for x in dvfs.getTemps()]
	P = get_power()
	# Throughput stats:
	IPC_u = instructions / cycles_used
	IPC_p = instructions / cycles_possible
	IPS   =	instructions / PERIOD
	MPKI  = l2misses / (instructions / 1000.0)
	BMPKI = bmisses / (instructions / 1000.0)
	DAPKI = dmemaccesses / (instructions / 1000.0)
	# Collect all possible state:
	all_stats = {
		'BMPKI':BMPKI, 
		'IPC_u':IPC_u, 
		'IPC_p':IPC_p, 
		'MPKI' :MPKI, 
		'DAPKI':DAPKI,
		'temp' :T[4], 
		'power':P,
		'freq' :cpu_freq,
		'usage':cycles_used/cycles_possible,
		'IPS'  :IPS
		}
	return all_stats

'''
Place state in 'bucket' given min/max values and number of buckets for each value.
Use bucket width to determine index of each raw state value after scaling values on linear or log scale.
'''
def bucket_state(raw):
	global num_buckets, all_maxs, all_mins
	global scaled_bounds, scaled_mins, scaled_maxs, scaled_widths
	global labels	

	raw_no_freq = [raw[k] for k in LABELS] 
	# Bound raw values to min and max from params:
	raw_no_freq = np.clip(raw_no_freq, all_mins, all_maxs)
	# Apply log scaling where specified (otherwise linear):
	raw_no_freq[SCALING] = np.log(raw_no_freq[SCALING])
	# Floor values for proper bucketing:
	raw_floored = raw_no_freq - scaled_mins
	state = np.divide(raw_floored, scaled_widths)
	state = np.minimum.reduce([num_buckets-1, state])
	if FREQ_IN_STATE:
		# Add frequency index to end of state:
		state = np.append(state, [freq_to_bucket(raw['freq'])])
	# Convert floats to integer bucket indices and return:
	return [int(x) for x in state]




# (Greedy Q-Learning)
# Given previous and last state, action and reward between them (one-step), update
# based on greedy policy.
def update_Q_off_policy(last_state, last_action, reward, state):
	global Q, GAMMA, ALPHA
	# Follow greedy policy at new state to determine best action:
	best_next_return = np.max(Q[ tuple(state) ] )
	# Total return:
	total_return = reward + GAMMA*best_next_return
	# Update last_state estimate:
	old_value = Q[ tuple(last_state + [last_action] ) ]
	Q[ tuple(last_state + [last_action] ) ] = old_value + ALPHA*(total_return - old_value) 

'''
Q-learning driver function. Uses global state space LUTs (Q, C) to hold
state-action value estimates and state-action counts. 
On call tries to load previous state space value estimates and counts; 
if unsuccessful starts from all 0s.
'''
def Q_learning():
	global num_buckets
	global big_freqs
	global Q, EPSILON
	
	# Take care of statespace checkpoints:
	try:
		load_statespace()
		print("Loaded statespace")
	except:
		print("Could not load statespace; continue with fresh.")
	atexit.register(checkpoint_statespace)
	
	# Init runtime vars:
	# sa_history = deque(maxlen=HIST_LIM)
	last_action = None
	last_state = None
	reward = None
	bounded_freq_index=0
	cur_freq_index=0
	# Learn forever:
	while True:
		start = time.time()
		
		# get current state and reward from last iteration:
		stats = get_raw_state()
		state = bucket_state(stats)
		reward = reward_func(stats)	

		# Penalize trying to go out of bounds, since there is no utility in doing so.
		if ACTIONS != FREQS and bounded_freq_index != cur_freq_index:
			reward = reward - 1000
		
		# Update state-action-reward trace:
		if last_action is not None:
			# sa_history.append((last_state, last_action, reward))
			update_Q_off_policy(last_state, last_action, reward, state)
			print(last_state, last_action, reward)

		# Apply EPSILON randomness to select a random frequency:
		if random.random() < EPSILON:
			best_action = random.randint(0, ACTIONS-1)
		# Or greedily select the best frequency to use given past experience:
		else:
			# Note: numpy's argmax sensibly returns the lowest value if all have the same
			# value. Therefore, when we have all the same, behavior should really be random.
			best_action = np.argmax(Q[ tuple(state) ])
			if C[ tuple(state + [best_action]) ] == 0:
				best_action = random.randint(0, ACTIONS-1)

		# Take action.
		# (note big_freqs is lookup table from state_space module).
		# Also counter increment is performed in Q off policy update function.
		if ACTIONS == FREQS:
			dvfs.setClusterFreq(4, big_freqs[best_action])
		else:
			stay = ACTIONS // 2
			cur_freq_index = freq_to_bucket( stats['freq'] )
			cur_freq_index += (best_action - stay)
			bounded_freq_index = max( 0, min( cur_freq_index, FREQS-1))
			dvfs.setClusterFreq(4, big_freqs[bounded_freq_index])
		
		# Save state and action:
		last_state = state
		last_action = best_action
		print([stats[k] for k in LABELS])
		C[ tuple(state + [best_action]) ] += 1 

		# Wait for next period. Note that reward cannot be evaluated 
		# at least until the period has expired.
		elapsed = time.time() - start
		time.sleep(max(0, PERIOD - elapsed))


def reward_func(stats):
	global RHO, THETA # <-- From state space params module.
	IPS = stats['IPS']
	watts = stats['power']
	temp = stats['temp']
	# Return throughput (MIPS) minus thermal violation:
	thermal_v = max(temp - THERMAL_LIMIT, 0.0)
	instructions = IPS * PERIOD
	print(watts*1000000/instructions)
	reward = IPS/1000000.0 - (RHO * thermal_v) - (THETA * watts/instructions)
	return reward



if __name__ == "__main__":
#	if len(sys.argv) > 2:
#		print("USAGE: {} <benchmark_to_profile (optional)>".format(sys.argv[0]))
#		sys.exit()
	init()
	Q_learning()
#	if len(sys.argv) == 2:
#		benchmark=sys.argv[1]
#		try:
#			os.mkdir(benchmark)
#		except:
#			print("Folder {} already exists. Continue? (y/n)".format(benchmark))
#			cont = str(raw_input('> ')).lower()
#			while cont != 'y' and cont != 'n':
#				cont = str(raw_input('Enter y/n: ')).lower()
#			if cont == 'n':
#				sys.exit()
#		os.chdir(benchmark)
#		profile_statespace()
#	else:



# DEPRECATED CODE:
'''

def profile_statespace():
	global num_buckets
	ms_period = int(PERIOD*1000)
	raw_history = []
	try:
		max_state = np.load('max_state_{}ms_single_core.npy'.format(ms_period))
		min_state = np.load('min_state_{}ms_single_core.npy'.format(ms_period))
		print("Loaded previously checkpointed states.")
	except:
		max_state, _, _ = get_raw_state()
		min_state = max_state
		print("No previous data. Starting anew.")
	i = 0
	stat_counts = np.zeros((VARS, num_buckets), dtype=np.uint64)
	while True:
		start = time.time()
		raw, IPC_p, _ = get_raw_state()
		raw_history.append(list(raw)+[IPC_p])
		max_state = np.maximum.reduce([max_state, raw])
		min_state = np.minimum.reduce([min_state, raw])
		bucketed = bucket_state(raw)
		for stat_index, loc in enumerate(bucketed):
			stat_counts[stat_index, loc] += 1
		
		i += 1
		if i % 1000 == 0:
			np.save('max_state_{}ms_single_core.npy'.format(ms_period), max_state)
			np.save('min_state_{}ms_single_core.npy'.format(ms_period), min_state)
			np.save('bucket_counts_{}ms_single_core.npy'.format(ms_period), stat_counts)
			np.save('raw.npy', raw_history)
			print("{}: Checkpointed raw state max and min.".format(i))
			print(raw)
			print(bucketed)
		
		end = time.time()
		elapsed = end-start
		if elapsed > PERIOD:
			print("WARN: elapsed > period ({} > {})".format(elapsed, PERIOD))
		time.sleep(max(0, PERIOD - elapsed))
'''


# Given a history of states, actions taken at that state, and the subsequent reward,
# Update the value estimate for SA pairs.
# The update method here will perform a composite update with steps ranging from 
# 1 to n, where for a given state s, n is the number of steps following s in the history.
# (SARSA)
'''
def update_QC_on_policy(SAR_hist):
	global Q, C
	# Update each s,a pair in the history:
	for index, val in enumerate(SAR_hist):
		last_state, last_action, _ = val
		# Compute the number of steps taken after the s,a pair being updated.
		# Goes down to a minimum slack of 1 for the last item.
		# Note that the last s,a pair in the history will not be updated.
		slack = len(SAR_hist) - index
		if slack <= 1:
			continue
		# Set s,a return initially to 0.
		total_return = 0.0
		comp_weight = 1.0
		# Go through 1..n lookaheads (from current s,a pair to target s,a pair).
		for lookahead in range(1, slack):
			target_state, target_action, _ = SAR_hist[index+lookahead]
			target_val = Q[target_action, target_state[0], target_state[1], target_state[2], \
								target_state[3], target_state[4], target_state[5]]
			# Get rewards from state at index up to but not including the target:
			rewards = [x[-1] for x in SAR_hist[index:index+lookahead]]
			# Compute DISCOUNTED return up to target:
			# This loop gets the original indices of each reward but iterates in reverse:
			for i, r in reversed(list(enumerate(rewards))):
				pretarget_return += r
				if i > 0:
					pretarget_return *= GAMMA 
			# Update composite step return.
			# Note: last item in history is at lookahead = slack-1; this one gets special treatment.
			if lookahead < slack-1:
				total_return += (1 - LAMBDA) * comp_weight * (pretarget_return + target_val)
			else:
				# Omit (1-LAMBDA) factor if this is the last return in the composite series:
				total_return += comp_weight * (pretarget_return + target_val)
			# Compound composite weight for next lookahead on the same s,a pair.
			comp_weight *= LAMBDA

		# Use composite return, old_value, and count to update Q value estimate:
		old_value = Q[last_action, last_state[0], last_state[1], last_state[2], last_state[3], \
								last_state[4], last_state[5] ]
		count = C[last_action, last_state[0], last_state[1], last_state[2], last_state[3], \
								last_state[4], last_state[5] ]
		Q[last_action, last_state[0], last_state[1], last_state[2], last_state[3], \
								last_state[4], last_state[5] ] = \
								old_value + (total_return - old_value) / count

'''
