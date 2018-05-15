obj-m += perf-counters.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean

test:
	gcc -DDEBUG userspace_read_perf_counters.c -I /usr/include/python2.7/
