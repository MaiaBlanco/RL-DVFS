import perf_module as perf
import time

perf.reset_counters()
print('Cycles\t\tInstructions')
for i in range(10):
	print(perf.cycle_count(), perf.inst_count())
	time.sleep(0.1)

print("\n\nTesting getting counters over time:")

perf.reset_counters()
for i in range(10):
	l = perf.perf_w_period(100);
	print("cycles: {}\t\tinstructions: {}\t\t"\
		"branch misses: {}\t\tDmem Access: {}\t\tl2 refill:{}".format(
			l[0], l[1], l[2], l[3], l[4]))
