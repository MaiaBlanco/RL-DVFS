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
FREQS = 19
LABELS = ['BMPKI', 'IPC', 'CMPKI', #'DAPKI',
						'temp', 'power']

# +1 for frequency added on the end.
VARS = len(LABELS) + 1

# Array of bools sets log scale if true:
SCALING = [ True, False, True, #True,
				False, True]
BUCKETS = \
	{
	'BMPKI':10,
	'IPC':	10,
	'CMPKI':10,
	'temp':	10,
	'power':10,
	}
# Min and max limits are in linear scale
MINS = \
	{
	# Note 1s to avoid domain error on log scaled stats:
	'BMPKI':0.1,
	'IPC':0.01,
	'CMPKI':0.01,
	'temp':30,
	'power':0.1
	}
MAXS = \
	{
	'BMPKI':80,
	'IPC':4,
	'CMPKI':80,
	'temp':80,
	'power':2
	}

#big cluster frequencies
big_freqs = [200000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000, 1100000, 1200000, 1300000, 1400000, 1500000, 1600000, 1700000, 1800000, 1900000, 2000000]
# Function to bin frequencies:
def freq_to_bucket(freq):
	global big_freqs
	return big_freqs.index(int(freq))

# N0 for epsilon calculation
N0= 100.0
# Discounting factor:
GAMMA = 0.9
# Lambda for multistep Q-learning updates:
LAMBDA = 0.6
# History length limit:
HIST_LIM = 10
# Update period in seconds
PERIOD = 0.200
# Limit in celsius
THERMAL_LIMIT = 60
RHO = 500
THETA = 10

# Defined names for state space indices:
c4bm = 0 
c4ipc = 1
c4mpi = 2
c4dmemapi = 3
# c5bm = 4 
# c5ipc = 5
# c5mpi = 6
# c5dmemapi = 7
# c6bm = 8 
# c6ipc = 9
# c6mpi = 10
# c6dmemapi = 11
# c7bm = 12 
# c7ipc = 13
# c7mpi = 14
# c7dmemapi = 15
# pwr = 16
# lkpwr = 17
