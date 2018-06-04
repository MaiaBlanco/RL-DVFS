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
	print("Setting userspace")
	if clusters is None:
		clusters = [0, 4]
	elif type(clusters) is int:
		clusters = [(clusters // 4) * 4]
	elif type(clusters) is not list:
		print("ERROR: input None, int, or list of ints to set/unset userspace function.")
		sys.exit(1)
	else:
		clusters = [x//4 for x in clusters]
	prev_govs = ['powersave'] * (sorted(clusters)[-1] + 1)
	for i in clusters:
		if i != 0 and i != 4:
			print("ERROR: {} is not a valid cluster number! Integers 0 and 4 are valid.".format(i))
			sys.exit(1)
		with open(sysfs.fn_cluster_gov.format(i), 'r') as f:
			prev_govs[i] = f.readline().strip()
		with open(sysfs.fn_cluster_gov.format(i), 'w') as f:
			f.write('userspace')
			f.flush()

# As with note at top of this file, clusters should be selected using CORE numbers.
def unsetUserSpace(clusters=None):
	global prev_govs
	if clusters is None:
		clusters = [0, 4]
	elif type(clusters) is int:
		clusters = [(clusters // 4)*4]
	elif type(clusters) is not list:
		print("ERROR: input None, int, or list of ints to set/unset userspace function.")
		sys.exit(1)
	else:
		clusters = [x//4 for x in clusters]
	for i in clusters:
		if i != 0 and i != 4:
			print("ERROR: {} is not a valid cluster number! Integers 0 and 4 are valid.".format(i))
			sys.exit(1)
		with open(sysfs.fn_cluster_gov.format(i), 'w') as f:
			f.write(prev_govs[i])

# As with note at top of this file, clusters should be selected using CORE numbers.
def getClusterFreq(cpu_num):
	with open(sysfs.fn_cpu_freq_read.format(cpu_num), 'r') as f:
		return int(f.read().strip())
	
# Accepts frequency in khz as int or string
# As with note at top of this file, clusters should be selected using CORE numbers.
def setClusterFreq(cpu_num, frequency):
	with open(sysfs.fn_cpu_freq_set.format(cpu_num), 'w') as f:
		f.write(str(frequency))	
	

def getGPUFreq():
	with open(sysfs.gpu_freq, 'r') as f:
		return int(f.read().strip()) * 1000 

def getMemFreq():
	#with open(sysfs.mem_freq, 'r') as f:
	#return int(f.read().strip()) 
	return int(750000)

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
