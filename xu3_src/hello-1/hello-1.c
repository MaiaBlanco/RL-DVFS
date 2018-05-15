/* 
 * Super simple kernel module.
 */

#include <linux/module.h>	// Needed by all modules
#include <linux/kernel.h>	// Needed for KERN_INFO

int init_module(void)
{
	pr_info("Hello World V1.\n");
	return 0;
}

void cleanup_module(void)
{
	pr_info("Goodbye World V1.\n");
}
