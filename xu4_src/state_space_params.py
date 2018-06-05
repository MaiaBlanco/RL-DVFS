# Dimensions of state space:
FREQS = 10
ACTIONS = FREQS
FREQ_STEP = 2
FREQ_IN_STATE=1
LABELS = [ 	\
		#'BMPKI', 
		#'IPC_u', 
		#'usage',
		'IPC_p', 
		'MPKI', 
		#'DAPKI',
		'temp', 
		#'power'
		]

# +1 for frequency added on the end.
VARS = len(LABELS) + FREQ_IN_STATE

BUCKETS = \
	{
#	'BMPKI':10,
#	'IPC_u':15,
#	'usage':10,
	'IPC_p':10,
	'MPKI' :5,
	'temp' :6,
#	'power':10,
	}
# Min and max limits are in linear scale
MINS = \
	{
	'BMPKI':0.0,
	'usage':0.0,
	'IPC_u':0.0,
	'IPC_p':0.0,
	'MPKI':0.0,
	'temp':44.0,
	'power':0.0
	}
MAXS = \
	{
	#'BMPKI':80,
	'usage':1.2,
	'IPC_u':3.0,
	'IPC_p':3.0,
	'MPKI':4.0,
	'temp':56.0,
	'power':4.0
	}

#big cluster frequencies
big_freqs_base = [200000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000, 1100000, 1200000, 1300000, 1400000, 1500000, 1600000, 1700000, 1800000, 1900000, 2000000]
big_freqs = big_freqs_base[0::FREQ_STEP]
print(big_freqs_base)
print(big_freqs)
# freq to bin indices:
freq_to_bucket = {big_freqs[i]:i for i in range(len(big_freqs))}

EPSILON = 0.20
# Discounting factor:
GAMMA = 0.90
# Lambda for multistep Q-learning updates:
#LAMBDA = 0.6
ALPHA = 0.1
# Update period in seconds
PERIOD = 0.050
# Limit in celsius
THERMAL_LIMIT = 50
# Thermal limit coefficient
RHO = 5
# Power coefficient:
LAMBDA = 0.001
