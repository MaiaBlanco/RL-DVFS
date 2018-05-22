'''
# State space:
Core 4 branch misses per instruction
Core 4 instructions per cycle
Core 4 L2 misses per instruction
Core 4 temperature
Core 5 branch misses per instruction
Core 5 instructions per cycle
Core 5 L2 misses per instruction
Core 5 temperature
Core 6 branch misses per instruction
Core 6 instructions per cycle
Core 6 L2 misses per instruction
Core 6 temperature
Core 7 branch misses per instruction
Core 7 instructions per cycle
Core 7 L2 misses per instruction
Core 7 temperature
Big cluster power
Estimated big cluster leakage power
'''

# Dimensions of state space:
BUCKETS = 15
VARS = 17
FREQS = 19
# Epsilon
E = 0.01
# Update period in seconds
PERIOD = 0.050
# Limit in celsius
THERMAL_LIMIT = 68
RHO = 0.0

# Defined names for state space indices:
c4bm = 0 
c4ipc = 1
c4mpi = 2
c4t = 3
c5bm = 4 
c5ipc = 5
c5mpi = 6
c5t = 7
c6bm = 8 
c6ipc = 9
c6mpi = 10
c6t = 11
c7bm = 12 
c7ipc = 13
c7mpi = 14
c7t = 15
pwr = 16
lkpwr = 17

# Estimated ranges for each value type:
bmiss_MIN = 0.0
bmiss_MAX = 2.0 
ipc_MIN = 0.0
ipc_MAX = 3.0
mpi_MIN = 0.0
mpi_MAX = 2.0
temp_MIN = 35.0
temp_MAX = 75.0
pwr_MIN = 0.25
pwr_MAX = 15.0

# Compute width of each bucket for each state dimension:
bmiss_width = (bmiss_MAX - bmiss_MIN) / BUCKETS
ipc_width = (ipc_MAX - ipc_MIN) / BUCKETS
mpi_width = (mpi_MAX - mpi_MIN) / BUCKETS
temp_width = (temp_MAX - temp_MIN) / BUCKETS
pwr_width = (pwr_MAX - pwr_MIN) / BUCKETS
