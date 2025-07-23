import numpy as np
import time
import numpy as np
import multiprocessing as mp

from ni_x_pulse_time_series_control import communicating, accumulating_func

class ModuleState:
    def __init__(self):
        self._state = 'unlocked'

    def lock(self):
        self._state = 'locked'

    def unlock(self):
        self._state = 'unlocked'

    def __call__(self):
        return self._state

class PulseTimeSeries():
    # config options
    # parameters of clock
    _device_name = 'Dev3'
    clk_terminal = 'ctr0'
    _sample_rate = 10 # in Hz, 1/s
    _frame_size = 100 
    _frame_num = 50
    _physical_sample_clock_output = 'PFI12'

    # parameters of analog channels
    analog_channels = 'ai5'
    _adc_voltage_range = (-10, 10)
    _rw_timeout = 20
    external_sample_clock_source = 'PFI9'

    # debug switch
    _enable_debug = False

    def __init__(self):

        self.controler_pipe1, self.spectrum_pipe1 = mp.Pipe()
        self.average_pipe2, self.spectrum_pipe2 = mp.Pipe()
        self.controler_pipe3, self.average_pipe3 = mp.Pipe()
        self.state_nidaq = mp.Value("i", 1)         # {0, 1, 2} check details in ni_x_control.py
        self.state_average = mp.Value("i", 1)       # {0, 1, 2, 3, -1} check details in ni_x_control.py

        self.nidaq_process = mp.Process(target=communicating, args=(self.spectrum_pipe1, self.spectrum_pipe2, self.state_nidaq, self._enable_debug))
        self.average_process = mp.Process(target=accumulating_func, args=(self.average_pipe2, self.average_pipe3, self.state_average, ))
        self.nidaq_process.start()
        self.average_process.start()
        self.module_state = ModuleState()

        self.controler_pipe1.send('init')
        if self.controler_pipe1.recv() == 1: # ready
            self.controler_pipe1.send(list([self._device_name,
                                            self.clk_terminal,
                                            self._sample_rate,
                                            self._frame_size,
                                            self._frame_num,
                                            self._physical_sample_clock_output,
                                            self.analog_channels,
                                            self._adc_voltage_range,
                                            self._rw_timeout,
                                            self.external_sample_clock_source,
                                            self._enable_debug])) # send parameters
        else:
            if self._enable_debug: 
                print('not ready for init ') # not ready
        if self.controler_pipe1.recv() == 0: # finished
            if self._enable_debug: 
                print('init finished')
        else:
            if self._enable_debug: 
                print('init failed')

    def on_activate(self):
        """Starts up the NI-card and performs sanity checks. 
        """
        if self._enable_debug: 
            print('【FUNC】 on activate')
        self._number_of_gates = int(100)
        self._bin_width = 1
        self._record_length = int(4000)

        self.statusvar = 0


    def on_deactivate(self):
        """ Shut down the NI card.
        """
        if self._enable_debug:  
            print('【FUNC】 on_deactivate')
        self.stop_measure()
        self.state_average.value = -1
        self.controler_pipe1.send('deactive')
        self.controler_pipe1.send(None) # excute communicating
        self.nidaq_process.join()
        self.average_process.join()
        return

    def configure(self, bin_width_s, record_length_s, number_of_gates=0):

        """ Configuration of the fast counter.

        @param float bin_width_s: Length of a single time bin in the time trace
                                  histogram in seconds.
        @param float record_length_s: Total length of the timetrace/each single
                                      gate in seconds.
        @param int number_of_gates: optional, number of gates in the pulse
                                    sequence. Ignore for not gated counter.

        @return tuple(binwidth_s, gate_length_s, number_of_gates):
                    binwidth_s: float the actual set binwidth in seconds
                    gate_length_s: the actual set gate length in seconds
                    number_of_gates: the number of gated, which are accepted
        """
        if self._enable_debug:  
            print('【FUNC】 configure')
        # self._number_of_gates = number_of_gates
        # print(self._number_of_gates)
        # self._bin_width = bin_width_s * 1e5 
        # self._sample_rate = int(1 / self._bin_width)
        # self._record_length = record_length_s
        # self.num_samples = int(self._record_length / self._bin_width) + 1   # per pulse
        # self.statusvar = 1
        # print(self._bin_width, self._record_length, self._sample_rate)
        self._bin_width = bin_width_s
        self._record_length = record_length_s   
        self._number_of_gates = number_of_gates

        
        # lNotifySize_list = np.array([1,2,4,8,16,32,64,128,256,512,1e3,2e3,4e3],dtype='int') # Notify size can only in this list
        # lSegmentSize_list = lNotifySize_list * 1024 / 2 
        # temp_list = np.absolute(lSegmentSize_list - self._record_length / self._bin_width)
         
        # self.lSegmentSize = int(lSegmentSize_list[np.where(temp_list == np.min(temp_list))])
        # self.qwToTransfer = self.lSegmentSize * self._number_of_gates * 2 / 1024
        # self.qwBufferSize = self.qwToTransfer 

        self._sample_rate = int(round(1/self._bin_width))
        self._frame_size = int(self._record_length / self._bin_width)
        self._frame_num = self._number_of_gates

        
        self.controler_pipe1.send('config')
        if self.controler_pipe1.recv() == 1: # ready
            self.controler_pipe1.send(list([self._device_name,
                                            self.clk_terminal,
                                            self._sample_rate,
                                            self._frame_size,
                                            self._frame_num,
                                            self._physical_sample_clock_output,
                                            self.analog_channels,
                                            self._adc_voltage_range,
                                            self._rw_timeout,
                                            self.external_sample_clock_source,
                                            self._enable_debug])) # send parameters
            if self._enable_debug:  print('not ready for config ') # not ready
        if self.controler_pipe1.recv() == 0: # finished
            if self._enable_debug:  print('config finished')
        else:
            if self._enable_debug:  print('config failed')

        return self._bin_width, self._record_length, self._number_of_gates

    def start_measure(self):
        """ Start the fast counter. """
        if self._enable_debug: 
            print('【FUNC】 start_measure')
        self.module_state.lock()
        self.state_nidaq.value, self.state_average.value = 1, 1
        self.controler_pipe1.send('start')
        time.sleep(1)
        self.statusvar = 2
        return 0

    def stop_measure(self):
        """ Stop the fast counter. """
        if self.module_state() == 'locked':
            if self._enable_debug:  
                print('stop_measure')
            self.state_nidaq.value, self.state_average.value = 0, 0
            time.sleep(0.5) # wait for stop
            self.controler_pipe1.send('stop')
            self.module_state.unlock()
        self.statusvar = 1
        return 0

    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        if self._enable_debug:  
            print('【FUNC】 pause_measure')
        if self.module_state() == 'locked':
            self.stop_measure()
            self.statusvar = 3
        return 0

    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        if self._enable_debug:  
            print('【FUNC】 continue_measure')
        if self.module_state() == 'locked':
            self.start_measure()
            time.sleep(1)
            self.statusvar = 2
        return 0
    

    def get_data_trace(self, accumulate=True, timeout=None):
        if self._enable_debug: 
            print('【FUNC】 get_data_trace')
        self.state_average.value = 2 if accumulate else 3

        if timeout:
            if self.controler_pipe3.poll(timeout):
                data = self.controler_pipe3.recv()
            else:
                print('Timeout after %d seconds' % timeout)
                return -1
            
            if self.controler_pipe3.poll(timeout):
                cur_sweep = self.controler_pipe3.recv()
            else:
                print('Timeout after %d seconds' % timeout)
                return -1
        else:
            data = self.controler_pipe3.recv()
            cur_sweep = self.controler_pipe3.recv()

        if self.state_average.value == 1:
            if self._enable_debug:  print('run well---')
        info_dict = {'elapsed_sweeps': cur_sweep,
                     'elapsed_time': None}
        # print('data shape from [get_data_trace]', data.shape)
        return data, info_dict


    def reset_sweep_count(self):
        self.state_nidaq.value = 2  # Reset counter
