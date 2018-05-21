import sysfs_paths_xu3 as sfs
import devfreq_utils_xu3 as dvfs
from state_space_params_xu3 import *
import perf_module as pm
import numpy as np
import multiprocessing as mp
import subprocess, os
import ctypes
import time


# Array of global state-action values. Dimensions are:
# (num vf settings for big cluster * num state variables * max num buckets )
Q = np.zeros( (FREQS, VARS, BUCKETS) ) 


def checkpoint_statespace():
	return None

def load_statespace():
	return None

''' 
This function should run in a subprocess pinned to the particular CPU core
it should be reading performance counter data.
Upon initialization the process binds to its assigned CPU core.
'''
def perf_counter_proc(core_num, vals):
	# Set core affinity:
	pid = os.getpid()
	p = subprocess.Popen(["taskset", "-pc", str(core_num), str(pid)],\
											stdout=subprocess.PIPE)
	output, err = p.communicate()
#	print(output)
#	p = subprocess.Popen(["taskset", "-pc", str(pid)], stdout=subprocess.PIPE)
#	output, err = p.communicate()
#	print(output)

	# Get perf counters for pinned core:
	b_miss = float(pm.bmiss_count())
	cycles = float(pm.cycle_count())
	instrs = float(pm.inst_count())
	l2_miss = float(pm.l2refill_count())
	
	# Branch misses:
	vals[0] = float(b_miss)
	# cycles:
	vals[1] = float(cycles)
	# Instructions:
	vals[2] = float(instrs)
	# L2 misses per instruction:
	vals[3] = float(l2_miss)

# XU3 has built-in sensors, so use them:
def get_power():
	# Just return big cluster power:
	return dvfs.getPowerComponents()[0]

def reward1(counters, temps, power):
	# Return sum of IPC minus sum of thermal violations:
	total_ipc = counters[c4ipc] + counters[c5ipc] + counters[c6ipc] + counters[c7ipc]
	thermal_v = np.array(temps) - THERMAL_LIMIT
	thermal_v = np.maximum(thermal_v, 0.0)
	thermal_t = np.sum(thermal_v)
	reward = total_ipc - (thermal_v * RHO)
	return reward

def init_RL():
	# Make sure perf counter module is loaded
	process = subprocess.Popen(['lsmod'], stdout=subprocess.PIPE)
	output, err = process.communicate()
	loaded = "perf_counters" in output
	if not loaded:
		print("WARNING: perf-counters module not loaded. Loading...")
		process = subprocess.Popen(['sudo', 'insmod', 'perf-counters.ko'])
		output, err = process.communicate()
	profile_statespace() 

	print("FINISHED")
	return

'''
Returns state figures, non-quantized.
Includes branch misses, IPC, and L2 misses per instruction for each core, plus big cluster power.
TODO: add leakage power
'''
def get_raw_state(period):	
	# Start perf-counter threads:
	vals1 = [mp.Array(ctypes.c_double, 5, lock=False)]*4
	vals2 = [mp.Array(ctypes.c_double, 5, lock=False)]*4
	vals = [vals1, vals2]
	perf_procs = [None]*4
	# Get initial perf counter values:
	toggle = 0
	for pid in range(4):
		cpu_id = pid+4
		p = mp.Process(target=perf_counter_proc, args=(cpu_id, vals[toggle][pid]))
		perf_procs[pid] = p
		p.start()
	for i, p in enumerate(perf_procs):
		p.join()
		del p
	while True:
		toggle = toggle ^ 1
		start = time.time()
		# Get other stats here:
		T = dvfs.getTemps()[0:4]
		P = get_power()
		elapsed = time.time() - start
		#print("Sleeping for {} seconds.".format(period-elapsed))
		time.sleep(max(0, period-elapsed))
		# Get new perf counter vals:
		for pid in range(4):
			cpu_id = pid+4
			p = mp.Process(target=perf_counter_proc, args=(cpu_id, vals[toggle][pid]))
			perf_procs[pid] = p
			p.start()
		for i, p in enumerate(perf_procs):
			p.join()
			del p
		# Compute the change in values:
		diffs = np.abs(np.matrix(vals[0]) - np.matrix(vals[1]))
		# Compute state params from that:
		raw_state = [diffs[0,0]/diffs[0,2], diffs[0,2]/diffs[0,1], diffs[0,3]/diffs[0,2], T[0],\
				 diffs[1,0]/diffs[1,2], diffs[1,2]/diffs[1,1], diffs[1,3]/diffs[1,2], T[1],\
				 diffs[2,0]/diffs[2,2], diffs[2,2]/diffs[2,1], diffs[2,3]/diffs[2,2], T[2],\
				 diffs[3,0]/diffs[3,2], diffs[3,2]/diffs[3,1], diffs[3,3]/diffs[3,2], T[3],\
				 P]
		yield [float(x) for x in raw_state]


'''
Place state in 'bucket' given min/max values and number of buckets for each value
'''
def bucket_state(raw):
	# Use bucket width to determine index of each raw state value:
	all_mins = np.array([bmiss_MIN, ipc_MIN, mpi_MIN, temp_MIN]*4 + [pwr_MIN])
	all_widths = np.array([bmiss_width, ipc_width, mpi_width, temp_width]*4 + [pwr_width])
	raw_floored = np.array(raw) - all_mins
	state = np.divide(raw_floored, all_widths)
	return state


def profile_statespace():
	state_machine = get_raw_state(PERIOD)
	try:
		max_state = np.load('max_state.npy')
		min_state = np.load('min_state.npy')
	except:
		max_state = state_machine.next()
		min_state = state_machine.next()
	i = 0
	while True:
		raw = state_machine.next()
		max_state = np.maximum.reduce([max_state, raw])
		min_state = np.minimum.reduce([min_state, raw])
		i += 1
		if i % 1000 == 0:
			np.save('max_state.npy', max_state)
			np.save('min_state.npy', min_state)
			print("{}: Checkpointed raw state max and min.".format(i))
		elif i % 100 == 0:
			print(i)


def Q_learning(states):
	return


if __name__ == "__main__":
	init_RL()
