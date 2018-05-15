import perf_module as perf

for i in range(100):
	print(perf.cycle_count())
	print(perf.inst_count())
