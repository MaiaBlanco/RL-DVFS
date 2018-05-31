# Dimensions of state space:
ACTIONS = 5
FREQS = 19
FREQ_IN_STATE=1
LABELS = [ 	\
		#'BMPKI', 
		#'IPC_u', 
		'usage',
		'IPC_p', 
		'MPKI', 
		#'DAPKI',
		'temp', 
		#'power'
		]

# +1 for frequency added on the end.
VARS = len(LABELS) + FREQ_IN_STATE

# Array of bools sets log scale if true:
SCALING = [ False ] * len(LABELS)
BUCKETS = \
	{
	#'BMPKI':10,
	#'IPC_u':10,
	'usage':10,
	'IPC_p':10,
	'MPKI' :15,
	'temp' :20,
	'power':15,
	}
# Min and max limits are in linear scale
MINS = \
	{
	# Note 0..1s to avoid domain error on log scaled stats:
	#'BMPKI':0.1,a
	'usage':0.01,
	'IPC_u':0.01,
	'IPC_p':0.01,
	'MPKI':0.01,
	'temp':30,
	'power':0.1
	}
MAXS = \
	{
	#'BMPKI':80,
	'usage':2,
	'IPC_u':3,
	'IPC_p':3,
	'MPKI':10,
	'temp':75,
	'power':4
	}

#big cluster frequencies
big_freqs = [200000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000, 1100000, 1200000, 1300000, 1400000, 1500000, 1600000, 1700000, 1800000, 1900000, 2000000]
# Function to bin frequencies:
def freq_to_bucket(freq):
	global big_freqs
	return big_freqs.index(int(freq))

# N0 for epsilon calculation
EPSILON = 0.25
# Discounting factor:
GAMMA = 0.9
# Lambda for multistep Q-learning updates:
#LAMBDA = 0.6
ALPHA = 0.1
# History length limit:
#HIST_LIM = 10
# Update period in seconds
PERIOD = 0.100
# Limit in celsius
THERMAL_LIMIT = 50
# Thermal limit coefficient
RHO = 10
# Power penalty coefficient
THETA = 05

