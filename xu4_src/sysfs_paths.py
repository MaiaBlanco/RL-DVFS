# This file defines strings as sysfs paths for various
# dials and control knobs available in Debian.
# fn_ prefix indicates that the string should be formatted with a
# core number

# For each cpu core
fn_cpu_core_base="/sys/devices/system/cpu/cpu{}/cpufreq/"
fn_cpu_cluster=fn_cpu_core_base+"related_cpus"
fn_cpu_max_freq=fn_cpu_core_base+"cpuinfo_max_freq"
fn_cpu_min_freq=fn_cpu_core_base+"cpuinfo_min_freq"
fn_cpu_freq_read_cpuinfo=fn_cpu_core_base+"cpuinfo_cur_freq"
fn_cpu_freq_read=fn_cpu_core_base+"scaling_cur_freq"
fn_cpu_governor=fn_cpu_core_base+"scaling_governor"
fn_cpu_max_freq_set=fn_cpu_core_base+"scaling_max_freq"
fn_cpu_min_freq_set=fn_cpu_core_base+"scaling_min_freq"
fn_cpu_freq_set=fn_cpu_core_base+"scaling_setspeed"
fn_core_enabled=fn_cpu_core_base[:-8]+"online"

# for clusters (e.g. policies on whole clusters):
fn_cluster_base="/sys/devices/system/cpu/cpufreq/policy{}/"
fn_cluster_max=fn_cluster_base+"cpuinfo_max_freq"
fn_cluster_min=fn_cluster_base+"cpuinfo_min_freq"
fn_cluster_freq_range=fn_cluster_base+"scaling_available_frequencies"
fn_cluster_cpus=fn_cluster_base+"affected_cpus"
#fn_cluster_govs=fn_cluster_base+"scaling_cur_governor"
fn_cluster_gov=fn_cluster_base+"scaling_governor"
fn_cluster_freq_read_cpuinfo=fn_cluster_base+"cpuinfo_cur_freq"
fn_cluster_freq_read=fn_cluster_base+"scaling_cur_freq"
fn_cluster_freq_set=fn_cluster_base+"scaling_setspeed"
fn_cluster_max_set=fn_cluster_base+"scaling_max_freq"
fn_cluster_min_set=fn_cluster_base+"scaling_min_freq"

# for temperatures:
fn_thermal_base="/sys/devices/virtual/thermal/thermal_zone{}/"
fn_thermal_sensor=fn_thermal_base+"temp"
fn_thermal_type=fn_thermal_base+"type"

# For voltages:
little_cluster_voltage_base="/sys/devices/platform/pwrseq/subsystem/devices/s2mps11-regulator/regulator/regulator.44/"
little_micro_volts=little_cluster_voltage_base+"microvolts"
little_max_micro_volts=little_cluster_voltage_base+"max_microvolts"
little_min_micro_volts=little_cluster_voltage_base+"min_microvolts"

big_cluster_voltage_base="/sys/devices/platform/pwrseq/subsystem/devices/s2mps11-regulator/regulator/regulator.40/"
big_micro_volts=big_cluster_voltage_base+"microvolts"
big_max_micro_volts=big_cluster_voltage_base+"max_microvolts"
big_min_micro_volts=big_cluster_voltage_base+"min_microvolts"


# Paths for GPU stats:
gpu_base = "/sys/devices/platform/11800000.mali/devfreq/devfreq0/device/devfreq/devfreq0/"
gpu_freq = gpu_base + "cur_freq"
# GPU voltage:
gpu_voltage_base="/sys/devices/platform/pwrseq/subsystem/devices/s2mps11-regulator/regulator/regulator.42/"
gpu_micro_volts = gpu_voltage_base + 'microvolts'


# Paths for memory stats:
# Memory runs at default frequency of 750000 kHz
# mem_freq_base = "/sys/class/devfreq/exynos5-devfreq-mif/"
# mem_freq = mem_freq_base + 
mem_voltage_base="/sys/devices/platform/pwrseq/subsystem/devices/s2mps11-regulator/regulator/regulator.43/"
mem_micro_volts = gpu_voltage_base + 'microvolts'
