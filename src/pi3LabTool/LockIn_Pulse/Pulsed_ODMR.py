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

t_ini = 40e-6
t_pi = 2e-6
power_MW = -6#dBm
f_start =  2.84e9#2.838e9
f_stop = 2.853e9#2.87e9
f_step = 101
MW_list = np.linspace(f_start,f_stop,f_step)
f_LIA = 10e3#100e-6
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
sp.pb_start_programming(sp.PULSE_PROGRAM)
start = sp.pb_inst_pbonly(0b000000000001100,sp.CONTINUE,0,t_ini*factor)
sp.pb_inst_pbonly(0b000000000000110,sp.CONTINUE,0,t_pi*factor)
sp.pb_inst_pbonly(0b000000000000100,sp.CONTINUE,0,(1/(2*f_LIA)-t_ini-t_pi)*factor)
sp.pb_inst_pbonly(0b000000000001000,sp.CONTINUE,0,t_ini*factor)
sp.pb_inst_pbonly(0b000000000000000,sp.BRANCH,start,(1/(2*f_LIA)-t_ini)*factor)
sp.pb_stop_programming()
sp.pb_reset()
sp.pb_start()
#
setTaborCW_Output(f_start, power_MW , 0x168C, 0x1202)
#sleep(5)
###Measurement###
RATE = 1e3
TIME_OUT = 10
POINTS = 200
MIN_VAL = -10
MAX_VAL = 10
data_list = []
with Task() as task:
    print('connected')
    sampling_rate = int(RATE)
    sampling_point = int(POINTS)
    task.ai_channels.add_ai_voltage_chan("Dev3/ai5",terminal_config=constants.TerminalConfiguration.DIFF,min_val=MIN_VAL,units=constants.VoltageUnits.VOLTS,max_val=MAX_VAL)
    task.timing.cfg_samp_clk_timing(rate=sampling_rate,samps_per_chan=sampling_point,sample_mode=constants.AcquisitionType.FINITE)
    for i,f in enumerate(MW_list):
        setfreq(f, 0x168C, 0x1202)
        sleep(0.1)
        task.start()
        data = np.array(task.read(number_of_samples_per_channel=sampling_point,timeout=TIME_OUT))
        data_averaged = np.average(data)
        data_list.append(data_averaged)
        task.stop()

print("finish")
sp.pb_stop()
sp.pb_close()
setoff(0x168C, 0x1202)
data_list = np.array(data_list)
fig = plt.figure(dpi=300,figsize=(10,6))
ax = fig.add_subplot(111)
ax.plot(MW_list,data_list)
plt.show()

idling(t_ini,f_LIA)
#saving

save_path = r'C:\Users\pi3-pc12\Desktop\Yuta\Experimental Data\Pulsed-ODMR'
npy_name = datetime.now().strftime('%Y%m%d_%H_%M%S')
data_dict = np.array({
'MW_list':MW_list,
'data':data_list,
'Sampling rate':sampling_rate,
'sampling number':POINTS,
'pi_pulse':t_pi,
't_ini':t_ini,
'power_MW':power_MW,
'f_LIA':f_LIA
})
np.save(save_path+'/'+npy_name,data_dict)