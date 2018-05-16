# This file defines strings as sysfs paths for various
# dials and control knobs available in Debian.
# fn_ prefix indicates that the string should be formatted with a
# core number

# For each cpu core
fn_cpu_core_base="/sys/devices/system/cpu/cpu{}/cpufreq/"
fn_cpu_cluster=fn_cpu_core_base+"affected_cpus"
#fn_cpu_max_freq_cpuinfo=fn_cpu_core_base+"cpuinfo_max_freq"
#fn_cpu_min_freq_cpuinfo=fn_cpu_core_base+"cpuinfo_min_freq"
#fn_cpu_freq_read_cpuinfo=fn_cpu_core_base+"cpuinfo_cur_freq"
fn_cpu_freq_read=fn_cpu_core_base+"scaling_cur_freq"
fn_cpu_governor=fn_cpu_core_base+"scaling_governor"
fn_cpu_max_freq_set=fn_cpu_core_base+"scaling_max_freq"
#fn_cpu_min_freq_set=fn_cpu_core_base+"scaling_min_freq"
#fn_cpu_freq_set=fn_cpu_core_base+"scaling_setspeed"
fn_core_enabled=fn_cpu_core_base[:-8]+"online"

# for clusters (e.g. policies on whole clusters):
cluster_base="/sys/devices/system/cpu/cpufreq/mp-cpufreq/"
big_cluster_max=fn_cpu_max_freq_set.format(4)#cluster_base+"cpu_max_freq"
#big_cluster_min=cluster_base+"cpu_min_freq"
little_cluster_max=fn_cpu_max_freq_set.format(0)#cluster_base+"kfc_max_freq"
#litte_cluster_min=cluster_base+"kfc_min_freq"
big_cluster_freq_range=cluster_base+"cpu_freq_table"
little_cluster_freq_range=cluster_base+"kfc_freq_table"

# for temperatures:
thermal_base="/sys/devices/10060000.tmu/"
thermal_sensors=thermal_base+"temp"

'''
reg 8 - kfc - little cores
reg 7 - g3d - primary gpu
reg 4 - mif - primary memory
reg 25 - g3ds - secondary gpu?
reg 23 - mifs - secondary memory?
reg 5 - eagle - big cores
'''
# For voltages:
little_cluster_voltage_base="/sys/devices/12ca0000.hsi2c/i2c-0/0-0066/s2mps11-pmic/regulator/regulator.8/"
little_micro_volts=little_cluster_voltage_base+"microvolts"
little_max_micro_volts=little_cluster_voltage_base+"max_microvolts"
little_min_micro_volts=little_cluster_voltage_base+"min_microvolts"

big_cluster_voltage_base="/sys/devices/12ca0000.hsi2c/i2c-0/0-0066/s2mps11-pmic/regulator/regulator.5/"
big_micro_volts=big_cluster_voltage_base+"microvolts"
big_max_micro_volts=big_cluster_voltage_base+"max_microvolts"
big_min_micro_volts=big_cluster_voltage_base+"min_microvolts"


# Paths for GPU stats:
gpu_base = "/sys/bus/platform/drivers/mali/11800000.mali/"
gpu_freq = gpu_base + "clock"
# GPU voltage:
gpu_voltage_base = "/sys/devices/12ca0000.hsi2c/i2c-0/0-0066/s2mps11-pmic/regulator/regulator.7/"
gpu_micro_volts =     gpu_voltage_base+"microvolts"
gpu_max_micro_volts = gpu_voltage_base+"max_microvolts"
gpu_min_micro_volts = gpu_voltage_base+"min_microvolts"

# Paths for memory stats:
# Memory runs at default frequency of 750000 kHz
mem_freq_base = "/sys/class/devfreq/exynos5-devfreq-mif/"
mem_freq = mem_freq_base + "cur_freq"
mem_voltage_base="/sys/devices/12ca0000.hsi2c/i2c-0/0-0066/s2mps11-pmic/regulator/regulator.4/"
mem_micro_volts = mem_voltage_base + 'microvolts'
gpu_max_micro_volts = mem_voltage_base+"max_microvolts"
gpu_min_micro_volts = mem_voltage_base+"min_microvolts"


# Paths for power:
big_cluster_power = "/sys/bus/i2c/devices/3-0040/sensor_W"
little_cluster_power = "/sys/bus/i2c/devices/3-0045/sensor_W"
gpu_power = "/sys/bus/i2c/devices/3-0044/sensor_W"
mem_power = "/sys/bus/i2c/devices/3-0041/sensor_W"
