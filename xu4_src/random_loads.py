import subprocess
import signal
import random
import time
import os

FNULL = open(os.devnull, 'w')

bench_prob = 0.3
period_max = 600
bench_processes = []
other_processes = []
path = "/home/odroid/hw1_files/parsec_files/"
inputs = [path + 'sequenceB_261/', path + 'in_10M_blackscholes.txt']
cmd = 'taskset --all-tasks ' + '{} {}'

benchmarks = [ path + 'bodytrack', path + 'blackscholes' ]

random.seed()
while True:
	for i in range(len(bench_processes)-1, -1, -1):
		if bench_processes[i].poll() is not None:
			del bench_processes[i]
	# Roll a die:
	d = random.random()
	if d <= bench_prob:
		if len(bench_processes) == 0:
			try:
				print("starting new run")
				# launch a new benchmark
				affinity_l = 0#random.randint(0, 15)
				affinity_b = 14 #random.randint(2, 2) #15)
				affinity = affinity_l | (affinity_b << 4)
				affinity_string = hex(affinity)
				num_threads = bin(affinity).count("1")#random.randint(1, bin(affinity).count("1"))
				bm_index = random.randint(0,1)
				if bm_index == 0: # bodytrack
					cmd_bm_args = ' {} 4 260 3000 8 3 {} 0'.format(inputs[bm_index], num_threads)
					#cmd_f = cmd.format(affinity_string, cmd_bm)
				elif bm_index == 1: # Blackscholes
					cmd_bm_args = ' {} {} /dev/null'.format(num_threads, inputs[bm_index])
					#cmd_f = cmd.format(affinity_string, cmd_bm)
				#print(cmd_f.split(' '))
				bench_processes.append(subprocess.Popen(['/bin/sh', './parsec.sh', affinity_string, benchmarks[bm_index], \
						cmd_bm_args], preexec_fn=os.setsid))
			except:
				continue
	else:
		continue
		'''
		if len(bench_processes) > 0:
			# Kill the process and idle:
			print("Killing process")
			os.killpg(os.getpgid(bench_processes[0].pid), signal.SIGTERM)
			#bench_processes[0].kill()
			del bench_processes[0]
		'''	
	wait_time = random.randint(0, period_max)
	print("Waiting for {} minutes.".format(wait_time/60.0))
	time.sleep(wait_time)

