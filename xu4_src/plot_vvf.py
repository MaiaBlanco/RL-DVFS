from therm_params import big_f_to_v_MC1 as vvf_dict

fs = list(vvf_dict.keys())
fs.sort()
vvfs = [f * (vvf_dict[f]**2) for f in fs]

IPC = 4
throughputs = [IPC * f for f in fs]

for t, vvf in zip(throughputs, vvfs):
    print("{:.2f}\t{:.2f}\t{:.2f}".format(t, vvf,t/vvf))
