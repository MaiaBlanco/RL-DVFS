/*
	Description: Header with struct definitions and sysfs function 
		prototypes for perf-counters kernel module, for use on 32-bit 
		ARM cortex-A processors (specifically A-7, A-15, and A-53 in v7 mode).
	Date: 25 May 2018
	Author: Mark Blanco <markb1@andrew.cmu.edu>
*/
#ifndef PERF_SYSFS_H
#define PERF_SYSFS_H

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

//#include "params-perf.h"

#define FMODE 0664
#define DEFAULT_PERIOD_MS 100

MODULE_LICENSE("Dual BSD/GPL");


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

// Externally-used functions for counter kobject creation and deletion:
struct cpu_counter_obj* create_cntr_obj(const char* name, struct kset* parent);
void destroy_cntr_obj(struct cpu_counter_obj* obj);


// Internal sysfs function prototypes:
ssize_t cntr_attr_show(struct kobject* kobj, struct attribute *attr, char* buf);
ssize_t cntr_attr_store(struct kobject* kobj, struct attribute *attr, 
						const char* buf, size_t len);
void cntr_release(struct kobject* kobj);
ssize_t cntr_show(struct cpu_counter_obj* obj, struct cntr_attribute* attr, char* buf);
ssize_t cntr_store(struct cpu_counter_obj* obj, struct cntr_attribute* attr, 
						const char* buf, size_t len);
#endif
