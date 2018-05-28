import numpy as np
import multiprocessing as mp
import subprocess, os
import ctypes
import time

# Local imports:
import sysfs_paths_xu3 as sfs
import devfreq_utils_xu3 as dvfs
from state_space_params_xu3 import *
from state_space_params_xu3 import freq_to_bucket

# Redefine state space number of vars for single-core implementation:
VARS = 7
# Array of global state-action values. Dimensions are:
# (num vf settings for big cluster * num state variables * max num buckets )
Q = np.zeros( (FREQS, VARS, BUCKETS) ) 

def checkpoint_statespace():
	ms_period = int(PERIOD*1000)
	np.save("statespace_{}ms.npy".format(ms_period))

def load_statespace():
	ms_period = int(PERIOD*1000)
	return np.load("statespace_{}ms.npy".format(ms_period))

# XU3 has built-in sensors, so use them:
def get_power():
	# Just return big cluster power:
	return dvfs.getPowerComponents()[0]

def reward1(counters, temps, power):
	# Return sum of IPC minus sum of thermal violations:
	total_ipc = counters[c4ipc] 
	thermal_v = np.array(temps) - THERMAL_LIMIT
	thermal_v = np.maximum(thermal_v, 0.0)
	thermal_t = np.sum(thermal_v)
	reward = total_ipc - (thermal_v * RHO)
	return reward

def init_RL():
	# Make sure perf counter module is loaded:
	process = subprocess.Popen(['lsmod'], stdout=subprocess.PIPE)
	output, err = process.communicate()
	loaded = "perfmod" in output
	if not loaded:
		print("WARNING: perf-counters module not loaded. Loading...")
		process = subprocess.Popen(['sudo', 'insmod', 'perfmod.ko'])
		output, err = process.communicate()
	profile_statespace() 

	print("FINISHED")
	return

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
(BMPKI, IPC, MPKI, MDMEMAPKI, celsius, watts)
TODO: add leakage power?
TODO: add v/f levels?
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
	diffs[cpu-4, 4] = get_counter_value(cpu, "data_memory_accesses")

	T = [float(x) for x in dvfs.getTemps()]

	# Convert instructions to kiloInstructions:
	diffs[:,2] /= 1000.0
	# Convert cycles to kiloCycles to make IPC computation make sense:
	diffs[:,1] /= 1000.0
	# Compute state params from that:
	# bmiss/Kinst, IPC, L2misses/Kinst, dmem_accesses/Kinst, temp, power
	raw_state = [diffs[0,0]/diffs[0,2], diffs[0,2]/diffs[0,1], diffs[0,3]/diffs[0,2], 
				 diffs[0,4]/diffs[0,2], T[0],P, cpu_freq]
	return raw_state


'''
Place state in 'bucket' given min/max values and number of buckets for each value
'''
def bucket_state(raw):
	# Use bucket width to determine index of each raw state value:
	all_mins = np.array([bmiss_MIN, ipc_MIN, mpi_MIN, dmemi_MIN, temp_MIN] \
															+ [pwr_MIN] + [0])
	all_widths = np.array([bmiss_width, ipc_width, mpi_width, dmemi_width, temp_width] \
																+ [pwr_width] + [1])
	raw_floored = np.array(raw) - all_mins
	state = np.divide(raw_floored, all_widths)
	state[-1] = freq_to_bucket(raw[-1])
	for i, x in enumerate(state):
		if x > (BUCKETS-1):
			print("WARN: Stat {} has greater bucket than {}: {}".format(i, BUCKETS-1, x))
			state[i] = BUCKETS-1
	return [int(x) for x in state]


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
	stat_counts = np.zeros((VARS, BUCKETS), dtype=np.uint64)
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


def Q_learning(states):
	return


if __name__ == "__main__":
	init_RL()
