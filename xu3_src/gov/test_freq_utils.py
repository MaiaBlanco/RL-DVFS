from devfreq_utils_xu3 import *
import sysfs_paths_xu3 as sysfs_paths


print("Testing 'userspace' (performance) setter/unsetter for governor selection:")
print("Note: userspace control on XU3 is accomplished using max freq and performance gov.")
cur_gov = open(sysfs_paths.fn_cpu_governor.format(0), 'r').read().strip()
print("Gov on little cluster: {}".format(cur_gov))
cur_gov = open(sysfs_paths.fn_cpu_governor.format(4), 'r').read().strip()
print("Gov on big cluster: {}".format(cur_gov))

print("Setting little cluster to userspace...")
setUserSpace(clusters=0)
cur_gov = open(sysfs_paths.fn_cpu_governor.format(0), 'r').read().strip()
print("Gov on little cluster: {}".format(cur_gov))

print("Setting big cluster to userspace...")
setUserSpace(clusters=4)
cur_gov = open(sysfs_paths.fn_cpu_governor.format(4), 'r').read().strip()
print("Gov on big cluster: {}".format(cur_gov))

print("Now resetting both clusters to previous governors...")
unsetUserSpace()
cur_gov = open(sysfs_paths.fn_cpu_governor.format(0), 'r').read().strip()
print("Gov on little cluster: {}".format(cur_gov))
cur_gov = open(sysfs_paths.fn_cpu_governor.format(4), 'r').read().strip()
print("Gov on big cluster: {}".format(cur_gov))
print("Done testing userspace set/unset\n\n")



print("Testing frequency getters and setters:")
print("Little cluster available frequencies:")
freqs = getAvailFreqs(0);
print(freqs)
print("Little cluster current frequency:")
cur_freq = getClusterFreq(0)
print(cur_freq)

print("Big cluster available frequencies:")
freqs = getAvailFreqs(4);
print(freqs)
print("Big cluster current frequency:")
cur_freq = getClusterFreq(4)
print(cur_freq)

print("Setting to 'userspace' (performance) to set frequencies...")
setUserSpace()
cur_gov = open(sysfs_paths.fn_cpu_governor.format(0), 'r').read().strip()
print("Gov on little cluster: {}".format(cur_gov))
cur_gov = open(sysfs_paths.fn_cpu_governor.format(4), 'r').read().strip()
print("Gov on big cluster: {}".format(cur_gov))

print("Setting little cluster to 800,000 KHz")
setClusterFreq(0, 800000)
print("Cluster one current frequency:")
cur_freq = getClusterFreq(0)
print(cur_freq)
print("Setting big cluster to 1,800,000 KHz")
setClusterFreq(4, 1800000)
print("Cluster two current frequency:")
cur_freq = getClusterFreq(4)
print(cur_freq)
print("Finished testing CPU freq getters/setters.\n\n")

print("Testing GPU freq...")
cur_freq = getGPUFreq()
print(cur_freq)

print("Testing mem freq...")
cur_freq = getMemFreq()
print(cur_freq)
print("Done with frequency testing.\n")


print("Testing voltage getters.")
cur_v = cpuVoltage(0)
print("Little voltage {}".format(cur_v))
cur_v = cpuVoltage(4)
print("big voltage {}".format(cur_v))
cur_v = GPUVoltage()
print("GPU voltage {}".format(cur_v))
cur_v = memVoltage()
print("Mem voltage {}".format(cur_v))
print("Done testing voltage getters.\n")



print("Done with all testing. Make sure the results were correct!")
