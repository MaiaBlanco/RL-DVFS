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


// License (required to load module that writes to sysfs anyways):
MODULE_LICENSE("Dual BSD/GPL");
MODULE_AUTHOR("Mark Blanco <markb1@andrew.cmu.edu>");

#define DEFAULT_PERIOD_MS 50

// Events of interest, aside from cycles:
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

// Struct definitions
struct my_perf_data_struct {
	// Jiffies
	unsigned int jif1;
	unsigned int jif2; 
	unsigned int jif_diff;
	// cycles
	unsigned int cycles1;
	unsigned int cycles2;
	unsigned int cycles_diff;
	// instructions
	unsigned int instr1;
	unsigned int instr2;
	unsigned int instr_diff;
	// l2 refills
	unsigned int l2r1;
	unsigned int l2r2;
	unsigned int l2r_diff;
	// data mem accesses
	unsigned int dmema1;
	unsigned int dmema2;
	unsigned int dmema_diff;
	// branch misses
	unsigned int bmiss1;
	unsigned int bmiss2;
	unsigned int bmiss_diff;
};

// This object is replicated for each CPU on the system for which we want counter data.
// All of the object instances will have a single (shared) kset as their parent and will
// have a directory and file representations in sysfs.
// See linux kernel samples/kobject/kset-example.c for more.
struct cpu_counter_obj {
	struct kobject kobj;
	unsigned long sample_period_ms;
	unsigned long cycles;
	unsigned long instructions_retired;
	unsigned long branch_mispredictions;
	unsigned long data_memory_accesses;
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
	else 
		var = obj->data_memory_accesses; 

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
	else if (strcmp(attr->attr.name, "cycles") == 0)
		obj->cycles = var;
	else if (strcmp(attr->attr.name, "instructions_retired") == 0)
		obj->instructions_retired = var;
	else if (strcmp(attr->attr.name, "branch_mispredictions") == 0)
		obj->branch_mispredictions = var;
	else 
		obj->data_memory_accesses = var; 

	return len;
}

// Define sysfs file attributes:
static struct cntr_attribute sample_period_attribute = 
	__ATTR(sample_period_ms, 0664, cntr_show, cntr_store);
static struct cntr_attribute cycles_attribute = 
	__ATTR(cycles, 0664, cntr_show, cntr_store);
static struct cntr_attribute instructions_attribute = 
	__ATTR(instructions, 0664, cntr_show, cntr_store);
static struct cntr_attribute branch_miss_attribute = 
	__ATTR(branch_miss, 0664, cntr_show, cntr_store);
static struct cntr_attribute dmem_access_attribute = 
	__ATTR(dmem_access, 0664, cntr_show, cntr_store);

// Create a group of attributes so they can be created and destroyed all at once:
static struct attribute* cntr_default_attrs[] = {
	&sample_period_attribute.attr,
	&cycles_attribute.attr,
	&instructions_attribute.attr,
	&branch_miss_attribute.attr,
	&dmem_access_attribute.attr,
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
static struct cpu_counter_obj* create_cntr_obj(const char* name)
{
	struct cpu_counter_obj* cntr_obj;
	int retval;

	/* Allocate the memory for the whole object */
	cntr_obj = kzalloc(sizeof(*cntr_obj), GFP_ATOMIC);
	if (!cntr_obj)
		return NULL;
	
	// Set kset for this object
	cntr_obj->kobj.kset = cntr_kset;

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

// Function definitions

// Enable the CPU counters #defined above; enable userspace access, etc:
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

// Disable perf counters and userspace access to them:
static void disable_cpu_counters(void* data)
{
	/* Disable user-mode access to counters. */
	asm volatile("mcr p15, 0, %0, c9, c14, 0" :: "r"(0));
	// Disable all counters (cycle counter and the 4 others): 
	asm volatile("mcr p15, 0, %0, c9, c12, 1" :: "r"(0x00000000));
	// Reset PMU counters and reset clock div settings, etc.:
	asm volatile("mcr p15, 0, %0, c9, c12, 0" :: "r"(0x00000007));
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
// TODO: add checks to make sure this doesn't try to access non-enabled regs.
// TODO: add check to make sure not to access if userspace is not enabled?
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
void reset_counters_c(void)
{
	unsigned int v;
	// Read the original value to preserve settings:
	asm volatile("mrc p15, 0, %0, c9, c12, 0" : "=r"(v));
	// Reset the performance counters by setting bits 1 and 2:
	asm volatile("mcr p15, 0, %0, c9, c12, 0" :: "r"(v | 2 | 4));
}

static inline 
unsigned int read_inst_count(void)
{
	return read_p15_count(1);
}

static inline 
unsigned int read_mispred_count(void)
{
	return read_p15_count(2);
}

static inline 
unsigned int read_datamemaccess_count(void)
{
	return read_p15_count(3);
}


static inline 
unsigned int read_l2refill_count(void)
{
	return read_p15_count(4);
}
/*
void get_perf_counters(unsigned int* res, unsigned int millis_period)
{

	unsigned int old_cycles, old_instructions, old_bmiss, 
					old_dmemaccess, old_l2refill;
	struct timeval stop, start;
	
	// Get initial time and counts:
	// TODO: fix this so it doesn't use non-kernel timing:
	gettimeofday(&start, NULL);
	old_cycles = read_cycle_count();
	old_instructions = read_inst_count();
	old_bmiss = read_mispred_count();
	old_dmemaccess = read_datamemaccess_count();
	old_l2refill = read_l2refill_count();
	gettimeofday(&stop, NULL);
	
	// Wait for sample period:
	while ( (unsigned int)(stop.tv_usec - start.tv_usec) < millis_period*1000 )
	{
		gettimeofday(&stop, NULL);
	}
	
	// Update counter vals and print:
	res[0] = read_cycle_count() - old_cycles;
	res[1] = read_inst_count() - old_instructions;
	res[2] = read_mispred_count() - old_bmiss;
	res[3] = read_datamemaccess_count() - old_dmemaccess;
	res[4] = read_l2refill_count() - old_l2refill;
}
*/
int perf_thread(void * data)
{
	// Get CPU id:
	unsigned int cpu_id = smp_processor_id();
	char name[] = "cpu_\0";

	// Timing:
	static struct timeval tm1;
	struct timeval tm2;
	unsigned long long elapsed;
	unsigned int sample_period_ms;

	struct my_perf_data_struct* my_perf_data_local;

	struct cpu_counter_obj* my_cpu_counter_obj_local;

	if (cpu_id < 4)
	{
		goto KTHREAD_END;
	}

	name[3] = (char)(cpu_id + '0');
	
	my_cpu_counter_obj_local = create_cntr_obj(name);
	if (!my_cpu_counter_obj_local)
	{
		goto KTHREAD_END;
	}
	
	// Start perf counters on CPU:
	enable_cpu_counters(NULL);
	
	schedule();

	while(!kthread_should_stop())
	{
		// Update sample period:
		sample_period_ms = my_cpu_counter_obj_local->sample_period_ms;
		// Get change in each counter
		do_gettimeofday(&tm1);

		my_perf_data_local = &get_cpu_var(my_perf_data);

		my_perf_data_local->jif2 = jiffies;
		my_perf_data_local->jif_diff = my_perf_data_local->jif2 - my_perf_data_local->jif1;

		my_perf_data_local->cycles2 = read_cycle_count();
		my_perf_data_local->cycles_diff = my_perf_data_local->cycles2 - my_perf_data_local->cycles1;

		my_perf_data_local->instr2 = read_inst_count();
		my_perf_data_local->instr_diff = my_perf_data_local->instr2 - my_perf_data_local->instr1;

		my_perf_data_local->dmema2 = read_datamemaccess_count();
		my_perf_data_local->dmema_diff = my_perf_data_local->dmema2 - my_perf_data_local->dmema1;

		my_perf_data_local->l2r2 = read_l2refill_count();
		my_perf_data_local->l2r_diff = my_perf_data_local->l2r2 - my_perf_data_local->l2r1;

		my_perf_data_local->bmiss2 = read_mispred_count();
		my_perf_data_local->bmiss_diff = my_perf_data_local->bmiss2 - my_perf_data_local->bmiss1;

		// Copy values over
		my_perf_data_local->jif1 = my_perf_data_local->jif2;
		my_perf_data_local->cycles1 = my_perf_data_local->cycles2;
		my_perf_data_local->instr1 = my_perf_data_local->instr2;
		my_perf_data_local->dmema1 = my_perf_data_local->dmema2;
		my_perf_data_local->l2r1 = my_perf_data_local->l2r2;
		my_perf_data_local->bmiss1 = my_perf_data_local->bmiss2;

		// Make values available in sysfs:
		my_cpu_counter_obj_local->cycles = my_perf_data_local->cycles_diff;
		my_cpu_counter_obj_local->instructions_retired = my_perf_data_local->instr_diff;
		my_cpu_counter_obj_local->branch_mispredictions = my_perf_data_local->bmiss_diff;
		my_cpu_counter_obj_local->data_memory_accesses = my_perf_data_local->dmema_diff;
		
		
#ifdef DEBUG
		printk(KERN_INFO "[perf] CPU %d: %u cycles\n", cpu_id, my_perf_data_local->cycles_diff );
#endif
		// Release reference to perf data, thereby ending the atomic section. VERY IMPORTANT!
		put_cpu_var(my_perf_data);

		// Check time elapsed and wait for remainder
		do_gettimeofday(&tm2);
		elapsed = 1000 * (tm2.tv_sec - tm1.tv_sec) + (tm2.tv_usec - tm1.tv_usec) / 1000;
		msleep((unsigned long long)(sample_period_ms - elapsed));	
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
	
	pr_info("Performance counter kmod for XU3.\n");
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
		// Don't bother perf monitoring for little cluster cores:
		if (cpu > 3)
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
		// Don't bother perf monitoring for little cluster cores:
		if (cpu > 3)
			wake_up_process(task[cpu]);
	}
	put_online_cpus();

	printk(KERN_INFO "[ RL_PERF ] initialized");
	return 0;
}

void cleanup_module(void)
{
	int cpu;

	pr_info("Cleaning up perf counter kmod for XU3.\n");
	
	get_online_cpus();
	for_each_online_cpu(cpu)
	{
		// Don't bother perf monitoring for little cluster cores:
		if (cpu > 3)
			kthread_stop(task[cpu]);
	}
	put_online_cpus();
	
	kset_unregister(cntr_kset);

	printk(KERN_INFO "[ RL_PERF ] unloaded.");
}

/* References:
https://github.com/pietromercati/KSAMPLER/blob/master/ksampler.c
TODO: Add others here...
*/
