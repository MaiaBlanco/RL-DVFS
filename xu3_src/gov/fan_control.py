#! /usr/bin/python
import atexit
import sys

if __name__ == "__main__":
	if len(sys.argv) == 2:
			if sys.argv[1] == "on":
				# Set to manual mode:
				with open('/sys/devices/odroid_fan.14/fan_mode', 'w') as f:
					f.write("0")
				# Turn fan all the way on (in manual):
				with open('/sys/devices/odroid_fan.14/pwm_duty', 'w') as f:
					f.write("255")	
			elif sys.argv[1] == "off":
				# Set to manual mode:
				with open('/sys/devices/odroid_fan.14/fan_mode', 'w') as f:
					f.write("0")
				# Turn fan off (in manual):
				with open('/sys/devices/odroid_fan.14/pwm_duty', 'w') as f:
					f.write("1")
			elif sys.argv[1] == "auto":
				# set to automatic mode:
				with open('/sys/devices/odroid_fan.14/fan_mode', 'w') as f:
					f.write("1")
	else:
		print("Invalid option! Select on, off, or auto.")



