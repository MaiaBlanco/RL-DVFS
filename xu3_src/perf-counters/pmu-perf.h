/*
	Description: Configuration and counter access declarations 
		for ARM performance counters kernel module, for use on 32-bit 
		ARM cortex-A processors (specifically A-7, A-15, and A-53 in v7 mode).
			
			If additional or different performance counters 
			are desired for the kernel module's functionality 
			(and for them to show up in sysfs), then the 
			struct instances in sysfs-perf.c should be updated to 
			reflect the names and quantity of the counter events. 

			Additionally, performance counter event codes must be
			added to params-perf.h for the code in this file to 
			select and enable the right counters. Be sure not to 
			try enabling more counters than your CPU supports!

			For more information, see the ARMv7 architecture
			reference manual and the reference manual for your 
			Cortex A ARMv7 processor.
	
	Date: 25 May 2018
	Author: Mark Blanco <markb1@andrew.cmu.edu>
*/

#ifndef PMU_PERF
#define PMU_PERF

#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
// For timing with jiffies:
#include <linux/sched.h>
#include <linux/jiffies.h>
// For kernel threading:
#include <linux/kthread.h>
// For outputting perf counters to sysfs:
#include <linux/sysfs.h>
#include <linux/fs.h>
#include <linux/string.h>
// More includes:
#include <linux/cpu.h>
#include <linux/delay.h>
#include <linux/timer.h>
#include <linux/time.h>
// For kobject stuff (to have sysfs endpoints):
#include <linux/kobject.h>
#include <linux/slab.h>

// Setting for perf counters. 
// 1 enables all counters, 16 enables event exporting to external devices.
// Setting 8 enables clock division such that the cycle counter counts every
// 64 cycles. 
// Setting 2 and 4 reset event counts and cycle counts respectively.
#define PERF_DEF_OPTS ( (1 << 0) )

// Events of interest, aside from cycles:
#define INST_RET 0x08 			// Instructions retired
#define BRANCH_MISPRED 0x10		// branch misprediction
#define DATA_MEM_ACCESS 0x13	// Access to data memory 
								// (assumed to RAM, past LLC)
#define L2_DATA_REFILL 0x17		// L2 Cache miss 

// The number of counters to be enabled, aside from the cycle counter.
#define NUM_COUNTERS 4

// Function prototypes for PMU interfacing:
// Disable perf counters and userspace access to them:
void disable_cpu_counters(void* data);
// Enable the CPU counters #defined above; enable userspace access, etc:
unsigned int enable_cpu_counters(void * data);


// Inline function definitions:

static inline 
unsigned int read_cycle_count(void)
{
	unsigned int c;
	// Read cycle count register:
	asm volatile("mrc p15, 0, %0, c9, c13, 0" : "=r"(c));
	return c;
}

// Select and read performance counter register number 'reg_num'
static inline 
unsigned int read_p15_count(unsigned int reg_num)
{
	unsigned int c;
	// Select correct register:
	asm volatile("mcr p15, 0, %0, c9, c12, 5" :: "r"(reg_num));
	// Read that register:
	asm volatile("mrc p15, 0, %0, c9, c13, 2" : "=r"(c));
	return c;
}

static inline 
void reset_counters(void)
{
	unsigned int v;
	// Read the original value to preserve settings:
	asm volatile("mrc p15, 0, %0, c9, c12, 0" : "=r"(v));
	// Reset the performance counters by setting bits 1 and 2:
	asm volatile("mcr p15, 0, %0, c9, c12, 0" :: "r"(v | (1 << 2) | (1 << 1)));
}
#endif
