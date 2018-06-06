import numpy as np
from multiprocessing import Array, Process
import subprocess, os, sys
import ctypes
import time
import random
import atexit
import select
import copy

# Local imports:
import sysfs_paths as sfs
import devfreq_utils as dvfs
from state_space_params import *
import therm_params as tm
from therm_params import big_f_to_v_MC1 as vvf_dict

# Filesystem monitoring:
watchers = [None] * 4
watcher_files = [None] * 4
# Multicore policy requested frequencies:
requested_freqs =  Array('i', 8, lock=True)
for i in requested_freqs:
    i = 200000
runners =  [None]*4

num_buckets = np.array([BUCKETS[k] for k in LABELS], dtype=np.double)
if FREQ_IN_STATE:
    dims = [int(b) for b in num_buckets] + [FREQS] + [ACTIONS]  
else:
    dims = [int(b) for b in num_buckets] + [ACTIONS]
print(dims)
Q = np.zeros( dims ) 
# Note: C is no longer used to keep track of exact counts, but if a state action has been seen ever.
C = np.zeros( dims ) 
# For bucketing stats:
all_mins = np.array([MINS[k] for k in LABELS], dtype=np.double)
all_maxs = np.array([MAXS[k] for k in LABELS], dtype=np.double)
widths = np.divide( np.array(all_maxs) - np.array(all_mins), num_buckets)
# VVF values and max IPS for reward_func:
# Note in this dict the freqs are in GHz, but elsewhere in this code they are KHz.
fslist = [f for f in vvf_dict.keys()]
fslist.sort()
vvfs = [f*1000000.0 * (vvf_dict[f]**2) for f in fslist]
print(vvfs)
VVF_max = vvfs[-1]
VVF_min = vvfs[0]
IPC_max = 4
IPS_max = fslist[-1] * 1000000000.0 * IPC_max
print(IPS_max)

###########################################################################
# State-Action value space checkpointing and system initialization:

def checkpoint_statespace():
    global Q
    yn = str(raw_input("Save statespace? (y/n)") ).lower()
    while yn != 'y' and yn != 'n':
        yn = str(raw_input("Enter y/n: ")).lower()
    if yn == 'n':
        return
    ms_period = int(PERIOD*1000)
    np.save("Q_{}ms.npy".format(ms_period), Q)
    #np.save("C_{}ms.npy".format(ms_period), C)

def load_statespace():
    global Q, C
    ms_period = int(PERIOD*1000)
    try:
        Q_t = np.load("Q_{}ms.npy".format(ms_period))
        #C_t = np.load("C_{}ms.npy".format(ms_period))
    except:
        raise Exception("Could not read previous statespace")
        return
    if Q_t.shape != Q.shape:
        raise Exception("Mismatched loaded state space to desired statespace.")
    else:
        Q = Q_t

def init():
    # Make sure perf counter module is loaded:
    process = subprocess.Popen(['lsmod'], stdout=subprocess.PIPE)
    output, err = process.communicate()
    loaded = "perfmod" in output
    if not loaded:
        print("WARNING: perf-counters module not loaded. Loading...")
        process = subprocess.Popen(['sudo', 'insmod', 'perfmod.ko'])
        output, err = process.communicate()
    # Set sampling period for kernel module:
    ms_period = int(PERIOD*1000)
    set_period(ms_period)
    print("Running with period: {} ms".format(ms_period))       
    # Set userspace on the big cluster:
    dvfs.setUserSpace(4)

###########################################################################



###########################################################################
# Interfacing functions to sysfs endpoints for performance kernel module:

def get_counter_value(cpu_num, attr_name):
    with open("/sys/kernel/performance_counters/cpu{}/{}".format(cpu_num, attr_name), 
                'r') as f:
        val = float(f.readline().strip())
    return val


def set_period(p):
    for cpu_num in range(4,8):
        with open("/sys/kernel/performance_counters/cpu{}/sample_period_ms".format(cpu_num), 
                'w') as f:
            f.write("{}\n".format(p))

'''
Basically barrier on the counter update being performed by the kernel module.
'''
def synch_to_counter_update(cpu_num):
    val = 0
    with open("/sys/kernel/performance_counters/cpu{}/cycles".format(cpu_num), 'r') as f:
        val = float(f.readline().strip())
    with open("/sys/kernel/performance_counters/cpu{}/cycles".format(cpu_num),'r') as f:
        while int(f.readline().strip() == val):
            continue

###########################################################################



###########################################################################
# Q Learning implementation:

'''
Returns state figures, non-quantized.
Includes branch misses per Kinstruction, IPC, and l2miss, data memory accesses 
per Kinstruction for each core, plus core temp and big cluster power. 
'''
def get_raw_state(cpu):    
    # Get the change in counter values:    
    cpu_freq = dvfs.getClusterFreq(cpu)
    # Multiply by period and frequency by 1000 to get total
    # possible cpu cycles.
    cycles_possible = float(cpu_freq * 1000 *  PERIOD)
    cycles_used = get_counter_value(cpu, "cycles")
    bmisses = get_counter_value(cpu, "branch_mispredictions")
    instructions = get_counter_value(cpu, "instructions_retired")
    l2misses = get_counter_value(cpu, "l2_data_refills")
    dmemaccesses = 0.0 #get_counter_value(cpu, "data_memory_accesses")
    T = [float(x) for x in dvfs.getTemps()]
    # Throughput stats:
    IPC_u = instructions / cycles_used
    IPC_p = instructions / cycles_possible
    IPS   = instructions / PERIOD
    MPKI  = l2misses / (instructions / 1000.0)
    BMPKI = bmisses / (instructions / 1000.0)
    DAPKI = dmemaccesses / (instructions / 1000.0)
    # Collect all possible state:
    all_stats = {
        'BMPKI':BMPKI, 
        'IPC_u':IPC_u, 
        'IPC_p':IPC_p, 
        'MPKI' :MPKI, 
        'DAPKI':DAPKI,
        'temp' :T[cpu-4], 
        'freq' :cpu_freq,
        'volt' :tm.big_f_to_v_MC1[float(cpu_freq) / 1000000],
        'usage':cycles_used/cycles_possible,
        'IPS'  :IPS
        }
    return all_stats

'''
Place state in 'bucket' given min/max values and number of buckets for each value.
Use bucket width to determine index of each raw state value after scaling values on linear or log scale.
'''
def bucket_state(raw):
    global num_buckets, all_maxs, all_mins, widths
    global labels   

    raw_no_freq = [raw[k] for k in LABELS] 
    # Bound raw values to min and max from params:
    raw_no_freq = np.clip(raw_no_freq, all_mins, all_maxs)
    # Floor values for proper bucketing:
    raw_floored = raw_no_freq - all_mins
    state = np.divide(raw_floored, widths)
    state = np.clip(state, 0, num_buckets-1)
    if FREQ_IN_STATE:
        # Add frequency index to end of state:
        state = np.append(state, [ freq_to_bucket[ raw['freq'] ] ])
    # Convert floats to integer bucket indices and return:
    return [int(x) for x in state]

''' 
Reward function: Performance, Power, and Thermal-aware.
'''
def reward_func(stats, new_freq):
    global RHO, LAMBDA # <-- From state space params module.
    global IPS_max, VVF_min, VVF_max, vvf_dict
    global THERMAL_LIMIT
    
    IPS = stats['IPS']
    temp = stats['temp']
    freq = stats['freq'] #new_freq
    volts = stats['volt'] #vvf_dict[new_freq / 1000000.0] 
    # VVF and power:
    vvf = (volts ** 2) * float(freq)
    vvf_n = ( vvf - VVF_min) / VVF_min
    power_penalty = LAMBDA * vvf_n
    # Thermal term:
    thermal_v = max(temp - THERMAL_LIMIT, 0.0)
    thermal_penalty = RHO * thermal_v * ( vvf / VVF_max )
    # Throughput:
    thpt_reward = IPS / IPS_max
    # Debug printouts:
    print("VVFn:",vvf_n)
    print("IPSn:",thpt_reward)
    print("Power Penalty:",power_penalty)
    print("Thermal Penalty:",thermal_penalty)
    # Return overall reward:
    reward = thpt_reward - power_penalty - thermal_penalty
    return reward


# Greedy Q-Learning Update
# Given previous and last state, action and reward between them (one-step), update
# based on greedy policy.
def update_Q_off_policy(last_state, last_action, reward, state):
    global Q, GAMMA, ALPHA
    # Follow greedy policy at new state to determine best action:
    best_next_return = np.max(Q[ tuple(state) ] )
    # Total return:
    total_return = reward + GAMMA*best_next_return
    # Update last_state estimate:
    old_value = Q[ tuple(last_state + [last_action] ) ]
    Q[ tuple(last_state + [last_action] ) ] = old_value + ALPHA*(total_return - old_value) 
    return Q[ tuple(last_state + [last_action] ) ]

'''
Q-learning driver function. Uses global state space LUTs (Q, C) to hold
state-action value estimates and state-action counts. 
On call tries to load previous state space value estimates and counts; 
if unsuccessful starts from all 0s.
'''
def Q_learning(cpu):
    global num_buckets
    global big_freqs
    global Q, EPSILON
    
    # Take care of statespace checkpoints:
    try:
        load_statespace()
        print("Loaded statespace")
    except:
        print("Could not load statespace; continue with fresh.")
    atexit.register(cleanup, checkpoint=True)
    
    # Init runtime vars:
    last_action = None
    last_state = None
    reward = None
    bounded_freq_index=0
    cur_freq_index=0
    # Synchronize to kernel sampler:
    #synch_to_counter_update(cpu)
    # Register inotify event with linux kernel:
    watchers[cpu-4] = select.poll()
    watcher_files[cpu-4] = open("/sys/kernel/performance_counters/cpu{}/data_memory_accesses".format(cpu), 'r')
    watchers[cpu-4].register(watcher_files[cpu-4], select.POLLPRI | select.POLLERR )
    # Learn forever:
    while True:
        start = time.time()
        
        # get current state and reward from last iteration:
        stats = get_raw_state(cpu)
        state = bucket_state(stats)
        
        # Update state-action-reward trace:
        if last_action is not None:
            print("Prev state and action taken:")
            print([last_stats[k] for k in LABELS] + [last_stats['freq']])
            print(last_state, last_action)
            reward = reward_func(stats, big_freqs[last_action]) 
            print("Results (Reward):",reward)
            update_Q_off_policy(last_state, last_action, reward, state)
            print()
        else:
            reward = reward_func(stats, big_freqs[0]) 


        # Apply EPSILON randomness to select a random frequency:
        if random.random() < EPSILON:
            best_action = random.randint(0, ACTIONS-1)
        # Or greedily select the best frequency to use given past experience:
        else:
            best_action = np.argmax(Q[ tuple(state) ])
            '''
            # Note: numpy's argmax sensibly returns the lowest value if all have the same
            # value. Therefore, when we have all the same, behavior should really be random.
            if C[ tuple(state + [best_action]) ] == 0:
                best_action = random.randint(0, ACTIONS-1)
            '''
        # Take action.
        # (note big_freqs is lookup table from state_space module).
        # Also counter increment is performed in Q off policy update function.
        dvfs.setClusterFreq(cpu, big_freqs[best_action])
        '''     
        if ACTIONS == FREQS:
            dvfs.setClusterFreq(4, big_freqs[best_action])
        else:
            stay = ACTIONS // 2
            cur_freq_index = freq_to_bucket[ stats['freq'] ]
            cur_freq_index += (best_action - stay)
            bounded_freq_index = max( 0, min( cur_freq_index, FREQS-1))
            dvfs.setClusterFreq(4, big_freqs[bounded_freq_index])
        '''     
        # Save state and action:
        last_state = state
        last_action = best_action
        last_stats = stats
        '''
        C[ tuple(state + [best_action]) ] += 1 
        '''

        # Wait for next period. Note that reward cannot be evaluated 
        # at least until the period has expired.
        elapsed = time.time() - start
        print("Elapsed:",elapsed)
        #time.sleep(max(0, PERIOD - elapsed))
        watcher_files[cpu-4].read()
        watcher_files[cpu-4].seek(0)
        res = watchers[cpu-4].poll()
        end = time.time()
        print("Total:",end-start)


###########################################################################


###########################################################################
# Offline policy running (not learning):

'''
Use global lookup table (LUT) Q to select best action based on quantized state.
This implementation applies learned Q 'function' to core 4 only.
'''
def run_offline(cpu, requested_freqs_array):
    print("Started offline policy on core", cpu)
    global Q
    global big_freqs
    global watchers, watcher_files,requested_freqs
    global lock
    # Synchronize to kernel sampler:
    #synch_to_counter_update(cpu)
    # Register inotify event with linux kernel:
    watchers[cpu-4] = select.poll()
    watcher_files[cpu-4] = open("/sys/kernel/performance_counters/cpu{}/data_memory_accesses".format(cpu), 'r')
    watchers[cpu-4].register(watcher_files[cpu-4], select.POLLPRI | select.POLLERR )
    # Run offline greedy policy:
    while True:
        start = time.time()
        
        # get current state:
        stats = get_raw_state(cpu)
        state = bucket_state(stats)

        # Greedily select the best frequency to use given past experience:
        best_action = np.argmax(Q[ tuple(state) ])

        # Take action.
        # (note big_freqs is lookup table from state_space module).
        if requested_freqs_array is not None:
            with requested_freqs_array.get_lock():
                requested_freqs_array[(cpu-4)*2] = int(big_freqs[best_action])
                requested_freqs_array[(cpu-4)*2+1] = int(stats['temp'])
            #print("Updated frquency ",cpu, big_freqs[best_action])
        else:
            dvfs.setClusterFreq(cpu, big_freqs[best_action])
        ''' 
        if ACTIONS == FREQS:
            #dvfs.setClusterFreq(4, big_freqs[best_action])
                requested_freqs[cpu-4] = (big_freqs[best_action], stats['temp'])
        else:
            stay = ACTIONS // 2
            cur_freq_index = freq_to_bucket[ stats['freq'] ]
            cur_freq_index += (best_action - stay)
            bounded_freq_index = max( 0, min( cur_freq_index, FREQS-1))
            #dvfs.setClusterFreq(4, big_freqs[bounded_freq_index])
                requested_freqs[cpu-4] = (big_freqs[bounded_freq_index], stats['temp'])
        '''     
        # Print state and action:
        #print([stats[k] for k in LABELS])
        #print(state, best_action)

        # Wait for next period. 
        elapsed = time.time() - start
        #print("Elapsed:", elapsed)
        #time.sleep(max(0, PERIOD - elapsed))
        watcher_files[cpu-4].read()
        watcher_files[cpu-4].seek(0)
        res = watchers[cpu-4].poll()
        end = time.time()
        #print("Total:", end-start)
    
'''
Compare two requests:
Could sort by recency, but the processes will be updating pretty quickly. 
Instead, sort first by frequency requested (need) and then by temperature (risk)
'''
def request_sort(x, y):
    freq_x = x[0]
    freq_y = y[0]
    t_x = x[1]
    t_y = x[1]
    if freq_x < freq_y:
        return -1
    elif freq_x > freq_y:
        return 1
    elif t_x < t_y:
        return -1
    elif t_x > t_y:
        return 1
    else:
        return 0
    


def update_freqs(array):
    with array.get_lock():
        local_suggestions = [ x for x in requested_freqs]
    things = []
    for i in range(len(local_suggestions)/2):
        things.append( [local_suggestions[i*2], local_suggestions[i*2+1] ] )
    sorted_requests = sorted(things, cmp=request_sort)
    dvfs.setClusterFreq(4, sorted_requests[-1][0])
    print(things, sorted_requests[-1][0])



'''
Use global lookup table (LUT) Q to select best action based on quantized state.
This implementation applies learned Q 'function' from core 4 to all big cores.
'''
def run_offline_multicore():
    global runners
    # Launch individual core policies:
    global requested_freqs
    for core_num in range(4,8):
        runners[core_num-4] = Process(target=run_offline, args=( core_num, requested_freqs) )
        runners[core_num-4].start()

    # Continue to monitor 'suggested' frequencies and update as appropriate:
    while True:
        start = time.time()
        update_freqs(requested_freqs)
        time.sleep(max( 0, PERIOD - (time.time() - start)) )




###########################################################################


###########################################################################
# Main and usage:

def usage():
    print("USAGE: {} <train|run>".format(sys.argv[0]))
    sys.exit(0)

def cleanup(checkpoint=False):
    global watchers, runners, watcher_files
    if checkpoint:
        checkpoint_statespace()
    for w, f in zip(watchers, watcher_files):
        if w is not None:
            w.unregister(f)
            f.close()
        for r in runners:
            if r is not None:
                r.terminate()

def try_load():
    # load state-action space values from Q file: 
    try:
        load_statespace()
        print("Loaded statespace")
    except:
        print("Could not load statespace. State space Q must be trained with Q learning function.")
        sys.exit(1)

if __name__ == "__main__":
    init()
    if len(sys.argv) > 1:
        if sys.argv[1] == "run":
            try_load()
            if len(sys.argv) > 2 and sys.argv[2] == 'all':
                print("Running on all 4 cores.")
                run_offline_multicore() 
            else:
                run_offline(4, None)
        
        elif sys.argv[1] == "train":
            Q_learning(4)
        else:
            usage()
    else:
        print("No args given; defaulting to training in 5 seconds.")
        time.sleep(5)
        Q_learning(4)

###########################################################################
