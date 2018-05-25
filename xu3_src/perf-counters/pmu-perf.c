/*
	Description: Configuration and counter access implementations
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
#include "pmu-perf.h"

const unsigned int counters[] = {INST_RET, BRANCH_MISPRED, DATA_MEM_ACCESS, L2_DATA_REFILL};

// Function definitions for PMU interfacing:

// Disable perf counters and userspace access to them:
void disable_cpu_counters(void* data)
{
	/* Disable Everything */
	// Disable user-mode access
	asm volatile("mcr p15, 0, %0, c9, c14, 0" :: "r"(0));
	// Disable Count
	asm volatile("mcr p15, 0, %0, c9, c12, 2" :: "r"(0xffffffff));
	// Disable Interrupts
	asm volatile("mcr p15, 0, %0, c9, c14, 2" :: "r"(0xffffffff));
	// Reset counts and disable counters
	asm volatile("mcr p15, 0, %0, c9, c12, 0" :: "r"((1 << 1) | (1 << 2)));
	// Clear Overflow Register
	asm volatile("mcr p15, 0, %0, c9, c12, 3" :: "r"(0xffffffff));
}
// Enable the CPU counters #defined in params-perf.h; enable userspace access, etc:
unsigned int enable_cpu_counters(void * data)
{
	unsigned int cpuid, i;
	/* Read cpucode from core */
	asm volatile("mrc p15, 0, %0, c9, c12, 0" : "=r"(cpuid));
	cpuid &= (0x00ff << 16);
	cpuid = cpuid >> 16;

	disable_cpu_counters(NULL);
	
	// Disable event filtering on clock. 
	// Note: requires PMUv2 as defined in ARM arch manual
	asm volatile("mcr p15, 0, %0, c9, c12, 5" :: "r"(0b11111));
	asm volatile("mcr p15, 0, %0, c9, c13, 1" :: "r"(0));

	// Setup the count registers to track events of interest (listed @ top of file):
	for(i = 0; i < NUM_COUNTERS; ++i)
	{
		asm volatile("mcr p15, 0, %0, c9, c12, 5" :: "r"(i));
		asm volatile("mcr p15, 0, %0, c9, c13, 1" :: "r"(counters[i]));
	}
	//Enable cycle count + counters (2**NUM_COUNTERS-1)
	asm volatile ("mcr p15, 0, %0, c9, c12, 1" :: "r"((1 << 31) | ((2 << NUM_COUNTERS)-1)));
	// Enable counters
	asm volatile ("mcr p15, 0, %0, c9, c12, 0" :: "r"(PERF_DEF_OPTS));
	// Enable user-mode access to counters
	asm volatile("mcr p15, 0, %0, c9, c14, 0" :: "r"(1));
	
	return cpuid;
}

