# -*- coding: utf-8 -*-

"""
A hardware module for communicating with the fast counter FPGA.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

import numpy as np
import ctypes
import time
import numpy as np
from transitions import Machine
import multiprocessing as mp
from pyspcm import *
from spcm_tools import *

from qudi.util.mutex import RecursiveMutex
from qudi.core.configoption import ConfigOption
from qudi.util.helpers import natural_sort
from qudi.interface.fast_counter_interface import FastCounterInterface
from qudi.core.configoption import ConfigOption


class SpectrumFastSampling(FastCounterInterface):

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self._thread_lock = RecursiveMutex()

        self.controler_pipe1, self.spectrum_pipe1 = mp.Pipe()
        self.average_pipe2, self.spectrum_pipe2 = mp.Pipe()
        self.controler_pipe3, self.average_pipe3 = mp.Pipe()
        self.state_1 = mp.Value("i", 1) #1 for RUN, 0 for STOP
        self.state_3 = mp.Value("i", 1) #1 for RUN, 0 for STOP

        self.spectrum_process = mp.Process(target=communicating, args=(self.spectrum_pipe1, self.spectrum_pipe2, self.state_1, ))
        self.average_process = mp.Process(target=average_func, args=(self.average_pipe2, self.average_pipe3, self.state_3, ))
        self.spectrum_process.start()
        self.average_process.start()

        self.controler_pipe1.send('init')
        if self.controler_pipe1.recv() == 1: # ready
            self.controler_pipe1.send(np.array([4,8,4096,8,20,1,5000,5000], dtype='int32')) # send parameters
        else:
            print('not ready for init ') # not ready
        if self.controler_pipe1.recv() == 0: # finished
            print('init finished')
        else:
            print('init failed')

    def on_activate(self):
        """Starts up the NI-card and performs sanity checks. 
        """
        print('on activate')
        self._number_of_gates = int(100)
        self._bin_width = 1
        self._record_length = int(4000)

        self.statusvar = 0

    def get_constraints(self):
        """ Retrieve the hardware constrains from the Fast counting device.

        @return dict: dict with keys being the constraint names as string and
                      items are the definition for the constaints.

         The keys of the returned dictionary are the str name for the constraints
        (which are set in this method).

                    NO OTHER KEYS SHOULD BE INVENTED!

        If you are not sure about the meaning, look in other hardware files to
        get an impression. If still additional constraints are needed, then they
        have to be added to all files containing this interface.

        The items of the keys are again dictionaries which have the generic
        dictionary form:
            {'min': <value>,
             'max': <value>,
             'step': <value>,
             'unit': '<value>'}

        Only the key 'hardware_binwidth_list' differs, since they
        contain the list of possible binwidths.

        If the constraints cannot be set in the fast counting hardware then
        write just zero to each key of the generic dicts.
        Note that there is a difference between float input (0.0) and
        integer input (0), because some logic modules might rely on that
        distinction.

        ALL THE PRESENT KEYS OF THE CONSTRAINTS DICT MUST BE ASSIGNED!
        """
        print('get_constraints')
        constraints = dict()
        constraints['hardware_binwidth_list'] = [1 / 1000e6]
        return constraints

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        print('on_deactivate')
        self.stop_measure()
        self.state_3.value = -1
        self.controler_pipe1.send('deactive')
        self.controler_pipe1.send(None) # excute communicating
        self.spectrum_process.join()
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
        print('configure')
        self._number_of_gates = number_of_gates
        print(self._number_of_gates)
        self._bin_width = bin_width_s * 1e5 
        self._sample_rate = int(1 / self._bin_width)
        self._record_length = record_length_s
        self.num_samples = int(self._record_length / self._bin_width) + 1   # per pulse
        self.statusvar = 1
        print(self._bin_width, self._record_length, self._sample_rate)
        
        self.controler_pipe1.send('config')
        if self.controler_pipe1.recv() == 1: # ready
            self.controler_pipe1.send(np.array([4,8,4096,8,20,1,5000,5000], dtype='int32')) # send parameters
        else:
            print('not ready for config ') # not ready
        if self.controler_pipe1.recv() == 0: # finished
            print('config finished')
        else:
            print('config failed')

        return self._bin_width, self._record_length, self._number_of_gates

    def start_measure(self):
        """ Start the fast counter. """
        print('start_measure')
        self.module_state.lock()
        self.state_1.value, self.state_3.value = 1, 1
        self.controler_pipe1.send('start')
        self.statusvar = 2
        return 0

    def stop_measure(self):
        """ Stop the fast counter. """
        if self.module_state() == 'locked':
            print('stop_measure')
            self.state_1.value, self.state_3.value = 0, 0
            time.sleep(0.5) # wait for stop
            self.controler_pipe1.send('stop')
            self.module_state.unlock()
        self.statusvar = 1
        return 0

    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        print('pause_measure')
        if self.module_state() == 'locked':
            self.stop_measure()
            self.statusvar = 3
        return 0

    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        print('continue_measure')
        if self.module_state() == 'locked':
            self.start_measure()
            self.statusvar = 2
        return 0

    def is_gated(self):
        """ Check the gated counting possibility.
        Boolean return value indicates if the fast counter is a gated counter
        (TRUE) or not (FALSE).
        """
        return True

    def get_data_trace(self):
        """ Polls the current timetrace data from the fast counter.

        @return numpy.array: 2 dimensional array of dtype = int64. This counter
                             is gated the the return array has the following
                             shape:
                                returnarray[gate_index, timebin_index]

        The binning, specified by calling configure() in forehand, must be taken
        care of in this hardware class. A possible overflow of the histogram
        bins must be caught here and taken care of.
        """
        print('get_data_trace')
        self.state_3.value = 2
        data = self.controler_pipe3.recv()
        cur_sweep = self.controler_pipe3.recv()
        if self.state_3.value == 1:
            print('run well---')
        info_dict = {'elapsed_sweeps': cur_sweep,
                     'elapsed_time': None}

        return data, info_dict


    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as
            return value.

        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
        -1 = error state
        """
        return self.statusvar

    def get_binwidth(self):
        """ Returns the width of a single timebin in the timetrace in seconds. """
        print('get_binwidth')
        width_in_seconds = self._bin_width 
        return 5e-8
    
# =========================additional codes=============================================
# =============create 2 parallel process to get data and caculate average ==============

class Spectrum_State_Trans(object):
    states = ['IDLE', 'INIT', 'SS']
    transitions = [
        {'trigger': 'init', 'source': 'IDLE', 'dest': 'INIT', 'before': 'INIT_begin'},
        {'trigger': 'start', 'source': 'INIT', 'dest': 'SS', 'before': 'SS_begin'},
        {'trigger': 'stop', 'source': 'SS', 'dest': 'INIT', 'before': 'SS_stop'},
        {'trigger': 'config', 'source': 'INIT', 'dest': 'INIT', 'before': 'INIT_begin'},
        {'trigger': 'deactive', 'source': 'INIT', 'dest': 'IDLE', 'before': 'process_exit'},
        {'trigger': 'deactive', 'source': 'SS', 'dest': 'IDLE', 'before': 'process_exit'},
    ]
    def __init__(self, pipe1, pipe2, state):
        # Initialize the state machine
        self.machine = Machine(model=self, states=Spectrum_State_Trans.states,
                               transitions=Spectrum_State_Trans.transitions, initial='IDLE')
        self.pipe1 = pipe1
        self.pipe2 = pipe2
        self._state= state

        self.sweep = 0

        self.szErrorTextBuffer = create_string_buffer(ERRORTEXTLEN)
        self.dwError = uint32()
        self.lStatus = int32()
        self.lAvailUser = int32()
        self.lPCPos = int32()
        self.lChCount = int32()
        self.qwTotalMem = uint64(0)
        self.lSegmentIndex = uint32(0)
        self.lSegmentCnt = uint32(0)
        self.llSamplingrate = int64(0)

        # open card
        # uncomment the second line and replace the IP address to use remote
        # cards like in a digitizerNETBOX
        self.hCard = spcm_hOpen(create_string_buffer(b'/dev/spcm0'))
        # hCard = spcm_hOpen(create_string_buffer(b'TCPIP::192.168.1.10::inst0::INSTR'))
        if not self.hCard:
            sys.stdout.write("no card found...\n")
            exit(1)

        # read type, function and sn and check for A/D card
        self.lCardType = int32(0)
        spcm_dwGetParam_i32(self.hCard, SPC_PCITYP, byref(self.lCardType))
        self.lSerialNumber = int32(0)
        spcm_dwGetParam_i32(self.hCard, SPC_PCISERIALNO, byref(self.lSerialNumber))
        self.lFncType = int32(0)
        spcm_dwGetParam_i32(self.hCard, SPC_FNCTYPE, byref(self.lFncType))
        self.lFeatureMap = int32(0)
        spcm_dwGetParam_i32(self.hCard, SPC_PCIFEATURES, byref(self.lFeatureMap))

        self.sCardName = szTypeToName(self.lCardType.value)
        if self.lFncType.value == SPCM_TYPE_AI:
            sys.stdout.write("Found: {0} sn {1:05d}\n".format(self.sCardName, self.lSerialNumber.value))
        else:
            sys.stdout.write("Card: {0} sn {1:05d} not supported by this program !\n".format(self.sCardName, self.lSerialNumber.value))
            spcm_vClose(self.hCard)
            exit(1)

        if self.lFeatureMap.value & SPCM_FEAT_MULTI == 0:
            sys.stdout.write("Multiple Recording Option not installed !\n")
            spcm_vClose(self.hCard)
            exit(1)


    def INIT_begin(self):
        print('start initializing')
        self.pipe1.send(1) # ready
        parameters = self.pipe1.recv()

        # default parameters -------------------------------------
        # self.qwBufferSize = uint64(MEGA_B(4))
        # self.lNotifySize = int32(KILO_B(8))
        # self.lSegmentSize = 4096
        # self.qwToTransfer = uint64(MEGA_B(8))
        # self.samplerate = int64(MEGA(20))
        # self.channel = 1
        # self.timeout = 5000
        # self.input_range = 5000
        #  -------------------------------------------------------

        self.qwBufferSize = uint64(MEGA_B(4))
        self.lNotifySize = int32(KILO_B(8))
        self.lSegmentSize = 4096
        self.qwToTransfer = uint64(KILO_B(512))
        self.samplerate = int64(MEGA(20))
        self.channel = 1
        self.timeout = 5000
        self.input_range = 5000
        

        # do a simple standard setup
        spcm_dwSetParam_i32(self.hCard, SPC_CHENABLE,         1)           # just 1 channel enabled
        spcm_dwSetParam_i32(self.hCard, SPC_PRETRIGGER,       1024)                   # 1k of pretrigger data at start of FIFO mode
        spcm_dwSetParam_i32(self.hCard, SPC_CARDMODE,         SPC_REC_FIFO_MULTI)     # multiple recording FIFO mode
        spcm_dwSetParam_i32(self.hCard, SPC_SEGMENTSIZE,      self.lSegmentSize)           # set segment size
        spcm_dwSetParam_i32(self.hCard, SPC_POSTTRIGGER,      self.lSegmentSize - 128)     # set posttrigger
        spcm_dwSetParam_i32(self.hCard, SPC_LOOPS,            0)                      # set loops
        spcm_dwSetParam_i32(self.hCard, SPC_CLOCKMODE,        SPC_CM_INTPLL)          # clock mode internal PLL
        spcm_dwSetParam_i32(self.hCard, SPC_CLOCKOUT,         0)                      # no clock output
        spcm_dwSetParam_i32(self.hCard, SPC_TRIG_EXT0_MODE,   SPC_TM_POS)             # set trigger mode
        spcm_dwSetParam_i32(self.hCard, SPC_TRIG_TERM,        0)                      # set trigger termination
        spcm_dwSetParam_i32(self.hCard, SPC_TRIG_ORMASK,      SPC_TMASK_EXT0)         # trigger set to external
        spcm_dwSetParam_i32(self.hCard, SPC_TRIG_ANDMASK,     0)                      # ...
        spcm_dwSetParam_i32(self.hCard, SPC_TRIG_EXT0_ACDC,   COUPLING_DC)            # trigger coupling
        spcm_dwSetParam_i32(self.hCard, SPC_TRIG_EXT0_LEVEL0, 1500)                   # trigger level of 1.5 Volt
        spcm_dwSetParam_i32(self.hCard, SPC_TRIG_EXT0_LEVEL1, 0)                      # unused
        spcm_dwSetParam_i32(self.hCard, SPC_TIMEOUT,          5000)                   # timeout 5 s
        spcm_dwSetParam_i32(self.hCard, SPC_PATH0,            1)                      # 50 Ohm termination
        spcm_dwSetParam_i32(self.hCard, SPC_ACDC0,            0)                      # clock mode internal PLL

        spcm_dwGetParam_i32(self.hCard, SPC_CHCOUNT, byref(self.lChCount))
        for lChannel in range(0, self.lChCount.value, 1):
            spcm_dwSetParam_i32(self.hCard, SPC_AMP0 + lChannel * (SPC_AMP1 - SPC_AMP0), 5000)

        # we try to set the samplerate to 100 kHz (M2i) or 20 MHz on internal PLL, no clock output
        spcm_dwSetParam_i64(self.hCard, SPC_SAMPLERATE, int64(MEGA(20)))
        print('samplerate : {0}MHz '.format(20))

        # read back current sampling rate from driver
        spcm_dwGetParam_i64(self.hCard, SPC_SAMPLERATE, byref(self.llSamplingrate))


        # define the data buffer
        # we try to use continuous memory if available and big enough
        self.pvBuffer = ptr8()  # will be cast to correct type later
        self.qwContBufLen = uint64(0)
        spcm_dwGetContBuf_i64(self.hCard, SPCM_BUF_DATA, byref(self.pvBuffer), byref(self.qwContBufLen))
        sys.stdout.write("ContBuf length: {0:d}\n".format(self.qwContBufLen.value))
        if self.qwContBufLen.value >= self.qwBufferSize.value:
            sys.stdout.write("Using continuous buffer\n")
        else:
            self.pvBuffer = cast(pvAllocMemPageAligned(self.qwBufferSize.value), ptr8)  # cast to ptr8 to make it behave like the continuous memory
            sys.stdout.write("Using buffer allocated by user program\n")

        sys.stdout.write("\n  !!! Using external trigger - please connect a signal to the trigger input !!!\n\n")

        # set up buffer for data transfer
        spcm_dwDefTransfer_i64(self.hCard, SPCM_BUF_DATA, SPCM_DIR_CARDTOPC, self.lNotifySize, self.pvBuffer, uint64(0), self.qwBufferSize)
        

        # test-----------------------------------
        # time.sleep(1)
        print('parameters: ', parameters)
        print('set up finished')
        # test-----------------------------------

        self.pipe1.send(0) # finished

        
    def SS_begin(self):
        print('start sampling')

        # start everything
        self.dwError = spcm_dwSetParam_i32(self.hCard, SPC_M2CMD, M2CMD_CARD_START | M2CMD_CARD_ENABLETRIGGER | M2CMD_DATA_STARTDMA)

        # check for error
        if self.dwError != 0:  # != ERR_OK
            spcm_dwGetErrorInfo_i32(self.hCard, None, None, self.szErrorTextBuffer)
            sys.stdout.write("{0}\n".format(self.szErrorTextBuffer.value))
            spcm_vClose(self.hCard)
            exit(1)

        # run the FIFO mode and loop through the data
        else:
            lMin = int(32767)  # normal python type
            lMax = int(-32768)  # normal python type
            self.stop_symbol = 0
            

            while not self.stop_symbol and self._state.value:
                self.qwTotalMem = uint64(0)
                self.lSegmentCnt = uint32(0)
                store_data = np.array([[]])
                while self.qwTotalMem.value < self.qwToTransfer.value:
                    temp = np.array([])
                    self.dwError = spcm_dwSetParam_i32(self.hCard, SPC_M2CMD, M2CMD_DATA_WAITDMA)
                    if self._state.value == 0:
                      self.stop_symbol = 1
                      break
                    if self.dwError != ERR_OK:
                        if self.dwError == ERR_TIMEOUT:
                            sys.stdout.write("... Timeout\n")
                            self.stop_symbol = 1
                            break
                        else:
                            sys.stdout.write("... Error: {0:d}\n".format(self.dwError))
                            self.stop_symbol = 1
                            break

                    else:
                        spcm_dwGetParam_i32(self.hCard, SPC_M2STATUS,            byref(self.lStatus))
                        spcm_dwGetParam_i32(self.hCard, SPC_DATA_AVAIL_USER_LEN, byref(self.lAvailUser))
                        spcm_dwGetParam_i32(self.hCard, SPC_DATA_AVAIL_USER_POS, byref(self.lPCPos))

                        if self.lAvailUser.value >= self.lNotifySize.value:
                            self.qwTotalMem.value += self.lNotifySize.value

                            # this is the point to do anything with the data
                            # e.g. calculate minimum and maximum of the acquired data
                            pnData = cast(addressof(self.pvBuffer.contents) + self.lPCPos.value, ptr16)  # cast to pointer to 16bit integer
                            # lNumSamples = int(self.lNotifySize.value / 2)  # two bytes per sample
                            # for i in range(0, lNumSamples - 1, 1):
                            #     temp = np.append(temp, pnData[i])
                            #     if pnData[i] < lMin:
                            #         lMin = pnData[i]
                            #     if pnData[i] > lMax:
                            #         lMax = pnData[i]

                            #     self.lSegmentIndex.value += 1
                            #     self.lSegmentIndex.value %= self.lSegmentSize

                            #     # check end of acquired segment
                            #     if self.lSegmentIndex.value == 0:
                            #         self.lSegmentCnt.value += 1

                            #         # sys.stdout.write("Segment[{0:d}] : Minimum: {1:d}, Maximum: {2:d}\n".format(self.lSegmentCnt.value, lMin, lMax))
                            #         # sys.stdout.write("cur: {0}, need: {1}\n".format(self.qwTotalMem.value, self.qwToTransfer.value))

                            #         lMin = 32767
                            #         lMax = -32768
                            temp = np.array(pnData[:self.lNotifySize.value//2 - 1])
                            if not len(store_data[0]):
                                store_data = np.array([temp])
                            else:
                                store_data = np.append(store_data, [temp], axis=0)
                            spcm_dwSetParam_i32(self.hCard, SPC_DATA_AVAIL_CARD_LEN, self.lNotifySize)
                            
                self.sweep += 1
                print('sended sweep is :', self.sweep)
                self.pipe2.send(store_data)  
                self.pipe2.send(self.sweep) 
            self.pipe2.send(None)
            print('sampling finished!')

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
        print('stop sampling')
        # send stop command
        self.dwError = spcm_dwSetParam_i32(self.hCard, SPC_M2CMD, M2CMD_CARD_STOP | M2CMD_DATA_STOPDMA)
        self.sweep = 0
        print("Stop/Pause.... \n")

    def process_exit(self):
        print('stop processing')
        self.dwError = spcm_dwSetParam_i32(self.hCard, SPC_M2CMD, M2CMD_CARD_STOP | M2CMD_DATA_STOPDMA)
        print("Exit...\n")
        # clean up
        spcm_vClose(self.hCard)


def average_func(pipe2, pipe3, cmd):
        while True:
            store_data = np.array([[]])
            minus = 0
            if cmd.value == -1:
                break
            while cmd.value: # cmd = 1 for RUN, 2 for get data,  0 for STOP, -1 for exit
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
                if cmd.value == 2:
                    pipe3.send((store_data * 5000 / 32768).astype('int16'))  # gated (change unit * 5000mv / int16's max value 32768)
                    pipe3.send(sweep + 1 - minus)
                    cmd.value = 1
            

def communicating(pipe1, pipe2, state):
    spectrum = Spectrum_State_Trans(pipe1, pipe2, state)
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
                print('wrong command! :', cmd)
                spectrum.deactive()
                break