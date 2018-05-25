#ifndef PERF_PARAMS
#define PERF_PARAMS

#define DEFAULT_PERIOD_MS 100

// Events of interest, aside from cycles:
#define INST_RET 0x08 			// Instructions retired
#define BRANCH_MISPRED 0x10		// branch misprediction
#define DATA_MEM_ACCESS 0x13	// Access to data memory 
								// (assumed to RAM, past LLC)
#define L2_DATA_REFILL 0x17		// L2 Cache miss 

// Register assignments in CP15 PMU in ARM cores:
#define COUNTER_INST 0
#define COUNTER_MISPRED 1
#define COUNTER_DMEMA 2
#define COUNTER_L2R 3

#define CNTR_MASK 0xffffffff

// Setting for perf counters. 
// 1 enables all counters, 16 enables event exporting to external devices.
// Setting 8 enables clock division such that the cycle counter counts every
// 64 cycles. 
// Setting 2 and 4 reset event counts and cycle counts respectively.
#define PERF_DEF_OPTS ( (1 << 0) | (1 << 3) )

#endif
