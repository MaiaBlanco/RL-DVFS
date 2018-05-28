import numpy as np
import multiprocessing as mp
import subprocess, os, sys
import ctypes
import time
import random

# Local imports:
import sysfs_paths_xu3 as sfs
import devfreq_utils_xu3 as dvfs
from state_space_params_xu3_single_core import *
from state_space_params_xu3_single_core import freq_to_bucket

num_buckets = np.array([BUCKETS[k] for k in LABELS])
# TODO: resolve redundant frequency in action and state space
dims = [FREQS] + list(num_buckets) + [FREQS]
print(dims)
Q = np.zeros( dims ) 
C = np.zeros( dims, dtype=np.uint32)

def checkpoint_statespace(state_vals):
	ms_period = int(PERIOD*1000)
	np.save("statespace_{}ms.npy".format(ms_period), state_vals)

def load_statespace():
	ms_period = int(PERIOD*1000)
	return np.load("statespace_{}ms.npy".format(ms_period))

# XU3 has built-in sensors, so use them:
def get_power():
	# Just return big cluster power:
	return dvfs.getPowerComponents()[0]

def reward1(raw_state):
	# Return sum of IPC minus sum of thermal violations:
	total_ipc = raw_state[1] 
	thermal_v = raw_state[4] - THERMAL_LIMIT
	thermal_v = np.maximum(thermal_v, 0.0)
	#thermal_t = np.sum(thermal_v)
	reward = total_ipc - (thermal_v * RHO)
	return reward

def init():
	# Make sure perf counter module is loaded:
	process = subprocess.Popen(['lsmod'], stdout=subprocess.PIPE)
	output, err = process.communicate()
	loaded = "perfmod" in output
	if not loaded:
		print("WARNING: perf-counters module not loaded. Loading...")
		process = subprocess.Popen(['sudo', 'insmod', 'perfmod.ko'])
		output, err = process.communicate()

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
	diffs = np.zeros((1,5))
	P = get_power()
	cpu = 4
		
	cpu_freq = dvfs.getClusterFreq(cpu)
	# Convert cpu freq from kHz to Hz and then multiply by period;
	total_possible_cycles = int(cpu_freq * 1000 * PERIOD)
	#cycles_used = get_counter_value(cpu, "cycles")
	
	diffs[cpu-4, 0] = get_counter_value(cpu, "branch_mispredictions")
	diffs[cpu-4, 1] = total_possible_cycles
	diffs[cpu-4, 2] = get_counter_value(cpu, "instructions_retired")
	diffs[cpu-4, 3] = get_counter_value(cpu, "l2_data_refills")
	#diffs[cpu-4, 4] = get_counter_value(cpu, "data_memory_accesses")

	T = [float(x) for x in dvfs.getTemps()]

	# Convert instructions to kiloInstructions:
	diffs[:,2] /= 1000.0
	# Convert cycles to kiloCycles to make IPC computation make sense:
	diffs[:,1] /= 1000.0
	# Compute state params from that:
	# bmiss/Kinst, IPC, L2misses/Kinst, dmem_accesses/Kinst, temp, power
	raw_state = [ \
		diffs[0,0]/diffs[0,2], 
		diffs[0,2]/diffs[0,1], 
		diffs[0,3]/diffs[0,2], 
	#	diffs[0,4]/diffs[0,2], 
		T[0], P, cpu_freq]
	return raw_state


'''
Place state in 'bucket' given min/max values and number of buckets for each value
'''
def bucket_state(raw):
	global num_buckets
	raw_no_freq = raw[:-1]
	# Use bucket width to determine index of each raw state value:
	all_mins = np.array([MINS[k] for k in LABELS])
	all_maxs = np.array([MAXS[k] for k in LABELS])
	# Bound raw values to min and max from params:
	raw_no_freq = np.minimum.reduce([all_maxs, raw_no_freq])
	raw_no_freq = np.maximum.reduce([all_mins, raw_no_freq])
	# Apply log scaling where specified:
	raw_no_freq[SCALING] = np.log(raw_no_freq[SCALING]) #np.array([np.log(x) if s else x for x,s in zip(raw_no_freq, SCALING)])
	# Floor values for proper bucketing:
	scaled_bounds = [(np.log(x), np.log(y)) if s else (x,y) for x,y,s in zip(all_mins, all_maxs, SCALING)]
	scaled_mins, scaled_maxs = zip(*scaled_bounds)
	scaled_widths = np.divide( np.array(scaled_maxs) - np.array(scaled_mins), num_buckets)
	raw_floored = raw_no_freq - scaled_mins
	state = np.divide(raw_floored, scaled_widths)
	state = np.append(state, [freq_to_bucket(raw[-1])])
	return [int(x) for x in state]


def update_QC(SAR_hist):
	global Q, C
	for index, val in enumerate(SAR_hist):
		last_state, last_action, last_reward = val
		slack = max( 0, len(SAR_hist) - index )
		if slack == 0:
			continue
		else:
			total_return = 0.0
			for lookahead in range(1, slack):
				state, target_action, _ = SAR_hist[index+lookahead]
				target_val = Q[target_action,state[0], state[1], state[2], state[3], \
									state[4], state[5]]
				# Get rewards from state at index up to but not including the target:
				rewards = [x[-1] for x in SAR_hist[index:index+lookahead]]
				# Compute DISCOUNTED return up to target:
				pretarget_return = np.sum([x * GAMMA**i for i,x in enumerate(rewards)])
				# Update composite step return:
				if lookahead < slack-1:
					total_return += (1 - LAMBDA) * (LAMBDA**(lookahead-1)) * (pretarget_return + target_val)
				else:
					# Omit (1-LAMBDA) factor if this is the last return in the composite series:
					total_return += (LAMBDA**(lookahead-1)) * (pretarget_return + target_val)

			# Use composite returns over 1..n steps, old_value, and count to update Q value:
			old_value = Q[last_action,last_state[0], last_state[1], last_state[2], last_state[3], \
									last_state[4], last_state[5] ]
			count = C[last_action,last_state[0], last_state[1], last_state[2], last_state[3], \
									last_state[4], last_state[5] ]
			Q[last_action,last_state[0], last_state[1], last_state[2], last_state[3], \
									last_state[4], last_state[5] ] = \
									old_value + (total_return - old_value) / count




# TODO: implement limit to history length
def Q_learning():
	# Array of state-action values. Dimensions are:
	global num_buckets
	global big_freqs
	global Q,C
	sa_history = []
	last_action = None
	last_state = None
	# Learn forever:
	while True:
		start = time.time()
		
		# get current state:
		raw_state = get_raw_state()
		state = bucket_state(raw_state)
		reward = reward1(raw_state)	
		print(reward)
		
		# Update state-action-reward trace:
		if last_action is not None:
			sa_history.append((last_state, last_action, reward))
			update_QC(sa_history)

		# Compute epsilon for next round of action: 
		N_st = np.sum(C[:,state[0], state[1], state[2], state[3], \
									state[4], state[5] ]) 
		epsilon = N0/(N0+N_st)

		# Apply epsilon randomness:
		if random.random() < epsilon:
			best_action = random.randint(1,FREQS-1)
		else:
			best_action = np.argmax(Q[:,state[0], state[1], state[2], state[3], \
									state[4], state[5] ] )
		print(best_action)

		# Save current state:
		last_state = state
		last_action = best_action

		# Take action:
		dvfs.setClusterFreq(4, big_freqs[best_action])
		
		# Wait for next period:
		elapsed = time.time() - start
		time.sleep(max(0, PERIOD - elapsed))


def profile_statespace():
	raw_history = []
	ms_period = int(PERIOD*1000)
	set_period(ms_period)
	try:
		max_state = np.load('max_state_{}ms_single_core.npy'.format(ms_period))
		min_state = np.load('min_state_{}ms_single_core.npy'.format(ms_period))
		print("Loaded previously checkpointed states.")
	except:
		max_state = get_raw_state()
		min_state = max_state
	i = 0
	num_buckets = np.max([v for v in BUCKETS.values()])
	stat_counts = np.zeros((VARS, num_buckets), dtype=np.uint64)
	while True:
		start = time.time()
		raw = get_raw_state()
		raw_history.append(raw)
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


if __name__ == "__main__":
	if len(sys.argv) > 2:
		print("USAGE: {} <benchmark_to_profile (optional)>".format(sys.argv[0]))
		sys.exit()
	init()
	if len(sys.argv) == 2:
		benchmark=sys.argv[1]
		os.mkdir(benchmark)
		os.chdir(benchmark)
		profile_statespace()
	else:
		Q_learning()
