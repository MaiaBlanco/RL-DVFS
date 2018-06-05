#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
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

#include "pmu-perf.h"
#include "sysfs-perf.h"

// License (required to load module that writes to sysfs anyways):
MODULE_LICENSE("Dual BSD/GPL");
MODULE_AUTHOR("Mark Blanco <markb1@andrew.cmu.edu>");


// Sampling period can be changed per-core from the sysfs interface at
// '/sys/kernel/performance_counters/cpu*/sample_period_ms
#define DEFAULT_PERIOD_MS 50

// Adds printouts for timing and measure cpu cycles in kthread function:
#define DEBUG 0

// If defined, RESTRICT_CPU causes perf counter kthread to run on just
// the CPU core with the number specified.
#define RESTRICT_CPU 4


struct my_perf_data_struct {
	// cycles
	unsigned int cycles;
	unsigned int counterVal[NUM_COUNTERS];
};

//extern struct cpu_counter_obj* create_cntr_obj(const char* name, struct kset* parent);
//extern void destroy_cntr_obj(struct cpu_counter_obj* obj);

// Create unifying kset for all cpu counter objects:
static struct kset* cntr_kset;
// Create counter objects on each CPU:
DEFINE_PER_CPU(struct cpu_counter_obj, my_cpu_counter_obj);
// Create some data instances on all CPUs, bound to each CPU:
DEFINE_PER_CPU(struct my_perf_data_struct, my_perf_data);
DEFINE_PER_CPU(struct my_perf_data_struct*, my_perf_data_ptr);

struct task_struct* task[8];
int data;
int ret;


int perf_thread(void * data)
{
	// Get core id:
	unsigned int coreid = smp_processor_id();
	char name[] = "cpu_\0";

	// Timing:
	struct timeval tm1, tm2;
	unsigned long elapsed;
#if DEBUG
	unsigned long elapsed2; 
	struct timeval tm3;
#endif
	// Data holding:
	unsigned int sample_period_ms, cpuid;
	unsigned int i = 0;
	struct my_perf_data_struct* my_perf_data_local;
	struct cpu_counter_obj* my_cpu_counter_obj_local;

	// Create representative sysfs object:
	name[3] = (char)(coreid + '0');
	my_cpu_counter_obj_local = create_cntr_obj(name, cntr_kset);
	if (!my_cpu_counter_obj_local)
	{
		goto KTHREAD_END;
	}
	
	// Start perf counters on CPU:
	cpuid = enable_cpu_counters(NULL);
	printk(KERN_INFO "[perf] CPU %d of type %u\n", coreid, cpuid);
	schedule();

	while(!kthread_should_stop())
	{
		// Update sample period:
		sample_period_ms = my_cpu_counter_obj_local->sample_period_ms;
		// Get change in each counter
		do_gettimeofday(&tm1);

		my_perf_data_local = &get_cpu_var(my_perf_data);

		my_perf_data_local->cycles = read_cycle_count();
		for(i = 0; i < NUM_COUNTERS; ++i)
		{
			my_perf_data_local->counterVal[i] = read_p15_count(i);
		}

		// Make values available in sysfs:
		my_cpu_counter_obj_local->cycles = my_perf_data_local->cycles;
		my_cpu_counter_obj_local->instructions_retired = my_perf_data_local->counterVal[0];
		my_cpu_counter_obj_local->branch_mispredictions = my_perf_data_local->counterVal[1];
		my_cpu_counter_obj_local->data_memory_accesses = my_perf_data_local->counterVal[2];
		my_cpu_counter_obj_local->l2_data_refills = my_perf_data_local->counterVal[3];
		sysfs_notify(&(my_cpu_counter_obj_local->kobj), NULL, "data_memory_accesses"); 
		
		
#if DEBUG
		if (coreid == 4)
			printk(KERN_INFO "[perf] CPU %d: %u cycles\n", coreid, my_perf_data_local->cycles);
#endif
		// Check time elapsed:
#if DEBUG
		tm3.tv_usec = tm2.tv_usec;
		tm3.tv_sec = tm2.tv_sec;
#endif
		do_gettimeofday(&tm2);
		
		elapsed = 1000 * (tm2.tv_sec - tm1.tv_sec) + (tm2.tv_usec - tm1.tv_usec) / 1000;
#if DEBUG
		elapsed2 = 1000 * (tm2.tv_sec - tm3.tv_sec) + (tm2.tv_usec - tm3.tv_usec) / 1000;
		pr_info("[perf] CPU %d: %llu ms elapsed", coreid, elapsed);
		pr_info("[perf] CPU %d: %llu ms elapsed2", coreid, elapsed2);
#endif
		
		// Release reference to perf data, thereby ending the atomic section. VERY IMPORTANT!
		put_cpu_var(my_perf_data);
		
		// Reset counters for next period of accumulation
		// NOTE: if period is too high, it is possible that the counters could overflow
		// 		 and reset within the span of one period.
		reset_counters();
		
		// wait for remainder:
		msleep((unsigned long)(sample_period_ms - elapsed));
	}

	// Cleanup and disable CPU counters:
	KTHREAD_END:
	destroy_cntr_obj(my_cpu_counter_obj_local);
	disable_cpu_counters(NULL);
	return 0;
}

int init_module(void)
{
	int cpu;
	
	pr_info("Performance counter kmod for ARMv7.\n");
	// Setup here:
	my_perf_data_ptr = alloc_percpu(my_perf_data);

	// Instantiate the one kset to rule them all:
	cntr_kset = kset_create_and_add("performance_counters", NULL, kernel_kobj);
	if (!cntr_kset)
		return -ENOMEM;
	
	// Create cpu_counter_obj for each cpu:
	// TODO: ALLOC cpu_counter_obj objects for each CPU?
	// each will be registered by the corresponding kthread with the kset.
	

	get_online_cpus();
	for_each_online_cpu(cpu)
	{
#ifdef RESTRICT_CPU
		if (cpu >= RESTRICT_CPU)
#endif
		{
			task[cpu] = kthread_create(perf_thread, (void*) data, "perf_counter_thread");
			kthread_bind(task[cpu], cpu);
			printk(KERN_INFO "activated perf monitoring on CPU %d\n", cpu);
		}
	}
	put_online_cpus();

	get_online_cpus();
	for_each_online_cpu(cpu)
	{
#ifdef RESTRICT_CPU
		if (cpu >= RESTRICT_CPU)
#endif
			wake_up_process(task[cpu]);
	}
	put_online_cpus();

	printk(KERN_INFO "[ RL_PERF ] initialized");
	return 0;
}

void cleanup_module(void)
{
	int cpu;

	pr_info("Cleaning up perf counter kmod for ARMv7.\n");
	
	get_online_cpus();
	for_each_online_cpu(cpu)
	{
#ifdef RESTRICT_CPU
		if (cpu >= RESTRICT_CPU)
#endif
			kthread_stop(task[cpu]);
	}
	put_online_cpus();
	
	kset_unregister(cntr_kset);

	printk(KERN_INFO "[ RL_PERF ] unloaded.");
}
