import sys, os
import sysfs_paths as sysfs

# Userspace cpu frequency governor and utilities for XU3
# Based on:
# https://stackoverflow.com/questions/1296703/getting-system-status-in-python#1296816

# On the exynos 5422, cluster 0 (kfc) is the low-power (LITTLE) cluster and 
# cluster 1 (arm, eagle) is the high-power (big) cluster.

# In all functions below, cluster or core selection arguments should be the lowest
# numbered CPU CORE in the selected cluster or the number of the specific core.

prev_govs = None 

# Return list of ints of available frequencies, sorted from least to greatest.
def getAvailFreqs(cpu_num):
	cluster = (cpu_num//4)
	if cluster == 0:
		freqs = open(sysfs.little_cluster_freq_range, 'r').read().strip().split(' ')
	elif cluster == 1:
		freqs = open(sysfs.big_cluster_freq_range, 'r').read().strip().split(' ')
	else:
		print("This cluster ({}) doesn't exist!".format(cluster))
		return None
	return list(reversed([int(f.strip()) for f in freqs]))

# As with note at top of this file, clusters should be selected using CORE numbers.
def setUserSpace(clusters=None):
	global prev_govs
	print("WARNING: Running on XU3; therefore setting performance and limiting max freq.")
	if clusters is None:
		clusters = [0, 4]
	elif type(clusters) is int:
		clusters = [(clusters // 4) * 4]
	elif type(clusters) is not list:
		print("ERROR: input None, int, or list of ints to set/unset userspace function.")
		sys.exit(1)
	else:
		clusters = [x//4 for x in clusters]
	#print("Using CPUs {}".format(clusters))
	if prev_govs is None:
		prev_govs = {x:'performance' for x in clusters}
	else:
		for x in clusters:
			if x not in prev_govs.keys():
				prev_govs[x] = 'performance'

	for c in clusters:
		if c != 0 and c != 4:
			print("ERROR: {} is not a valid cluster number! Integers 0 and 4 are valid.".format(c))
			sys.exit(1)
		with open(sysfs.fn_cpu_governor.format(c), 'r+') as f:
			# Record previous governor setting for cluster c
			prev_govs[c] = f.readlines()[0].strip()
			f.seek(0)
			# Set userspace governor setting for cluster c
			f.write('performance')
			f.flush()


# As with note at top of this file, clusters should be selected using CORE numbers.
def unsetUserSpace(clusters=None):
	global prev_govs
	print("WARNING: Running on XU3; therefore unsetting performance and removing max freq limit.")
	if clusters is None:
		clusters = [0, 4]
	elif type(clusters) is int:
		clusters = [(clusters // 4)*4]
	elif type(clusters) is not list:
		print("ERROR: input None, int, or list of ints to set/unset userspace function.")
		sys.exit(1)
	else:
		clusters = [x//4 for x in clusters]
	if prev_govs is None:
		prev_govs = {x:'performance' for x in clusters}
	else:
		for x in clusters:
			if x not in prev_govs.keys():
				prev_govs[x] = 'performance'
	#print("Using CPUs {}".format(clusters))
	for c in clusters:
		if c != 0 and c != 4:
			print("ERROR: {} is not a valid cluster number! Integers 0 and 4 are valid.".format(c))
			sys.exit(1)
		with open(sysfs.fn_cpu_governor.format(c), 'w') as f:
			f.write(prev_govs[c])
		# Note: set cluster function sets the max frequency on XU3.
		# This is because the userspace governor is not actually available;
		# hence the workaround is to set to performance and change the max freq.
		setClusterFreq(c, getAvailFreqs(c)[-1] )
	

# As with note at top of this file, clusters should be selected using CORE numbers.
def getClusterFreq(cpu_num):
	#print("using cpu {}".format(cpu_num))
	with open(sysfs.fn_cpu_freq_read.format(cpu_num), 'r') as f:
		return int(f.read().strip())
	
# Accepts frequency in khz as int or string
# As with note at top of this file, clusters should be selected using CORE numbers.
def setClusterFreq(cpu_num, frequency):
	cpu_num = cpu_num // 4
	# Note: set cluster function sets the max frequency on XU3.
	# This is because the userspace governor is not actually available;
	# hence the workaround is to set to performance and change the max freq.
	if cpu_num == 0:
		cluster_max_freq = sysfs.little_cluster_max
		a_freqs = getAvailFreqs(0)
	elif cpu_num == 1:
		cluster_max_freq = sysfs.big_cluster_max
		a_freqs = getAvailFreqs(4)
	else:
		print("ERROR: invalid cluster number!")
		return None
	with open(cluster_max_freq, 'w') as f:
		if int(frequency) > a_freqs[-1]:
			frequency = a_freqs[-1]
		elif int(frequency) < a_freqs[0]:
			frequency = a_freqs[0]
		f.write(str(frequency))	
		f.flush()

def getGPUFreq():
	with open(sysfs.gpu_freq, 'r') as f:
		return int(f.read().strip()) * 1000 

def getMemFreq():
	with open(sysfs.mem_freq, 'r') as f:
		return int(f.read().strip()) 

def getTemps():
	templ = []
	for i in range(5):
		temp = float(file(sysfs.fn_thermal_sensor.format(i),'r').readline().strip())/1000
		templ.append(temp)
	# Note: on the 5422, cpu temperatures 5 and 7 (big cores 1 and 3, counting from 0)
	# appear to be swapped.
	# therefore, swap them back:
	t1 = templ[1]
	templ[1] = templ[3]
	templ[3] = t1
	return templ

# As with note at top of this file, clusters should be selected using CORE numbers.
def cpuVoltage(n):
	n = (n // 4) * 4
	# 0 is little cluster
	# 4 is big cluster
	if n == 0:
		temp = float(file(sysfs.little_micro_volts, 'r').readline().strip())/1000000
	elif n == 4:
		temp = float(file(sysfs.big_micro_volts, 'r').readline().strip())/1000000
	else:
		raise Exception('Error: {} is not a supported resource ID for voltage.'.format(n))
	return temp

def GPUVoltage():
	return float(file(sysfs.gpu_micro_volts, 'r').readline().strip())/1000000

def memVoltage():
	return float(file(sysfs.mem_micro_volts, 'r').readline().strip())/1000000
