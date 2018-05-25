/*
	Description: Sysfs-interface function definitions for for perf-counters 
			kernel module, for use on 32-bit ARM cortex-A processors 
			(specifically A-7, A-15, and A-53 in v7 mode).
	Date: 25 May 2018
	Author: Mark Blanco <markb1@andrew.cmu.edu>
*/

#include "sysfs-perf.h"

// Sysfs interfacing variables:

// Sysfs ops that will be associated with ktype below, 
// defined using the show/store functions above.
const struct sysfs_ops cntr_sysfs_ops = {
	.show = cntr_attr_show,
	.store = cntr_attr_store,
};

// Define sysfs file attributes:
struct cntr_attribute sample_period_attribute = 
	__ATTR(sample_period_ms, FMODE, cntr_show, cntr_store);
struct cntr_attribute cycles_attribute = 
	__ATTR(cycles, FMODE, cntr_show, cntr_store);
struct cntr_attribute instructions_attribute = 
	__ATTR(instructions_retired, FMODE, cntr_show, cntr_store);
struct cntr_attribute branch_miss_attribute = 
	__ATTR(branch_mispredictions, FMODE, cntr_show, cntr_store);
struct cntr_attribute dmem_access_attribute = 
	__ATTR(data_memory_accesses, FMODE, cntr_show, cntr_store);
struct cntr_attribute l2_refill_attribute = 
	__ATTR(l2_data_refills, FMODE, cntr_show, cntr_store);

// Create a group of attributes so they can be created and destroyed all at once:
struct attribute* cntr_default_attrs[] = {
	&sample_period_attribute.attr,
	&cycles_attribute.attr,
	&instructions_attribute.attr,
	&branch_miss_attribute.attr,
	&dmem_access_attribute.attr,
	&l2_refill_attribute.attr,
	NULL,		// MUST BE NULL TERMINATED!
};


// Create ktypes for custom kobjects. This is where the sysfs ops,
// release function, and set of default attributes are tied together.
struct kobj_type cntr_ktype = {
	.sysfs_ops = &cntr_sysfs_ops,
	.release = cntr_release,
	.default_attrs = cntr_default_attrs,
};


/*
 * Default show function to be passed to sysfs. Translates from kobject to the 
 * cpu_counter_obj object, then calls show for that object.
 */
ssize_t cntr_attr_show(struct kobject* kobj, struct attribute *attr, char* buf)
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
ssize_t cntr_attr_store(struct kobject* kobj, struct attribute *attr, const char* buf, size_t len)
{
	struct cntr_attribute* attribute;
	struct cpu_counter_obj* cpu_cntr;

	attribute = to_cntr_attribute(attr);
	cpu_cntr = to_cntr_obj(kobj);

	if (!attribute->store)
		return -EIO;

	return attribute->store(cpu_cntr, attribute, buf, len);
}


// Release function for cpu_counter_obj object. CANNOT BE LEFT EMPTY!
void cntr_release(struct kobject* kobj)
{
	struct cpu_counter_obj* cntr_obj;
	cntr_obj = to_cntr_obj(kobj);
	kfree(cntr_obj);
}

// Sysfs show/store functions to handle the vars stored in cpu_counter_obj objects:
ssize_t cntr_show(struct cpu_counter_obj* obj, 
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


ssize_t cntr_store(struct cpu_counter_obj* obj, struct cntr_attribute* attr, 
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


// Define function to create a new cpu_counter_obj object:
struct cpu_counter_obj* create_cntr_obj(const char* name, struct kset* parent_kset)
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
void destroy_cntr_obj(struct cpu_counter_obj* obj)
{
	kobject_put(&obj->kobj);
}

