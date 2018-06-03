# NOTE: Requires telnet connection over wifi to the SmartPower2, which provides power data.
# SP2 is usually at ip 192.168.4.1

import therm_params as tp
import math
import telnetlib as tel
import time
import devfreq_utils as dvfs

# power used by ethernet and wifiusb when active (assuming they are active)
board_power = 1.71
peripheral_power = 0.072 + 0.472 + board_power
SP2_tel = tel.Telnet("192.168.4.1")

# leakage power for a given resource (specified by the input model parameters)
def leakagePower(c1, c2, igate, v, t):
	return v*(c1 * math.pow(t, 2) * math.exp(c2/t) + igate)

def get_dyn_power(t):
		# Set temperatures for each (small, big, gpu, mem) (big cluster and GPU are exact; 
		# small and mem are approx)
		# mem die is on top of big core, so they should have approx the same max temp
		# small core takes average of all temps.
		T = [0.0, 0.0, 0.0, 0.0]
		# Set temperatures for the small, big, gpu and memory. Convert to kelvin
		T[0] = sum(t)/len(t)+ 273.15
		T[1] = max(t[0:4]) 	+ 273.15
		T[2] = t[4] 		+ 273.15
		T[3] = max(t[0:4]) 	+ 273.15
		F = [0, 0, 0, 0]
		# Get frequency of small cluster, big cluster, GPU, and mem (convert from Khz to hz, except for GPU freq which is already reported by sysfs in hz)
		F[0] = float(dvfs.getClusterFreq(0))*1000
		F[1] = float(dvfs.getClusterFreq(4))*1000
		F[2] = float(dvfs.getGPUFreq())
		F[3] = float(dvfs.getMemFreq())*1000
		# Get voltages for each resource (function returns volts so no conversion necessary):
		V = [0.0, 0.0, 0.0, 0.0]
		V[0] = tp.little_f_to_v_MC1[F[0]/1000000000]
		V[1] = tp.big_f_to_v_MC1[F[1]/1000000000]
		V[2] = dvfs.GPUVoltage()
		V[3] = dvfs.memVoltage()
		# Now compute the leakage power of each resource
		Pl = [0.0, 0.0, 0.0, 0.0]
		#print("Volts: {}".format(V))
		#print("Hz: {}".format(F))
		#print("Temp: {}".format(T))
		total_leakage_power = 0.0
		Pl[0] = leakagePower(tp.c1, tp.c2, tp.Igate, V[0], T[0])
		Pl[1] = leakagePower(tp.c1, tp.c2, tp.Igate, V[1], T[1])
		Pl[2] = leakagePower(tp.c1, tp.c2, tp.Igate, V[2], T[2])
		Pl[3] = leakagePower(tp.c1, tp.c2, tp.Igate, V[3], T[3])
		total_leakage_power = sum(Pl)
		tel_dat = str(SP2_tel.read_until('\r', timeout=0.05))
		# find latest power measurement in the data
		findex = tel_dat[0:len(tel_dat)].find('\n')
		ln = tel_dat[findex:].strip().split(',')
		total_power = float(ln[-2])
		total_dynamic_power = total_power - total_leakage_power - peripheral_power
		return total_dynamic_power	
