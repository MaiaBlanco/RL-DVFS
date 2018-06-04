# unsigned int b11 = 1646, b12 = 793, b13 = 0,    b14 = 228;
# unsigned int b21 = 1143, b22 = 730, b23 = 178,  b24 = 0;
# unsigned int b31 = 1440, b32 = 818, b33 = 0,    b34 = 0;
# unsigned int b41 = 1160, b42 = 833, b43 = 1112, b44 = 154;
# unsigned int b51 = 1332, b52 = 713, b53 = 0,    b54 = 991;
# unsigned int a11 = 9935,  a12 = 15,    a13 = 22,   a14 = 14,   a15 = 7;
# unsigned int a21 = 70,    a22 = 9913,  a23 = 1,    a24 = 8,    a25 = 0;
# unsigned int a31 = 17,    a32 = 22,    a33 = 9911, a34 = 19,   a35 = 30;
# unsigned int a41 = 74,    a42 = 0,     a43 = 0,    a44 = 9904, a45 = 3;
# unsigned int a51 = 20,    a52 = 19,    a53 = 22,   a54 = 15,   a55 = 9896;
# NOTE: above was all converted to integer by multiplying by 10000


c1 = 0.002488
c2 = -2660
# Gate current
Igate=0.000001

big_f_to_v = {
			0.2:0.9,
			0.3:0.9,
			0.4:0.9,
			0.5:0.9,
			0.6:0.9,
			0.7:0.9,
			0.8:0.9,
			0.9:0.925,
			1.0:0.95,
			1.1:0.975,
			1.2:1.0,
			1.3:1.025,
			1.4:1.05,
			1.5:1.075,
			1.6:1.1125,
			1.7:1.15,
			1.8:1.1875,
			1.9:1.2375,
			2.0:1.3
		}

little_f_to_v = {
			0.2:0.9,
			0.3:0.9,
			0.4:0.9,
			0.5:0.9,
			0.6:0.925,
			0.7:0.9625,
			0.8:1.0,
			0.9:1.0375,
			1.0:1.075,
			1.1:1.1125,
			1.2:1.15,
			1.3:1.2,
			1.4:1.25
		}

big_f_to_v_MC1 = {
			0.2:0.9,
			0.3:0.9,
			0.4:0.9,
			0.5:0.9,
			0.6:0.9,
			0.7:0.9,
			0.8:0.9,
			0.9:0.9125,
			1.0:0.9375,
			1.1:0.9625,
			1.2:0.9875,
			1.3:1.0125,
			1.4:1.0375,
			1.5:1.0625,
			1.6:1.1,
			1.7:1.1375,
			1.8:1.175,
			1.9:1.225,
			2.0:1.2875
		}

little_f_to_v_MC1 = {
			0.2:0.9,
			0.3:0.9,
			0.4:0.9,
			0.5:0.9,
			0.6:0.9125,
			0.7:0.95,
			0.8:0.9875,
			0.9:1.025,
			1.0:1.0625,
			1.1:1.1,
			1.2:1.1375,
			1.3:1.1875,
			1.4:1.2375
		}

		
'''algorithm:
get max temperature
get current power usage
calculate power usage of each big core and of 


# COmments from ganapati's implemnentation:
# /*
#  * Every sampling_rate, we check, if current idle time is less than 20%
#  * (default), then we try to increase frequency. Every sampling_rate, we look
#  * for the lowest frequency which can sustain the load while keeping idle time
#  * over 30%. If such a frequency exist, we try to decrease to this frequency.
#  *
#  * Any frequency increase takes it to the maximum frequency. Frequency reduction
#  * happens at minimum steps of 5% (default) of current frequency
#  */
'''
