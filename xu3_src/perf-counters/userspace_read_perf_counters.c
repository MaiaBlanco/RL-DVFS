#include <Python.h> /* Necessary for python wrapper integration */
// Note: below headers are actually included by Python.h, but also
// listed here to make clear what is available:
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
// End of python.h included headers
#include <sys/time.h>

#define MILLIS_WAIT 100

unsigned int read_cycle_count()
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

unsigned int read_inst_count()
{
	return read_p15_count(1);
}

unsigned int read_mispred_count()
{
	return read_p15_count(2);
}

unsigned int read_datamemaccess_count()
{
	return read_p15_count(3);
}


unsigned int read_L2refill_count()
{
	return read_p15_count(4);
}


#ifdef DEBUG
// tester main function. Else this is being compiled as python API.
void main()
{
	unsigned int cycles, instructions, bmiss, dmemaccess, l2refill;
	unsigned int old_cycles, old_instructions, old_bmiss, 
					old_dmemaccess, old_l2refill;
	struct timeval stop, start;
	
	for ( int i = 0; i < 100; i++ )
	{
		// Get initial time and counts:
		gettimeofday(&start, NULL);
		old_cycles = read_cycle_count();
		old_instructions = read_inst_count();
		old_bmiss = read_mispred_count();
		old_dmemaccess = read_datamemaccess_count();
		old_l2refill = read_L2refill_count();
		gettimeofday(&stop, NULL);
		
		// Wait for sample period:
		while ( (unsigned int)(stop.tv_usec - start.tv_usec) < MILLIS_WAIT*1000 )
		{
			gettimeofday(&stop, NULL);
		}

		// Update counter vals and print:
		cycles = read_cycle_count() - old_cycles;
		instructions = read_inst_count() - old_instructions;
		bmiss = read_mispred_count() - old_bmiss;
		dmemaccess = read_datamemaccess_count() - old_dmemaccess;
		l2refill = read_L2refill_count() - old_l2refill;
		fprintf(stdout, "Cycles: %d\nInstructions: %d\nBranch Misses: %d\n\
					 Data Mem Accesses: %d\n L2 Cache Refills: %d\n\n",
					 cycles, instructions, bmiss, dmemaccess, l2refill);
	}
}

#else

// Python wrapper for functions above:
#endif
