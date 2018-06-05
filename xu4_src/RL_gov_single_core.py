import numpy as np
import multiprocessing as mp
import subprocess, os, sys
import ctypes
import time
import random
import atexit
from collections import deque

# Local imports:
import sysfs_paths as sfs
import devfreq_utils as dvfs
from state_space_params_xu3_single_core import *
#from power_model import get_dyn_power
import therm_params as tm

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
print("Widths:")


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
	if Q_t.shape != Q.shape:
		if Q.ndim == Q_t.ndim and Q_t.shape[-1] == ACTIONS:
			print("Warning: extending loaded Q to match state space dimensions!")
		else:
			raise Exception("Completely mismatched loaded state space to desired statespace.")
	else:
		Q = Q_t

# XU4 does not have built-in sensors...
def get_power(temps):
	# Just return big cluster power:
	#return dvfs.getPowerComponents()[0]
	return 0.0 #get_dyn_power(temps)

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
	dvfs.setUserSpace(4)

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
	cycles_possible = float(cpu_freq * 1000 *  PERIOD)
	cycles_used = get_counter_value(cpu, "cycles")
	bmisses = get_counter_value(cpu, "branch_mispredictions")
	instructions = get_counter_value(cpu, "instructions_retired")
	l2misses = get_counter_value(cpu, "l2_data_refills")
	dmemaccesses = get_counter_value(cpu, "data_memory_accesses")
	T = [float(x) for x in dvfs.getTemps()]
	P = get_power(T)
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
		'volt' :tm.big_f_to_v_MC1[float(cpu_freq) / 1000000],
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
	state = np.clip(state, 0, num_buckets-1)
	if FREQ_IN_STATE:
		# Add frequency index to end of state:
		state = np.append(state, [ freq_to_bucket[ raw['freq'] ] ])
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
	return Q[ tuple(last_state + [last_action] ) ]

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
			reward -= 5000
		
		# Update state-action-reward trace:
		if last_action is not None:
			# sa_history.append((last_state, last_action, reward))
			v = update_Q_off_policy(last_state, last_action, reward, state)
			print(last_state, last_action, reward, v)

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
			cur_freq_index = freq_to_bucket[ stats['freq'] ]
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
	global RHO # <-- From state space params module.
	IPS = stats['IPS']
	temp = stats['temp']
	freq = stats['freq']
	volts = stats['volt']
	vvf = (volts ** 2) * float(freq)
	# Return throughput (MIPS) minus thermal violation:
	thermal_v = max(temp - THERMAL_LIMIT, 0.0)
	instructions = IPS * PERIOD
	thermal_penalty = (RHO * thermal_v)
	throughput_term = IPS/vvf
	print("Thoughput term", throughput_term)
	print("Thermal penalty:", thermal_penalty)
	reward = throughput_term - thermal_penalty
	return reward

'''
Use global lookup table (LUT) Q to select best action based on quantized state.
This implementation applies learned Q 'function' to core 4 only.
'''
def run_offline():
	global Q
	global big_freqs
	# load state-action space values from Q file: 
	try:
		load_statespace()
		print("Loaded statespace")
	except:
		print("Could not load statespace. State space Q must be trained with Q learning function.")
		sys.exit(1)
	# Run offline greedy policy:
	while True:
		start = time.time()
		
		# get current state:
		stats = get_raw_state()
		state = bucket_state(stats)

		# Greedily select the best frequency to use given past experience:
		best_action = np.argmax(Q[ tuple(state) ])

		# Take action.
		# (note big_freqs is lookup table from state_space module).
		if ACTIONS == FREQS:
			dvfs.setClusterFreq(4, big_freqs[best_action])
		else:
			stay = ACTIONS // 2
			cur_freq_index = freq_to_bucket[ stats['freq'] ]
			cur_freq_index += (best_action - stay)
			bounded_freq_index = max( 0, min( cur_freq_index, FREQS-1))
			dvfs.setClusterFreq(4, big_freqs[bounded_freq_index])
		
		# Print state and action:
		print([stats[k] for k in LABELS])
		print(state, best_action)

		# Wait for next period. 
		elapsed = time.time() - start
		print("Elapsed:", elapsed)
		time.sleep(max(0, PERIOD - elapsed))
	


'''
Use global lookup table (LUT) Q to select best action based on quantized state.
This implementation applies learned Q 'function' from core 4 to all big cores.
'''
def run_offline_multicore():
	global Q	
	return 0

def usage():
		print("USAGE: {} <train|run>".format(sys.argv[0]))
		sys.exit(0)



if __name__ == "__main__":
	init()
	if len(sys.argv) > 1:
		if sys.argv[1] == "run":
			run_offline()
		elif sys.argv[1] == "train":
			Q_learning()
		else:
			usage()
	else:
		print("No args given; defaulting to training in 5 seconds.")
		time.sleep(5)
		Q_learning()
