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

// License (required to load module that writes to sysfs anyways):
MODULE_LICENSE("Dual BSD/GPL");
MODULE_AUTHOR("Mark Blanco <markb1@andrew.cmu.edu>");

// If defined, RESTRICT_CPU causes perf counter kthread to run on just
// the CPU core with the number specified.
//#define RESTRICT_CPU 0

#define DEBUG 0

#define DEFAULT_PERIOD_MS 100

// Events of interest, aside from cycles:
#define INST_RET 0x08 			// Instructions retired
#define BRANCH_MISPRED 0x10		// branch misprediction
#define DATA_MEM_ACCESS 0x13	// Access to data memory 
								// (assumed to RAM, past LLC)
#define L2_DATA_REFILL 0x17		// L2 Cache miss 

// The number of counters to be enabled, aside from the cycle counter.
#define NUM_COUNTERS 4
const unsigned int counters[] = {INST_RET, BRANCH_MISPRED, DATA_MEM_ACCESS, L2_DATA_REFILL};

// Setting for perf counters. 
// 1 enables all counters, 16 enables event exporting to external devices.
// Setting 8 enables clock division such that the cycle counter counts every
// 64 cycles. 
// Setting 2 and 4 reset event counts and cycle counts respectively.
#define PERF_DEF_OPTS ( (1 << 0) )

// Struct definitions
struct my_perf_data_struct {
	// cycles
	unsigned int cycles;
	unsigned int counterVal[NUM_COUNTERS];
};

// This object is replicated for each CPU on the system for which we want counter data.
// All of the object instances will have a single (shared) kset as their parent and will
// have a directory and file representations in sysfs.
// See linux kernel samples/kobject/kset-example.c for more.
struct cpu_counter_obj {
	struct kobject kobj;
	unsigned int sample_period_ms;
	unsigned int cycles;
	unsigned int instructions_retired;
	unsigned int branch_mispredictions;
	unsigned int data_memory_accesses;
	unsigned int l2_data_refills;
};
#define to_cntr_obj(x) container_of(x, struct cpu_counter_obj, kobj)

// Custom attribute for the cpu_counter_obj object:
struct cntr_attribute {
	struct attribute attr;
	ssize_t (*show)(struct cpu_counter_obj* obj, struct cntr_attribute* attr, char* buf);
	ssize_t (*store)(struct cpu_counter_obj* obj, struct cntr_attribute* attr, const char* buf, 
						size_t len);
};
#define to_cntr_attribute(x) container_of(x, struct cntr_attribute, attr)

/*
 * Default show function to be passed to sysfs. Translates from kobject to the 
 * cpu_counter_obj object, then calls show for that object.
 */
static ssize_t cntr_attr_show(struct kobject* kobj, struct attribute *attr, char* buf)
{
	struct cntr_attribute* attribute;
	struct cpu_counter_obj* cpu_cntr;

	attribute = to_cntr_attribute(attr);
	cpu_cntr = to_cntr_obj(kobj);

	if (!attribute->show)
		return -EIO;

	return attribute->show(cpu_cntr, attribute, buf);
}

/*
 * Default store function to be passed to sysfs. Translates from kobject to the 
 * cpu_counter_obj object, then calls store for that object.
 */
static ssize_t cntr_attr_store(struct kobject* kobj, struct attribute *attr, const char* buf, size_t len)
{
	struct cntr_attribute* attribute;
	struct cpu_counter_obj* cpu_cntr;

	attribute = to_cntr_attribute(attr);
	cpu_cntr = to_cntr_obj(kobj);

	if (!attribute->store)
		return -EIO;

	return attribute->store(cpu_cntr, attribute, buf, len);
}

// Sysfs ops that will be associated with ktype below, 
// defined using the show/store functions above.
static const struct sysfs_ops cntr_sysfs_ops = {
	.show = cntr_attr_show,
	.store = cntr_attr_store,
};

// Release function for cpu_counter_obj object. CANNOT BE LEFT EMPTY!
static void cntr_release(struct kobject* kobj)
{
	struct cpu_counter_obj* cntr_obj;
	cntr_obj = to_cntr_obj(kobj);
	kfree(cntr_obj);
}

// Sysfs show/store functions to handle the vars stored in cpu_counter_obj objects:
static ssize_t cntr_show(struct cpu_counter_obj* obj, 
							struct cntr_attribute* attr, char* buf)
{
	unsigned int var;

	if (strcmp(attr->attr.name, "sample_period_ms") == 0)
		var = obj->sample_period_ms;
	else if (strcmp(attr->attr.name, "cycles") == 0)
		var = obj->cycles;
	else if (strcmp(attr->attr.name, "instructions_retired") == 0)
		var = obj->instructions_retired;
	else if (strcmp(attr->attr.name, "branch_mispredictions") == 0)
		var = obj->branch_mispredictions;
	else if (strcmp(attr->attr.name, "data_memory_accesses") == 0)
		var = obj->data_memory_accesses; 
	else if (strcmp(attr->attr.name, "l2_data_refills") == 0)
		var = obj->l2_data_refills;
	else
		var = 0;

	return sprintf(buf, "%u\n", var);
}


static ssize_t cntr_store(struct cpu_counter_obj* obj, struct cntr_attribute* attr, 
							const char* buf, size_t len)
{
	unsigned int var;
	int ret;

	ret = kstrtoint(buf, 10, &var);
	if (ret < 0)
		return ret;

	if (strcmp(attr->attr.name, "sample_period_ms") == 0)
		obj->sample_period_ms = var;
	else
		// No reason to take a counter value from userspace.
		var = 0;

	return len;
}

// Define sysfs file attributes:
static struct cntr_attribute sample_period_attribute = 
	__ATTR(sample_period_ms, 0664, cntr_show, cntr_store);
static struct cntr_attribute cycles_attribute = 
	__ATTR(cycles, 0664, cntr_show, cntr_store);
static struct cntr_attribute instructions_attribute = 
	__ATTR(instructions_retired, 0664, cntr_show, cntr_store);
static struct cntr_attribute branch_miss_attribute = 
	__ATTR(branch_mispredictions, 0664, cntr_show, cntr_store);
static struct cntr_attribute dmem_access_attribute = 
	__ATTR(data_memory_accesses, 0664, cntr_show, cntr_store);
static struct cntr_attribute l2_refill_attribute = 
	__ATTR(l2_data_refills, 0664, cntr_show, cntr_store);

// Create a group of attributes so they can be created and destroyed all at once:
static struct attribute* cntr_default_attrs[] = {
	&sample_period_attribute.attr,
	&cycles_attribute.attr,
	&instructions_attribute.attr,
	&branch_miss_attribute.attr,
	&dmem_access_attribute.attr,
	&l2_refill_attribute.attr,
	NULL,		// MUST BE NULL TERMINATED!
};


// Create ktypes for custom kobjects. This is where the sysfs ops,
// release function, and set of default attributes (just instantiated above)
// are tied together.
static struct kobj_type cntr_ktype = {
	.sysfs_ops = &cntr_sysfs_ops,
	.release = cntr_release,
	.default_attrs = cntr_default_attrs,
};

// Create unifying kset for all cpu counter objects:
static struct kset* cntr_kset;
// Create counter objects on each CPU:
DEFINE_PER_CPU(struct cpu_counter_obj, my_cpu_counter_obj);
// Create some data instances on all CPUs, bound to each CPU:
DEFINE_PER_CPU(struct my_perf_data_struct, my_perf_data);
DEFINE_PER_CPU(struct my_perf_data_struct*, my_perf_data_ptr);

// Define function to create a new cpu_counter_obj object:
static struct cpu_counter_obj* create_cntr_obj(const char* name, struct kset* parent_kset)
{
	struct cpu_counter_obj* cntr_obj;
	int retval;

	/* Allocate the memory for the whole object */
	cntr_obj = kzalloc(sizeof(*cntr_obj), GFP_ATOMIC);
	if (!cntr_obj)
		return NULL;
	
	// Set kset for this object
	cntr_obj->kobj.kset = parent_kset;

	// Set default sampling period:
	cntr_obj->sample_period_ms = DEFAULT_PERIOD_MS;

	// Init and add kobject embedded in cntr_obj with the kernel.
	retval = kobject_init_and_add(&cntr_obj->kobj, &cntr_ktype, NULL, "%s", name);
	if (retval)
	{
		kobject_put(&cntr_obj->kobj);
		return NULL;
	}

	// Send uevent that the kobject was added to the system.
	kobject_uevent(&cntr_obj->kobj, KOBJ_ADD);

	return cntr_obj;
}

// Define destructor for cpu_counter_obj object. This works by removing a
// reference from the embdedded kobject; when all references are finally released
// the kernel will dismiss the cntr_obj.
static void destroy_cntr_obj(struct cpu_counter_obj* obj)
{
	kobject_put(&obj->kobj);
}

struct task_struct* task[8];
int data;
int ret;

// Function definitions for PMU interfacing:

// Disable perf counters and userspace access to them:
static void disable_cpu_counters(void* data)
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
// Enable the CPU counters #defined above; enable userspace access, etc:
static unsigned int enable_cpu_counters(void * data)
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

int perf_thread(void * data)
{
	// Get core id:
	unsigned int coreid = smp_processor_id();
	char name[] = "cpu_\0";

	// Timing:
	struct timeval tm1, tm2, tm3;
	unsigned long elapsed;
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
#ifdef DEBUG
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
		if (cpu == RESTRICT_CPU)
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
		if (cpu == RESTRICT_CPU)
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
		if (cpu == RESTRICT_CPU)
#endif
			kthread_stop(task[cpu]);
	}
	put_online_cpus();
	
	kset_unregister(cntr_kset);

	printk(KERN_INFO "[ RL_PERF ] unloaded.");
}
