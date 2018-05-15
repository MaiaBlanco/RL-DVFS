#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>

// Events of insterest, aside from cycles:
#define INST_RET 0x08 			// Instructions retired
#define BRANCH_MISPRED 0x10		// branch misprediction
#define DATA_MEM_ACCESS 0x13	// TODO: make sure this is in fact
								// an L2 cache miss.
#define L2_DATA_REFILL 0x17		// This might actually be the right one...

// Setting for perf counters. 
// 1 enables all counters, 16 enables event exporting to external devices.
// Setting 8 enables clock division such that the cycle counter counts every
// 64 cycles. 
// Setting 2 and 4 reset event counts and cycle counts respectively.
#define PERF_DEF_OPTS (1 | 16)

static void enable_cpu_counters(void * data)
{
	/* Enable user-mode access to counters. */
	asm volatile("mcr p15, 0, %0, c9, c14, 0" :: "r"(1));
	// Program PMU and enable all counters, and also reset counts:
	asm volatile("mcr p15, 0, %0, c9, c12, 0" :: "r"(PERF_DEF_OPTS | 2 | 4));
	// Enable cycle count register and 4 other event registers:
	asm volatile("mcr p15, 0, %0, c9, c12, 1" :: "r"(0x8000000f));
	// Disable counter overflow interrupts:
	asm volatile("mcr p15, 0, %0, c9, c14, 2" :: "r"(0x8000000f));
	
	// Setup the 4 other registers to track events of interest (listed @ top of file):
	// Select first programmable event register:
	asm volatile("mcr p15, 0, %0, c9, c12, 5" :: "r"(1));
	asm volatile("mcr p15, 0, %0, c9, c13, 1" :: "r"(INST_RET));

	// Select second programmable event reg:
	asm volatile("mcr p15, 0, %0, c9, c12, 5" :: "r"(2));
	asm volatile("mcr p15, 0, %0, c9, c13, 1" :: "r"(BRANCH_MISPRED));

	// Select third programmable event reg:
	asm volatile("mcr p15, 0, %0, c9, c12, 5" :: "r"(3));
	asm volatile("mcr p15, 0, %0, c9, c13, 1" :: "r"(DATA_MEM_ACCESS));

	// Select fourth programmable event reg:
	asm volatile("mcr p15, 0, %0, c9, c12, 5" :: "r"(4));
	asm volatile("mcr p15, 0, %0, c9, c13, 1" :: "r"(L2_DATA_REFILL));
	
}

static void disable_cpu_counters(void* data)
{
	/* Disable user-mode access to counters. */
	asm volatile("mcr p15, 0, %0, c9, c14, 0" :: "r"(0));
	// Disable all counters (cycle counter and the 4 others): 
	asm volatile("mcr p15, 0, %0, c9, c12, 1" :: "r"(0x00000000));
	// Reset PMU counters and reset clock div settings, etc.:
	asm volatile("mcr p15, 0, %0, c9, c12, 0" :: "r"(0x00000007));
}

int init_module(void)
{
	pr_info("Performance counter kmod for XU3.\n");
	// Setup here:
	on_each_cpu(enable_cpu_counters, NULL, 1);
	printk(KERN_INFO "[ RL_PERF ] initialized");
	return 0;
}

void cleanup_module(void)
{
	//on_each_cpu(disable_cpu_counters, NULL, 1);
	pr_info("Cleaning up perf counter kmod for XU3.\n");
	printk(KERN_INFO "[ RL_PERF ] unloaded.");
}

