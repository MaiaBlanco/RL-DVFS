import perf_module as perf
import time

perf.reset_counters()
for i in range(100):
	print(perf.cycle_count())
	print(perf.inst_count())

print("\n\nTesting getting counters over time:")

for i in range(10):
	l = perf.perf_w_period(100);
	print(l)
