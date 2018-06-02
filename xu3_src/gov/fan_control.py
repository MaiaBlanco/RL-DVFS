with open('/sys/devices/odroid_fan.14/fan_mode', 'w') as f:
	f.write("0")

with open('/sys/devices/odroid_fan.14/fan_mode', 'w') as f:
	f.write("1")

with open('/sys/devices/odroid_fan.14/pwm_duty', 'w') as f:
	f.write("1")

with open('/sys/devices/odroid_fan.14/pwm_duty', 'w') as f:
	f.write("255")	

