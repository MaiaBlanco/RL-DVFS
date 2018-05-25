obj-m += perfmod.o
perfmod-objs := perf-counters.o pmu-perf.o sysfs-perf.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
#	python setup.py build_ext --inplace
#	cp perf_module.so ../gov/
#	cp perfmod.ko ../gov/

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
	rm -f a.out
	rm -f ../gov/perf_module.so
	rm -f ../gov/perfmod.ko

#test:
#	gcc -DDEBUG perf_module.c -I /usr/include/python2.7/
#	./a.out
