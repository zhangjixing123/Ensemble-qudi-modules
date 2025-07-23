import numpy as np
import numpy as np
from transitions import Machine
from pyspcm import *
from spcm_tools import *



# Create 2 parallel process to get data and caculate average
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
    def __init__(self, pipe1, pipe2, state, enable_debug=False):
        # Initialize the state machine
        self.machine = Machine(model=self, states=Spectrum_State_Trans.states,
                               transitions=Spectrum_State_Trans.transitions, initial='IDLE')
        self.pipe1 = pipe1
        self.pipe2 = pipe2
        self._state= state

        self.sweep = 0
        self.sweep_reset = False

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
        self._enable_debug = enable_debug
        

    def INIT_begin(self):
        if self._enable_debug:  
            print('>> start initializing')
        self.pipe1.send(1) # ready
        parameters = self.pipe1.recv()
        if self._enable_debug:  
            print('parameters: ', parameters)

        # default parameters -------------------------------------
        self.device_name = parameters[0]
        self.qwBufferSize = uint64(KILO_B(int(float(parameters[1])))*4)
        self.lSegmentSize = int(float(parameters[2]))
        # self.qwBufferSize = uint64(MEGA_B(
        #     int(self.lSegmentSize * 2 / 1024)*int(parameters[2])
        # ))
        print(self.qwBufferSize.value, self.lSegmentSize)
        # self.qwBufferSize = uint64(KILO_B(parameters[2]))
        # self.qwBufferSize = uint64(MEGA_B(800))
        # print('Buffer size:', self.qwBufferSize.value)
        # print('lSegment size:', self.lSegmentSize)
        self.lNotifySize = int32(KILO_B(int(self.lSegmentSize * 2 / 1024))) 
        self.qwToTransfer = uint64(KILO_B(int(float(parameters[3]))))
        # print('qwToTransfer:', self.qwToTransfer.value)

        # check unit of sample rate
        temp_sample_rate = float(parameters[4])
        if temp_sample_rate >= 1e6:  # MHz, max. 250 MHz
            self.samplerate = int64(MEGA(int(temp_sample_rate/1e6)))
        elif temp_sample_rate >= 1e3: #kHz
            self.samplerate = int64(KILO(int(temp_sample_rate/1e3)))
        else:                        # Hz
            print('sample rate should be at least bigger than 1 kHz !\n')
            print('current sample rate is: ', temp_sample_rate)
            exit(1)

        # print('Samplerate:', self.samplerate.value)
        self.channel = int(parameters[5])
        self.timeout = float(parameters[6])
        self.input_range = int(parameters[7])
        self._enable_debug = parameters[8]
        if self._enable_debug:
            print("current parameters is: ")
            print("qwBufferSize = {0} kb".format(parameters[1]))
            print('lSegmentSize = {0}'.format(int(float(parameters[2]))))
            print('lNotifySize = {0} kb'.format(int(self.lSegmentSize * 2 / 1024)))
            print('qwToTransfer = {0} kb'.format(int(float(parameters[3]))))
            print('samplerate = {0} kS/s'.format(parameters[4]))
            print('channel = {0}'.format(int(float(parameters[5]))))
            print('timeout = {0} ms'.format(int(float(parameters[6]))))
            print('input_range = {0} mV '.format(int(parameters[7])))
        #  -------------------------------------------------------
        # open the card
        try:
            if not self.hCard:
                self.open_card()
        except AttributeError:
            self.open_card()


        
        # do a simple standard setup
        spcm_dwSetParam_i32(self.hCard, SPC_CHENABLE,         self.channel)           # just 1 channel enabled
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
            spcm_dwSetParam_i32(self.hCard, SPC_AMP0 + lChannel * (SPC_AMP1 - SPC_AMP0), self.input_range)

        # we try to set the samplerate to 100 kHz (M2i) or 20 MHz on internal PLL, no clock output
        spcm_dwSetParam_i64(self.hCard, SPC_SAMPLERATE, self.samplerate)

        # read back current sampling rate from driver
        spcm_dwGetParam_i64(self.hCard, SPC_SAMPLERATE, byref(self.llSamplingrate))


        # define the data buffer
        # we try to use continuous memory if available and big enough
        self.pvBuffer = ptr8()  # will be cast to correct type later
        self.qwContBufLen = uint64(0)
        spcm_dwGetContBuf_i64(self.hCard, SPCM_BUF_DATA, byref(self.pvBuffer), byref(self.qwContBufLen))
        # sys.stdout.write("ContBuf length: {0:d}\n".format(self.qwContBufLen.value))
        if self.qwContBufLen.value >= self.qwBufferSize.value:
            sys.stdout.write("Using continuous buffer\n")
        else:
            self.pvBuffer = cast(pvAllocMemPageAligned(self.qwBufferSize.value), ptr8)  # cast to ptr8 to make it behave like the continuous memory
            sys.stdout.write("Using buffer allocated by user program\n")

        sys.stdout.write("\n  !!! Using external trigger - please connect a signal to the trigger input !!!\n\n")

        # set up buffer for data transfer
        # Defines the transfer buffer by using 64 bit unsigned integer values
        # drv_handle hDevice:     handle to an already opened device
        # uint32 dwBufType:       type of the buffer to define as listed above under SPCM_BUF_XXXX
        # uint32 dwDirection:     the transfer direction as defined above
        # uint32 dwNotifySize:    no. of bytes after which an event is sent (0=end of transfer)
        # void* pvDataBuffer:     pointer to the data buffer
        # uint64 qwBrdOffs:       offset for transfer in board memory (zero when using FIFO mode)
        # uint64 qwTransferLen:   buffer length
        spcm_dwDefTransfer_i64(self.hCard, SPCM_BUF_DATA, SPCM_DIR_CARDTOPC, self.lNotifySize, self.pvBuffer, uint64(0), self.qwBufferSize)
        

        self.pipe1.send(0) # finished

    def SS_begin(self):
        if self._enable_debug: 
            print('>> start sampling')

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
            

            # f = open('C:\\Users\\yy3\\qudi\\Data\\2024\\11\\2024-11-29\\spec\\log.txt', 'a+')
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
                        
                        # f.write('211,qwTotalMem,%d\n' % self.qwTotalMem.value)
                        # f.write('212,qwToTransfer,%d\n' % self.qwToTransfer.value)
                        # f.write('213,lAvailUser,%d\n' % self.lAvailUser.value)
                        # f.write('214,lPCPos,%d\n' % self.lPCPos.value)
                        # f.write('215,lNotifySize,%d\n' % self.lNotifySize.value)

                        if self.lAvailUser.value >= self.lNotifySize.value:
                            self.qwTotalMem.value += self.lNotifySize.value
                            # print('216 qwTotalMem:', self.qwTotalMem.value)
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
                            
                            spcm_dwGetParam_i32(self.hCard, SPC_DATA_AVAIL_USER_LEN, byref(self.lAvailUser))
                            spcm_dwGetParam_i32(self.hCard, SPC_DATA_AVAIL_USER_POS, byref(self.lPCPos))

                if self._state.value == 2:
                    print('Reset sweep count from %d to 0' % self.sweep)
                    self.sweep = 0
                    self._state.value = 1
                self.sweep += 1
                if self._enable_debug: 
                    print('sended sweep is :', self.sweep)
                self.pipe2.send(store_data)
                self.pipe2.send(self.sweep) 
            self.pipe2.send(None)
            # f.close()
            if self._enable_debug: 
                print('>> sampling finished!')

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
        if self._enable_debug: 
            print('>> stop sampling')
        # send stop command
        self.dwError = spcm_dwSetParam_i32(self.hCard, SPC_M2CMD, M2CMD_CARD_STOP | M2CMD_DATA_STOPDMA)
        self.sweep = 0
        if self._enable_debug: 
            print(">> Stop/Pause.... \n")

    def process_exit(self):
        if self._enable_debug: 
            print('>> stop processing')
        self.dwError = spcm_dwSetParam_i32(self.hCard, SPC_M2CMD, M2CMD_CARD_STOP | M2CMD_DATA_STOPDMA)
        if self._enable_debug: 
            print(">> Exit...\n")
        # clean up
        spcm_vClose(self.hCard)

    def open_card(self):

        # This function initializes and opens an installed card
        # uncomment the second line and replace the IP address to use remote
        # cards like in a digitizerNETBOX
        device_name = '/dev/{name}'.format(name = self.device_name).encode('utf-8')
        self.hCard = spcm_hOpen(create_string_buffer(device_name))
        # self.hCard = spcm_hOpen(create_string_buffer(b'/dev/spcm0'))
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


def accumulating_func(pipe2, pipe3, cmd, Vmax=5000):
    # cmd list:
    #    0: STOP
    #    1: RUN
    #    2: get acummulated data
    #    3: get last data
    #   -1: exit
    amp = 1 # orginal unit is mV, qudi.pulse supports only integer, but here supports float
    scale = Vmax / 32768 * amp   # gated (change unit * 5000mv / int16's max value 32768)
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
    spectrum = Spectrum_State_Trans(pipe1, pipe2, state, enable_debug=enable_debug)
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

