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

// Function prototypes:


// Function definitions:

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

void reset_counters_c()
{
	// Reset the performance counters
	asm volatile("mcr p15, 0, %0, c9, c12, 0" :: "r"(2 | 4));
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


unsigned int read_l2refill_count()
{
	return read_p15_count(4);
}

void get_perf_counters(unsigned int* res, unsigned int millis_period)
{

	unsigned int old_cycles, old_instructions, old_bmiss, 
					old_dmemaccess, old_l2refill;
	struct timeval stop, start;
	
	// Get initial time and counts:
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


#ifdef DEBUG
// tester main function. Else this is being compiled as python API.
int main()
{
	int res[5];
	for ( int i = 0; i < 100; i++ )
	{
		get_perf_counters(&res[0], MILLIS_WAIT);
		fprintf(stdout, "Cycles: %d\nInstructions: %d\nBranch Misses: %d\n\
					 Data Mem Accesses: %d\n L2 Cache Refills: %d\n\n",
					 res[0], res[1], res[2], res[3], res[4]);
	}
	return 0;
}

#else
// Wrapped cycle count function:
static PyObject* cycle_count(PyObject* self, PyObject* args)
{
	unsigned int count;
	// There are no inputs, so skip input arg parsing.
	// Call cycle count function:
	count = read_cycle_count();

	// Construct output and return:
	return Py_BuildValue("i", count);
}

static PyObject* inst_count(PyObject* self, PyObject* args)
{
	unsigned int count;
	// There are no inputs, so skip input arg parsing.
	// Call instruction count function:
	count = read_inst_count();

	// Construct output and return:
	return Py_BuildValue("i", count);
}

static PyObject* bmiss_count(PyObject* self, PyObject* args)
{
	unsigned int count;
	// There are no inputs, so skip input arg parsing.
	// Call bmiss count function:
	count = read_mispred_count();

	// Construct output and return:
	return Py_BuildValue("i", count);
}

static PyObject* dmemaccess_count(PyObject* self, PyObject* args)
{
	unsigned int count;
	// There are no inputs, so skip input arg parsing.
	// Call data memory access count function:
	count = read_datamemaccess_count();

	// Construct output and return:
	return Py_BuildValue("i", count);
}

static PyObject* l2refill_count(PyObject* self, PyObject* args)
{
	unsigned int count;
	// There are no inputs, so skip input arg parsing.
	// Call l2 refill count function:
	count = read_l2refill_count();

	// Construct output and return:
	return Py_BuildValue("i", count);
}

static PyObject* perf_w_period(PyObject* self, PyObject* args)
{
	unsigned int results[5];
	unsigned int millis_period;
	// Parse args:
	if (!PyArg_ParseTuple(args, "i", &millis_period))
		return NULL;

	// Call function:
	get_perf_counters(&results[0], millis_period);
	
	// Return the results:
	PyObject *l = PyList_New(5);
	for (int i = 0; i < 5; i++)
	{
		PyList_SET_ITEM(l, i, Py_BuildValue("i", results[i]));
	}
	return Py_BuildValue("o", l);
}

static PyObject* reset_counters(PyObject* self, PyObject* args)
{
	reset_counters_c();
	return NULL;
}




// Python wrapper for functions above:
static PyMethodDef PerfMethods[] = 
{	
	// Get raw counter values:
	{"cycle_count", cycle_count, METH_VARARGS, "get number of cycles on counter."},
	{"inst_count", inst_count, METH_VARARGS, "get number of instructions retired."},
	{"bmiss_count", bmiss_count, METH_VARARGS, "get number of branch mispredictions."},
	{"dmemaccess_count", dmemaccess_count, METH_VARARGS, "get number of accesses to data memory."},
	{"l2refill_count", l2refill_count, METH_VARARGS, "get number of l2 data cache refills."},
	// Get all values over n millisecond period:
	{"perf_w_period", perf_w_period, METH_VARARGS, "get change in all counters over period in milliseconds."},
	{"reset_counters", reset_counters, METH_VARARGS, "reset all performance counters to 0."},
	{NULL, NULL, 0, NULL}
};


#if PY_MAJOR_VERSION >= 3
#error Python 3.* support not yet implemented. Compile with headers for Python 2.
#else
PyMODINIT_FUNC
initperf_module(void)
{
	(void) Py_InitModule("perf_module", PerfMethods);
}
#endif
#endif
