'''
# State space:
Core 4 branch misses
Core 4 instructions per cycle
Core 4 L2 misses per instruction
Core 4 temperature
Core 5 branch misses
Core 5 instructions per cycle
Core 5 L2 misses per instruction
Core 5 temperature
Core 6 branch misses
Core 6 instructions per cycle
Core 6 L2 misses per instruction
Core 6 temperature
Core 7 branch misses
Core 7 instructions per cycle
Core 7 L2 misses per instruction
Core 7 temperature
Big cluster power
Estimated big cluster leakage power
'''

# Dimensions of state space:
BUCKETS = 10
VARS = 18
FREQS = 19
# Epsilon
E = 0.01
# Update period in seconds
PERIOD = 0.100
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
