import numpy as np
import time
from collections import deque
from matplotlib import pyplot as plt
from matplotlib import animation
import sys

# Local imports:
import devfreq_utils_xu3 as dvfs
from state_space_params_xu3_single_core import *
import RL_gov_single_core as RLSC

def stats():	
	global cpu_num
	while True:
		# Update stats:
		args = [0.0]*8
		args[0] = [float(x) for x in dvfs.getTemps()][cpu_num]
		args[1] = RLSC.get_power()
		args[2] = RLSC.get_counter_value(cpu_num, "cycles")
		args[3] = RLSC.get_counter_value(cpu_num, "instructions_retired")
		args[4] = RLSC.get_counter_value(cpu_num, "branch_mispredictions")
		args[5] = RLSC.get_counter_value(cpu_num, "data_memory_accesses")
		args[6] = RLSC.get_counter_value(cpu_num, "l2_data_refills")
		args[7] = float(dvfs.getClusterFreq(cpu_num)) / 1000 # to MHz 
		yield args
		time.sleep(PERIOD)


def animate(args):
	global y, cycles, instrs, bmiss, dmema, l2miss, T, P, freq
	cycles.append(args[0])
	instrs.append(args[1])
	bmiss.append(args[2])
	dmema.append(args[3])
	l2miss.append(args[4])
	T.append(args[5])
	P.append(args[6])
	freq.append(args[7])
	return plt.plot(cycles, y, color='g')

if __name__ == "__main__":
	cpu_num = int(sys.argv[1])
	# Setup time plot:
	window = 60 # Window in seconds
	samples = int(1/PERIOD) * window
	fig = plt.figure() #subplots()
	# Data holding:
	cycles = deque([0.0]*samples, maxlen=samples)
	instrs = deque([0.0]*samples, maxlen=samples)
	bmiss  = deque([0.0]*samples, maxlen=samples)
	dmema  = deque([0.0]*samples, maxlen=samples)
	l2miss = deque([0.0]*samples, maxlen=samples)
	T      = deque([0.0]*samples, maxlen=samples)
	P      = deque([0.0]*samples, maxlen=samples)
	freq   = deque([0.0]*samples, maxlen=samples)
	y = np.arange(samples)
	# Start animation
	anim = animation.FuncAnimation(fig, animate, frames=stats, interval=samples)
	plt.show()
