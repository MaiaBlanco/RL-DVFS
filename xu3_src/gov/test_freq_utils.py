from devfreq_utils_xu3 import *
import sysfs_paths_xu3 as sysfs_paths


print("Testing userspace setter/unsetter for governor selection:")
cur_gov = open(sysfs_paths.fn_cpu_governor.format(0), 'r').read().strip()
print("Gov on little cluster: {}".format(cur_gov))
cur_gov = open(sysfs_paths.fn_cpu_governor.format(1), 'r').read().strip()
print("Gov on big cluster: {}".format(cur_gov))

print("Setting little cluster to userspace...")
setUserSpace(clusters=0)
cur_gov = open(sysfs_paths.fn_cpu_governor.format(0), 'r').read().strip()
print("Gov on little cluster: {}".format(cur_gov))

print("Setting big cluster to userspace...")
setUserSpace(clusters=1)
cur_gov = open(sysfs_paths.fn_cpu_governor.format(1), 'r').read().strip()
print("Gov on big cluster: {}".format(cur_gov))

print("Now resetting to previous governors...")
unsetUserSpace()
cur_gov = open(sysfs_paths.fn_cpu_governor.format(0), 'r').read().strip()
print("Gov on little cluster: {}".format(cur_gov))
cur_gov = open(sysfs_paths.fn_cpu_governor.format(1), 'r').read().strip()
print("Gov on big cluster: {}".format(cur_gov))
print("Done testing userspace set/unset")



print("Testing frequency getters and setters:")
print("Cluster one available frequencies:")
freqs = getAvailFreqs(0);
print(freqs)
print("Cluster one current frequency:")
cur_freq = getClusterFreq(0)
print(cur_freq)

print("Cluster two available frequencies:")
freqs = getAvailFreqs(4);
print(freqs)
print("Cluster two current frequency:")
cur_freq = getClusterFreq(1)
print(cur_freq)

print("Setting to userspace to set frequencies...")
setUserSpace()
cur_gov = open(sysfs_paths.fn_cpu_governor.format(0), 'r').read().strip()
print("Gov on little cluster: {}".format(cur_gov))
cur_gov = open(sysfs_paths.fn_cpu_governor.format(1), 'r').read().strip()
print("Gov on big cluster: {}".format(cur_gov))

print("Setting little cluster to 800,000 KHz")
setClusterFreq(0, 800000)
print("Cluster one current frequency:")
cur_freq = getClusterFreq(0)
print(cur_freq)
print("Setting big cluster to 1,800,000 KHz")
setClusterFreq(1, 1800000)
print("Cluster two current frequency:")
cur_freq = getClusterFreq(1)
print(cur_freq)

print("Testing GPU freq...")
cur_freq = getGPUFreq()
print(cur_freq)

print("Testing mem freq...")
cur_freq = getMemFreq()
print(cur_freq)
print("Done with frequency testing.")


print("Testing voltage getters.")
cur_v = resVoltage(0)
print("Little voltage {}".format(cur_v))
cur_v = resVoltage(4)
print("big voltage {}".format(cur_v))
cur_v = GPUVoltage()
print("GPU voltage {}".format(cur_v))
cur_v = memVoltage()
print("Mem voltage {}".format(cur_v))
print("Done testing voltage getters.")



print("Done with all testing. Make sure the results were correct!")
