# common packages:
import numpy as np
import numpy as np
from transitions import Machine
# from pyspcm import *
# from spcm_tools import *

# nidaq's packages:
import nidaqmx as ni
import nidaqmx.constants as cst
from nidaqmx.stream_readers import AnalogMultiChannelReader, CounterReader



# Create 2 parallel process to get data and caculate average
class NI_State_Trans(object):
    states = ['IDLE', 'INIT', 'SS']
    transitions = [
        {'trigger': 'init', 'source': 'IDLE', 'dest': 'INIT', 'before': 'INIT_begin'},
        {'trigger': 'start', 'source': 'INIT', 'dest': 'SS', 'before': 'SS_begin'},
        {'trigger': 'stop', 'source': 'SS', 'dest': 'INIT', 'before': 'SS_stop'},
        {'trigger': 'config', 'source': 'INIT', 'dest': 'INIT', 'before': 'INIT_begin'},
        {'trigger': 'deactive', 'source': 'INIT', 'dest': 'IDLE', 'before': 'process_exit'},
        {'trigger': 'deactive', 'source': 'SS', 'dest': 'IDLE', 'before': 'process_exit'},
    ]
    def __init__(self, pipe1, pipe2, state, enable_debug=False):
        # Initialize the state machine
        self.machine = Machine(model=self, states=NI_State_Trans.states,
                               transitions=NI_State_Trans.transitions, initial='IDLE')
        self.pipe1 = pipe1
        self.pipe2 = pipe2
        self._state= state

        self.sweep = 0
        self.sweep_reset = False
        self._enable_debug = enable_debug


    def INIT_begin(self):
        if self._enable_debug:  
            print('start initializing')
        self.pipe1.send(1) # ready
        parameters = self.pipe1.recv()
        if self._enable_debug:  
            print('parameters: ', parameters)

        # default parameters -------------------------------------
        self._device_name = parameters[0]
        self.clk_terminal = parameters[1]
        self._sample_rate = parameters[2]
        self._frame_size = parameters[3]
        self._frame_num = parameters[4]
        self._physical_sample_clock_output = parameters[5]
        self.sampleMode_clk = cst.AcquisitionType.FINITE
        self.analog_channels = parameters[6]
        self._adc_voltage_range = parameters[7]
        self._rw_timeout = parameters[8]
        self.external_sample_clock_source = parameters[9]
        self._enable_debug = parameters[10]
        self.sampleMode_ai = cst.AcquisitionType.CONTINUOUS
        self.diffTerminal = cst.TerminalConfiguration.RSE
        if self._frame_size < 1:
            self._frame_size = 1
        if self._enable_debug:
            print("\n ***Current parameters are:")
            print("Device Name = {0}".format(parameters[0]))
            print("Clock Terminal = {0}".format(parameters[1]))
            print("Sample Rate = {0} S/s".format(parameters[2]))
            print("Frame Size = {0} samples".format(parameters[3]))
            print("Number of frame = {0} ".format(parameters[4]))
            print("Physical Sample Clock Output = {0}".format(parameters[5]))
            print("Sample Mode (Clock) = cst.AcquisitionType.FINITE")
            print("Analog Channels = {0}".format(parameters[6]))
            print("ADC Voltage Range = {0} V".format(parameters[7]))
            print("Read/Write Timeout = {0} ms".format(parameters[8]))
            print("External Sample Clock Source = {0}".format(parameters[9]))
            print("Sample Mode (AI) = cst.AcquisitionType.CONTINUOUS \n")
        #  -------------------------------------------------------

        # do a simple standard setup

        # 0. reset device
        try:
            self.ai.stop()
            self.ai.close()
            if self._enable_debug:
                    print('sucessfully reset previous ai task')
        except (AttributeError, ni.DaqError):
            if self._enable_debug:
                print('No reserved ai tasks')
        try:
            self.clk.stop()
            self.clk.close()
            if self._enable_debug:
                print('sucessfully reset previous ai task')
        except (AttributeError, ni.DaqError):
            if self._enable_debug:
                print('No reserved clk tasks')

        self._device_handle = ni.system.Device(self._device_name)
        try:
            self._device_handle.reset_device()
            print('Reset device {0}.'.format(self._device_name))
        except ni.DaqError:
            print('Could not reset NI device {0}'.format(self._device_name))

        # 1. configerate the clock
        self.clk = ni.Task()
        self.clk.co_channels.add_co_pulse_chan_freq(
                            '/{0}/{1}'.format(self._device_name, self.clk_terminal),
                            freq=self._sample_rate,
                            idle_state=ni.constants.Level.LOW)
        self.clk.timing.cfg_implicit_timing(
                            sample_mode=self.sampleMode_clk,
                            samps_per_chan=self._frame_size)
        self.clk.triggers.start_trigger.cfg_dig_edge_start_trig(
                            '/{0}/{1}'.format(self._device_name, 
                            self.external_sample_clock_source), 
                            trigger_edge=cst.Edge.RISING)
        self.clk.triggers.start_trigger.retriggerable = True
        self.clk.control(ni.constants.TaskMode.TASK_RESERVE)

        # 2. configerate the analog channel
        self.ai = ni.Task()
        self.ai.ai_channels.add_ai_voltage_chan('/{0}/{1}'.format(self._device_name, self.analog_channels),
                                            terminal_config=self.diffTerminal,
                                            max_val=max(self._adc_voltage_range),
                                            min_val=min(self._adc_voltage_range))
        self.ai.ai_channels.ai_impedance = cst.Impedance1.FIFTY_OHMS
        self.ai.timing.cfg_samp_clk_timing(self._sample_rate,
                                            source='/{0}/{1}'.format(self._device_name, 
                                                    self._physical_sample_clock_output),
                                            active_edge=ni.constants.Edge.RISING,
                                            sample_mode=self.sampleMode_ai,
                                            samps_per_chan=4095) # TODO: or test self._frame_size, but 4095 is the max value
        # If sample_mode is CONTINUOUS_SAMPLES, 
        # NI-DAQmx uses this value (samps_per_chan) to determine the buffer size.
        # This describtion only fit for cfg_samp_clk_timin !!!
        self.ai.control(ni.constants.TaskMode.TASK_RESERVE)

        try:
            self.ai_reader = AnalogMultiChannelReader(self.ai.in_stream)
            self.ai_reader.verify_array_shape = False
        except ni.DaqError:
            print('schief gehen bei Configuration des ai_readers')

        self.pipe1.send(0) # finished
        if self._enable_debug:  
            print('Initialization finished')


    def SS_begin(self):

        if self._enable_debug: 
            print('start sampling')

        # start everything
        try:
            self.ai.start()
            self.stop_symbol = 0
        except ni.DaqError:
            print('schief gehen bei Starten von ai task')

        try:
            self.clk.start()
            self.stop_symbol = 0
        except ni.DaqError:
            print('schief gehen bei Starten von clk task')

        # get buffered samples
        while not self.stop_symbol and self._state.value:

            if self._state.value == 0:
                self.stop_symbol = 1

            store_data = np.array([[]])
            data_buffer = np.zeros(self._frame_size)
            for cur_frame in range(self._frame_num):
                try:                 
                    read_samples = self.ai_reader.read_many_sample(
                        data_buffer,
                        number_of_samples_per_channel=self._frame_size,
                        timeout=self._rw_timeout)
                    
                    if not store_data.any():
                        store_data = np.array([data_buffer])
                    else:
                        store_data = np.append(store_data, [data_buffer], axis=0)

                except ni.DaqError:
                    print('Getting samples from streamer failed.')

                        
            if self._state.value == 2:
                print('Reset sweep count from %d to 0' % self.sweep)
                self.sweep = 0
                self._state.value = 1
            self.sweep += 1
            # if self._enable_debug: 
            #     print('sended sweep is :', self.sweep)
            self.pipe2.send(store_data)
            self.pipe2.send(self.sweep) 
        # self.pipe2.send(None)
        if self._enable_debug: 
            print('sampling finished!')
  

    def SS_stop(self):
        if self._enable_debug: 
            print('stop sampling')
        # send stop command
        try:
            self.ai.stop()
            # self.ai.close()
            if self._enable_debug:
                print('sucessfully stop ai task')
        except ni.DaqError:
            print('Error while trying to terminate ai task.')
        try:
            self.clk.stop()
            # self.clk.close()
            if self._enable_debug:
                print('sucessfully stop clk task')
        except ni.DaqError:
            print('Error while trying to terminate clk task.')
        
        self.sweep = 0
        if self._enable_debug: 
            print("Stop/Pause.... \n")

    def process_exit(self):
        if self._enable_debug: 
            print('stop processing')
        try:
            self.ai.stop()
            self.ai.close()
            if self._enable_debug:
                print('sucessfully close ai task')
        except ni.DaqError:
            print('Error while trying to terminate ai task.')
        
        try:
            self.clk.stop()
            self.clk.close()
            if self._enable_debug:
                print('sucessfully close clk task')
        except ni.DaqError:
            print('Error while trying to terminate clk task.')

        if self._enable_debug: 
            print("Exit...\n")
    

def accumulating_func(pipe2, pipe3, cmd, Vmax=5000):
    # cmd list:
    #    0: STOP
    #    1: RUN
    #    2: get acummulated data
    #    3: get last data
    #   -1: exit

    # scale = Vmax / 32768    # gated (change unit * 5000mv / int16's max value 32768)
    scale = 1 # 这里没有精度
    while True:
        store_data = np.array([[]])
        avg_cur_data = np.array([[]])
        avg_accumu_data = np.array([[]])
        innen_sweep = 0
        minus = 0
        if cmd.value == -1:
            break
        while cmd.value:
            cur_data = np.array(pipe2.recv())
            if not cur_data.any():
                break 
            sweep = pipe2.recv() - 1
            if not innen_sweep: # first innen_sweep
                innen_sweep += 1
                store_data = cur_data
                avg_cur_data = np.mean(cur_data, axis=0)
                avg_accumu_data = avg_cur_data
                
            else:
                innen_sweep += 1
                store_data = np.vstack((store_data, cur_data))
                avg_cur_data = np.mean(cur_data, axis=0)
                avg_accumu_data = ((avg_cur_data/(innen_sweep - 1)) + avg_accumu_data)*(1-(1/innen_sweep))
                minus = 0

            if cmd.value == 3:
                if len(cur_data) == len(store_data):
                    temp = np.vstack((cur_data, avg_cur_data))
                    pipe3.send(temp*scale)
                    pipe3.send(1)
                    cmd.value = 1

                    store_data = np.array([[]])
                    avg_cur_data = np.array([[]])
                    avg_accumu_data = np.array([[]])
                    innen_sweep = 0

            if cmd.value == 2:
                # print('cur data shape from [accumulating_func]', cur_data.shape)
                # print('store data shape from [accumulating_func]', store_data.shape)
                # print('avg_accumu data shape from [accumulating_func]', avg_accumu_data.shape)
                temp = np.vstack((store_data, avg_accumu_data))
                pipe3.send(temp*scale)
                pipe3.send(sweep + 1 - minus)
                cmd.value = 1

                store_data = np.array([[]])
                avg_cur_data = np.array([[]])
                avg_accumu_data = np.array([[]])
                innen_sweep = 0
            

def communicating(pipe1, pipe2, state, enable_debug):
    state_machine = NI_State_Trans(pipe1, pipe2, state, enable_debug=enable_debug)
    while True:
        cmd = pipe1.recv()
        if cmd == None:
            break
        else:
            if cmd == 'init':
                state_machine.init()
            elif cmd == 'start':
                state_machine.start()
            elif cmd == 'stop':
                state_machine.stop()
            elif cmd == 'config':
                state_machine.config()
            elif cmd == 'deactive':
                state_machine.deactive()
            else:
                if enable_debug: ('wrong command! :', cmd)
                state_machine.deactive()
                break

