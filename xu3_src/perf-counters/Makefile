obj-m += perf-counters.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
	python setup.py build_ext --inplace

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
	rm -f a.out

test:
	gcc -DDEBUG perf_module.c -I /usr/include/python2.7/
	./a.out
