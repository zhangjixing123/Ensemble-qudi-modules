# common packages:
import numpy as np
import numpy as np
from transitions import Machine
from qudi.util.helpers import natural_sort
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
        if self._enable_debug:  print('start initializing')
        self.pipe1.send(1) # ready
        parameters = self.pipe1.recv()
        if self._enable_debug:  print('parameters: ', parameters)

        # default parameters -------------------------------------
        # self.qwBufferSize = uint64(KILO_B(parameters[0]))
        # self.lSegmentSize = int(parameters[1])
        # self.lNotifySize = int32(KILO_B(int(self.lSegmentSize * 2 / 1024))) 
        # self.qwToTransfer = uint64(KILO_B(int(parameters[2])))
        # self.samplerate = int64(KILO(parameters[3]))
        # self.channel = int(parameters[4])
        # self.timeout = int(parameters[5])
        # self.input_range = int(parameters[6])
        self._device_name = parameters[0]
        self.clk_terminal = parameters[1]
        self._sample_rate = parameters[2]
        self._frame_size = parameters[3]
        self._physical_sample_clock_output = parameters[4]
        self.sampleMode_clk = cst.AcquisitionType.FINITE
        self.analog_channels = parameters[5]
        self._adc_voltage_range = parameters[6]
        self._rw_timeout = parameters[7]
        self.external_sample_clock_source = parameters[8]
        self.sampleMode_ai = cst.AcquisitionType.FINITE
        if self._enable_debug:
            print("Current parameters are:")
            print("Device Name = {0}".format(parameters[0]))
            print("Clock Terminal = {0}".format(parameters[1]))
            print("Sample Rate = {0} S/s".format(parameters[2]))
            print("Frame Size = {0} samples".format(parameters[3]))
            print("Physical Sample Clock Output = {0}".format(parameters[4]))
            print("Sample Mode (Clock) = cst.AcquisitionType.FINITE")
            print("Analog Channels = {0}".format(parameters[5]))
            print("ADC Voltage Range = {0} V".format(parameters[6]))
            print("Read/Write Timeout = {0} ms".format(parameters[7]))
            print("External Sample Clock Source = {0}".format(parameters[8]))
            print("Sample Mode (AI) = cst.AcquisitionType.FINITE")
        #  -------------------------------------------------------

        # do a simple standard setup

        # 1. Check if device is connected and set device to use
        dev_names = ni.system.System().devices.device_names
        if self._device_name.lower() not in set(dev.lower() for dev in dev_names):
            raise ValueError(
                f'Device name "{self._device_name}" not found in list of connected devices: '
                f'{dev_names}\nActivation of NIXSeriesInStreamer failed!'
            )
        for dev in dev_names:
            if dev.lower() == self._device_name.lower():
                self._device_name = dev
                break
        self._device_handle = ni.system.Device(self._device_name)

        self.__all_counters = tuple(
            ctr.split('/')[-1] for ctr in self._device_handle.co_physical_chans.channel_names if
            'ctr' in ctr.lower())
        self.__all_digital_terminals = tuple(
            term.rsplit('/', 1)[-1].lower() for term in self._device_handle.terminals if 'PFI' in term)
        self.__all_analog_terminals = tuple(
            term.rsplit('/', 1)[-1].lower() for term in self._device_handle.ai_physical_chans.channel_names)
        

        # 2. Check analog input channels
        analog_sources = set(src for src in self._analog_channel_units)
        if analog_sources:
            source_set = set(self._extract_terminal(src) for src in analog_sources)
            invalid_sources = source_set.difference(set(self.__all_analog_terminals))
            if invalid_sources:
                self.log.error('Invalid analog source channels encountered. Following sources will '
                               'be ignored:\n  {0}\nValid analog input channels are:\n  {1}'
                               ''.format(', '.join(natural_sort(invalid_sources)),
                                         ', '.join(self.__all_analog_terminals)))
            analog_sources = set(natural_sort(source_set.difference(invalid_sources)))
        
        # 3. reset device
        self._device_handle = ni.system.Device(self._device_name)
        try:
            self._device_handle.reset_device()
            print('Reset device {0}.'.format(self._device_name))
        except ni.DaqError:
            print('Could not reset NI device {0}'.format(self._device_name))


        # 4. configerate the clock
        # not necessary due to externel clk

        # 5. configerate the analog channel
        self.ai = ni.Task()
        ai_ch_str = ','.join(['/{0}/{1}'.format(self._device_name, c) for c in self.analog_channels])
        self.ai.ai_channels.add_ai_voltage_chan(ai_ch_str,
                                            max_val=max(self._adc_voltage_range),
                                            min_val=min(self._adc_voltage_range))
        self.ai.timing.cfg_samp_clk_timing(self._sample_rate,
                                            source= '/{0}/{1}'.format(self._device_name, self.external_sample_clock_source),
                                            active_edge=ni.constants.Edge.RISING,
                                            sample_mode=self.sampleMode_ai,
                                            samps_per_chan=self._frame_size)
        # If sample_mode is CONTINUOUS_SAMPLES, 
        # NI-DAQmx uses this value (samps_per_chan) to determine the buffer size.
        self.ai.control(ni.constants.TaskMode.TASK_RESERVE)
        self._ai_reader = AnalogMultiChannelReader(self.ai.in_stream)
        self._ai_reader.verify_array_shape = False


        self.pipe1.send(0) # finished


    def SS_begin(self):
        if self._enable_debug: ('start sampling')

        # start everything
        try:
            self.ai.start()
            self.stop_symbol = 0
        except ni.DaqError:
            print('schief gehen bei Starten von ai task')

        # get buffered samples
        while not self.stop_symbol and self._state.value:

            if self._state.value == 0:
                self.stop_symbol = 1
            store_data = np.array([[]])

            data = dict()
            number_of_samples = self._frame_size
            try:
                data_buffer = np.zeros(number_of_samples * len(self.analog_channels))
                read_samples = self._ai_reader.read_many_sample(
                    data_buffer,
                    number_of_samples_per_channel=number_of_samples,
                    timeout=self._rw_timeout)
                # if read_samples != number_of_samples:
                #     return data
                for num, ai_channel in enumerate(self.analog_channels):
                    data[ai_channel] = data_buffer[num * number_of_samples:(num + 1) * number_of_samples]
            except ni.DaqError:
                print('Getting samples from streamer failed.')

            store_data = np.array(data[self.analog_channels[0]]).reshape(-1, 1)
                        
            if self._state.value == 2:
                print('Reset sweep count from %d to 0' % self.sweep)
                self.sweep = 0
                self._state.value = 1
            self.sweep += 1
            if self._enable_debug: ('sended sweep is :', self.sweep)
            self.pipe2.send(store_data)
            self.pipe2.send(self.sweep) 
        self.pipe2.send(None)
        if self._enable_debug: ('sampling finished!')

        # test-----------------------------------
        # sweep = 0
        # while self._state.value: 
        #     time.sleep(0.5)
        #     self.pipe2.send(np.array([1,2,3,4]))
        #     sweep += 1
        #     print('{0}st loop'.format(sweep))
        # self.pipe2.send(None)
        # print('sampling finished!')
        # test-----------------------------------       

    def SS_stop(self):
        if self._enable_debug: ('stop sampling')
        # send stop command
        try:
            self.ai.stop()
            self.ai.close()
        except ni.DaqError:
            print('Error while trying to terminate ai task.')
        self.sweep = 0
        if self._enable_debug: ("Stop/Pause.... \n")

    def process_exit(self):
        if self._enable_debug: ('stop processing')
        try:
            self.ai.stop()
            self.ai.close()
        except ni.DaqError:
            print('Error while trying to terminate ai task.')
        if self._enable_debug: ("Exit...\n")
    
    def _extract_terminal(term_str):
        """
        Helper function to extract the bare terminal name from a string and strip it of the device
        name and dashes.
        Will return the terminal name in lower case.

        @param str term_str: The str to extract the terminal name from
        @return str: The terminal name in lower case
        """
        term = term_str.strip('/').lower()
        if 'dev' in term:
            term = term.split('/', 1)[-1]
        return term

    def _extract_ai_di_from_input_channels(self, input_channels):
        """
        Takes an iterable and returns the split up ai and di channels
        @return tuple(di_channels), tuple(ai_channels))
        """
        input_channels = tuple(self._extract_terminal(src) for src in input_channels)

        di_channels = tuple(channel for channel in input_channels if 'pfi' in channel)
        ai_channels = tuple(channel for channel in input_channels if 'ai' in channel)

        assert (di_channels or ai_channels), f'No channels could be extracted from {*input_channels,}'

        return tuple(di_channels), tuple(ai_channels)



def average_func(pipe2, pipe3, cmd, Vmax=5000):
    # cmd list:
    #    0: STOP
    #    1: RUN
    #    2: get acummulated data
    #    3: get last data
    #   -1: exit

    scale = Vmax / 32768    # gated (change unit * 5000mv / int16's max value 32768)
    while True:
        store_data = np.array([[]])
        minus = 0
        if cmd.value == -1:
            break
        while cmd.value:
            cur_data = pipe2.recv()
            if cur_data is None:
                break 
            sweep = pipe2.recv() - 1
            if not sweep: # first sweep
                store_data = cur_data
            else:
                if len(cur_data) == len(store_data):
                    store_data = store_data*(sweep/(sweep+1)) + cur_data/(sweep + 1)
                    minus = 0
                else:
                    minus = 1
            if cmd.value == 3:
                if len(cur_data) == len(store_data):
                    pipe3.send((cur_data).astype('int16'))
                    pipe3.send(1)
                    cmd.value = 1
            if cmd.value == 2:
                pipe3.send((store_data*scale).astype('int16'))
                pipe3.send(sweep + 1 - minus)
                cmd.value = 1
            

def communicating(pipe1, pipe2, state, enable_debug):
    spectrum = NI_State_Trans(pipe1, pipe2, state, enable_debug=enable_debug)
    while True:
        cmd = pipe1.recv()
        if cmd == None:
            break
        else:
            if cmd == 'init':
                spectrum.init()
            elif cmd == 'start':
                spectrum.start()
            elif cmd == 'stop':
                spectrum.stop()
            elif cmd == 'config':
                spectrum.config()
            elif cmd == 'deactive':
                spectrum.deactive()
            else:
                if enable_debug: ('wrong command! :', cmd)
                spectrum.deactive()
                break

