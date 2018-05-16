import time
import sys, os
import sysfs_paths_xu3 as sysfs
import atexit
import psutil

# Userspace cpu frequency governor and utilities for XU3
# Based on:
# https://stackoverflow.com/questions/1296703/getting-system-status-in-python#1296816

# On the exynos 5422, cluster 0 (kfc) is the low-power (LITTLE) cluster and 
# cluster 1 (arm, eagle) is the high-power (big) cluster.

prev_govs = None 

# Return the power for the big cluster, little cluster, gpu, and memory
def getPowerComponents():
	p_vals = []
	with open(sysfs.big_cluster_power, 'r') as pf:
		p_vals.append( float(pf.read()) )
	with open(sysfs.little_cluster_power, 'r') as pf:
		p_vals.append( float(pf.read()) )
	with open(sysfs.gpu_power, 'r') as pf:
		p_vals.append( float(pf.read()) )
	with open(sysfs.mem_power, 'r') as pf:
		p_vals.append( float(pf.read()) )
	return p_vals
	
def getAvailFreqs(cpu_num):
	cluster = (cpu_num//4)
	if cluster == 0:
		freqs = open(sysfs.little_cluster_freq_range, 'r').read().strip().split(' ')
	elif cluster == 1:
		freqs = open(sysfs.big_cluster_freq_range, 'r').read().strip().split(' ')
	else:
		print("This cluster ({}) doesn't exist!".format(cluster))
		return None
	return [int(f.strip()) for f in freqs]

def setUserSpace(clusters=None):
	global prev_govs
	print("Setting performance")
	if clusters is None:
		clusters = [0, 4]
	elif type(clusters) is int:
		clusters = [(clusters % 4) * 4]
	elif type(clusters) is not list:
		print("ERROR: input None, int, or list of ints to set/unset userspace function.")
		sys.exit(1)
	else:
		clusters = [(x%4)*4 for x in clusters]
	#print("Using CPUs {}".format(clusters))
	prev_govs = ['performance'] * (sorted(clusters)[-1] + 1)
	for i in clusters:
		if i != 0 and i != 4:
			print("ERROR: {} is not a valid cluster number! Integers 0 and 4 are valid.".format(i))
			sys.exit(1)
		with open(sysfs.fn_cpu_governor.format(i), 'r') as f:
			prev_govs[i] = f.readline().strip()
		with open(sysfs.fn_cpu_governor.format(i), 'w') as f:
			f.write('performance')
			f.flush()	

def unsetUserSpace(clusters=None):
	global prev_govs
	if clusters is None:
		clusters = [0, 4]
	elif type(clusters) is int:
		clusters = [(clusters % 4) * 4]
	elif type(clusters) is not list:
		print("ERROR: input None, int, or list of ints to set/unset userspace function.")
		sys.exit(1)
	else:
		clusters = [(x%4)*4 for x in clusters]
	#print("Using CPUs {}".format(clusters))
	for i in clusters:
		if i != 0 and i != 4:
			print("ERROR: {} is not a valid cluster number! Integers 0 and 4 are valid.".format(i))
			sys.exit(1)
		with open(sysfs.fn_cpu_governor.format(i), 'w') as f:
			f.write(prev_govs[i])
		setClusterFreq(i, getAvailFreqs(i)[-1] )
	

def getClusterFreq(cluster_num):
	cluster_num = 0 if cluster_num < 4 else 4
	#print("using cpu {}".format(cluster_num))
	with open(sysfs.fn_cpu_freq_read.format(cluster_num), 'r') as f:
		return int(f.read().strip())
	
# Accepts frequency in khz as int or string
def setClusterFreq(cluster_num, frequency):
	if cluster_num > 1:
		cluster_num = cluster_num // 4
	#cluster_num = (cluster_num % 4) * 4
	#print("using cluster {}".format(cluster_num))
	if cluster_num == 0:
		cluster_max_freq = sysfs.little_cluster_max
	elif cluster_num == 1:
		cluster_max_freq = sysfs.big_cluster_max
	else:
		print("ERROR: invalid cluster number!")
		return None
	with open(cluster_max_freq, 'w') as f:
		# todo: add bounds checking
		f.write(str(frequency))	
		f.flush()

def getGPUFreq():
	with open(sysfs.gpu_freq, 'r') as f:
		return int(f.read().strip()) * 1000 

def getMemFreq():
	with open(sysfs.mem_freq, 'r') as f:
		return int(f.read().strip()) 

def getTemps():
	with open(sysfs.thermal_sensors, 'r') as tempf:
		temps = tempf.readlines()
		temps = [int(x.strip().split(' ')[2])/1000 for x in temps]
	# Note: on the 5422, cpu temperatures 5 and 7 (big cores 1 and 3, counting from 0)
	# appear to be swapped.
	# therefore, swap them back:
	t1 = temps[1]
	temps[1] = temps[3]
	temps[3] = t1
	return temps

def resVoltage(n):
	# 0 is little cluster
	# 4 is big cluster
	# TODO: add support for GPU and mem voltages.
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
