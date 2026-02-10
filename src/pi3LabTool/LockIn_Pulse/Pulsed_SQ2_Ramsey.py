import spinapi as sp
import time
import numpy as np
import pyvisa as visa
import matplotlib.pyplot as plt
from nidaqmx import Task, constants
from datetime import datetime
from controllTaborTest import *
import sys
sys.path.append(r'C:\Users\pi3-pc12\Desktop\Yuta')
from Pulse_idling import idling

##############Variations###################
freq = 2847299685
power_MW = 7#dBm
t_ini = 40e-6
detuning = 5e6
pi_2_pulse = 150e-9
tau_start = 40e-9
tau_stop = 6e-6
tau_step = 40e-9
tau_list = np.arange(tau_start,tau_stop,tau_step)
f_LIA =10e3
CLOCK_FREQ_MHZ = 200

#Pulse Sequence
factor = 1e9*sp.ns
print("Initializing PulseBlaster...")
# It's good practice to close any existing connection before starting.
try:
    sp.pb_close()
except Exception:
    pass  # Ignore error if board was not open.

# Initialize the connection to the board.
if sp.pb_init() != 0:
    print(f"Error initializing PulseBlaster: {sp.pb_get_error()}")
    exit()
sp.pb_core_clock(CLOCK_FREQ_MHZ)

#
setTaborCW_Output(freq-detuning , power_MW , 0x168C, 0x1202)
###Measurement###
RATE = 1e3
TIME_OUT = 10
POINTS = 500
MIN_VAL = -10
MAX_VAL = 10
data_list = []
with Task() as task:
    print('connected')
    sampling_rate = int(RATE)
    sampling_point = int(POINTS)
    task.ai_channels.add_ai_voltage_chan("Dev3/ai5",terminal_config=constants.TerminalConfiguration.DIFF,min_val=MIN_VAL,units=constants.VoltageUnits.VOLTS,max_val=MAX_VAL)
    task.timing.cfg_samp_clk_timing(rate=sampling_rate,samps_per_chan=sampling_point,sample_mode=constants.AcquisitionType.FINITE)
    for i,tau in enumerate(tau_list):
        print(tau)
        sp.pb_start_programming(sp.PULSE_PROGRAM)
        start = sp.pb_inst_pbonly(0b000000000001100,sp.CONTINUE,0,t_ini*factor) #AOM,LIA,MW TTL,IQ TTL
        sp.pb_inst_pbonly(0b000000000000110,sp.CONTINUE,0,pi_2_pulse*factor)
        sp.pb_inst_pbonly(0b000000000000100,sp.CONTINUE,0,tau*factor)
        sp.pb_inst_pbonly(0b000000000000110,sp.CONTINUE,0,pi_2_pulse*factor)
        sp.pb_inst_pbonly(0b000000000000100,sp.CONTINUE,0,(1/(2*f_LIA)-pi_2_pulse*2-tau-t_ini)*factor)
        sp.pb_inst_pbonly(0b000000000001000,sp.CONTINUE,0,t_ini*factor)
        sp.pb_inst_pbonly(0b000000000000010,sp.CONTINUE,0,pi_2_pulse*factor)
        sp.pb_inst_pbonly(0b000000000000001,sp.CONTINUE,0,tau*factor)
        sp.pb_inst_pbonly(0b000000000000011,sp.CONTINUE,0,pi_2_pulse*factor)
        sp.pb_inst_pbonly(0b000000000000000,sp.BRANCH,start,(1/(2*f_LIA)-tau-pi_2_pulse*2-t_ini)*factor)
        sp.pb_stop_programming()
        sp.pb_reset()
        sp.pb_start()
        sleep(0.2)
        task.start()
        data = np.array(task.read(number_of_samples_per_channel=sampling_point,timeout=TIME_OUT))
        data_averaged = np.average(data)
        data_list.append(data_averaged)
        task.stop()     
        sp.pb_stop()

print("finish")
#sp.pb_stop()
sp.pb_close()
setoff(0x168C, 0x1202)
data_list = np.array(data_list)
fig = plt.figure(dpi=300,figsize=(10,6))
ax = fig.add_subplot(111)
ax.plot(tau_list,data_list)
plt.show()
idling(t_ini,f_LIA)

#saving

save_path = r'C:\Users\pi3-pc12\Desktop\Yuta\Experimental Data\Pulsed-SQ-2-Ramsey'
npy_name = datetime.now().strftime('%Y%m%d_%H_%M%S')
data_dict = np.array({
'tau_list':tau_list,
'pi_2_pulse':pi_2_pulse,
'data':data_list,
'detuning':detuning,
'Sampling rate':sampling_rate,
'sampling number':POINTS,
'freq':freq,
't_ini':t_ini,
'power_MW':power_MW,
'f_LIA':f_LIA
})
np.save(save_path+'/'+npy_name,data_dict)