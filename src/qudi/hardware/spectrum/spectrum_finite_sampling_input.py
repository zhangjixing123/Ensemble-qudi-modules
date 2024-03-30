# -*- coding: utf-8 -*-

"""
Interface for input of data of a certain length at a given sampling rate and data type.

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
import numpy as np
from pyspcm import *
from spcm_tools import *

from qudi.core.configoption import ConfigOption
from qudi.util.helpers import natural_sort
from qudi.interface.finite_sampling_input_interface import FiniteSamplingInputInterface, FiniteSamplingInputConstraints


#use spectrum card to acquire data keep the same functionality as ni_x_series_finite_sampling_input.py but useing spectrum card
class SpectrumFiniteSamplingInput(FiniteSamplingInputInterface):
    """
    Interface for input of data of a certain length atspectrum_finite_sampling_input:
        module.Class: 'spectrum.spectrum_finite_sampling_input.SpectrumFiniteSamplingInput'
        options:
            buffer_size: 4096       # unit: uint64(MEGA_B(4)), as huge as possible
            segment_size: 4096         # samples per trigger
            samples_per_loop: 1024  # unit: uint64(KILO_B( ))
            sample_rate: 20            # unit: int64(MEGA( ))
            channel: 1                 # channel = 1
            timeout: 5000              # unit: ms
            input_range: 5000          # unit: mV
    """

    #config options
    qwBufferSize = ConfigOption(name='buffer_size', default=4, missing="info")
    lSegmentSize = ConfigOption(name='segment_size', default=4096, missing="info")
    # NotifySize = int32(KILO_B(lSegmentSize / 1024 * 2)) # data with type int16
    qwToTransfer = ConfigOption(name='samples_per_loop', default=512, missing="info") #loop size
    samplerate = ConfigOption(name='sample_rate', default=20, missing="info")
    channel = ConfigOption(name='channel', default=1, missing="info")
    timeout = ConfigOption(name='timeout', default=5000, missing="info")
    input_range = ConfigOption(name='input_range', default=5000, missing="info")



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #keep the same as spectrum example simple_rec_fifo.py
        self.szErrorTextBuffer = create_string_buffer(ERRORTEXTLEN)
        self.dwError = uint32()
        self.lStatus = int32()
        self.lAvailUser = int32()
        self.lPCPos = int32()
        self.qwTotalMem = uint64(0)
        self.qwToTransfer = uint64(MEGA_B(8))

        # settings for the FIFO mode buffer handling
        self.qwBufferSize = uint64(MEGA_B(1))
        # qwBufferSize = uint64(KILO_B(128))
        self.lNotifySize = int32(KILO_B(16))

        #print out the parameters
        sys.stdout.write(f"buffer size: {self.qwBufferSize}\n")
        sys.stdout.write(f"samples per loop: {self.qwToTransfer}\n")

        # open card
        # uncomment the second line and replace the IP address to use remote
        # cards like in a digitizerNETBOX
        self.hCard = spcm_hOpen(create_string_buffer(b'/dev/spcm0'))
        # hCard = spcm_hOpen(create_string_buffer(b'TCPIP::192.168.1.10::inst0::INSTR'))
        if not self.hCard:
            sys.stdout.write("no card found...\n")
            exit(1)

        # get card type name from driver
        self.qwValueBufferLen = 20
        self.pValueBuffer = pvAllocMemPageAligned(self.qwValueBufferLen)
        spcm_dwGetParam_ptr(self.hCard, SPC_PCITYP, self.pValueBuffer, self.qwValueBufferLen)
        self.sCardName = self.pValueBuffer.value.decode('UTF-8')
        sys.stdout.write(f"card found: {self.sCardName}\n")

        # read type, function and sn and check for A/D card
        self.lCardType = int32(0)
        spcm_dwGetParam_i32(self.hCard, SPC_PCITYP, byref(self.lCardType))
        self.lSerialNumber = int32(0)
        spcm_dwGetParam_i32(self.hCard, SPC_PCISERIALNO, byref(self.lSerialNumber))
        self.lFncType = int32(0)
        spcm_dwGetParam_i32(self.hCard, SPC_FNCTYPE, byref(self.lFncType))
            #check A/D cards
        if self.lFncType.value == SPCM_TYPE_AI:
            sys.stdout.write("Found: {0} sn {1:05d}\n".format(self.sCardName, self.lSerialNumber.value))
        else:
            sys.stdout.write("This is an example for A/D cards.\nCard: {0} sn {1:05d} not supported by example\n".format(self.sCardName, self.lSerialNumber.value))
            spcm_vClose(self.hCard)
            exit(1)

        # do a simple standard setup
        spcm_dwSetParam_i32(self.hCard, SPC_CHENABLE,       1)                      # just 1 channel enabled
        spcm_dwSetParam_i32(self.hCard, SPC_PRETRIGGER,     1024)                   # 1k of pretrigger data at start of FIFO mode
        spcm_dwSetParam_i32(self.hCard, SPC_CARDMODE,       SPC_REC_FIFO_SINGLE)    # single FIFO mode
        spcm_dwSetParam_i32(self.hCard, SPC_TIMEOUT,        5000)                   # timeout 5 s
        spcm_dwSetParam_i32(self.hCard, SPC_TRIG_ORMASK,    SPC_TMASK_SOFTWARE)     # trigger set to software     Defines the events included within the trigger OR mask of the card.
        spcm_dwSetParam_i32(self.hCard, SPC_TRIG_ANDMASK,   0)                      # ...
        spcm_dwSetParam_i32(self.hCard, SPC_CLOCKMODE,      SPC_CM_INTPLL)          # clock mode internal PLL

        self.lBitsPerSample = int32(0)
        spcm_dwGetParam_i32(self.hCard, SPC_MIINST_BITSPERSAMPLE, byref(self.lBitsPerSample)) #Resolution of the samples in bits.

        # we try to set the samplerate to 100 kHz (M2i) or 20 MHz on internal PLL, no clock output
        if ((self.lCardType.value & TYP_SERIESMASK) == TYP_M2ISERIES) or ((self.lCardType.value & TYP_SERIESMASK) == TYP_M2IEXPSERIES):
            spcm_dwSetParam_i64(self.hCard, SPC_SAMPLERATE, KILO(100))
        else:
            spcm_dwSetParam_i64(self.hCard, SPC_SAMPLERATE, MEGA(20))

        spcm_dwSetParam_i32(self.hCard, SPC_CLOCKOUT, 0)                            # no clock output

        # define the data buffer
        # we try to use continuous memory if available and big enough
        self.pvBuffer = ptr8()  # will be cast to correct type later
        self.qwContBufLen = uint64(0)
        spcm_dwGetContBuf_i64(self.hCard, SPCM_BUF_DATA, byref(self.pvBuffer), byref(self.qwContBufLen))
        sys.stdout.write("ContBuf length: {0:d}\n".format(self.qwContBufLen.value))
        if self.qwContBufLen.value >= self.qwBufferSize.value:
            sys.stdout.write("Using continuous buffer\n")
        else:
            pvBuffer = cast(pvAllocMemPageAligned(self.qwBufferSize.value), ptr8)  # cast to ptr8 to make it behave like the continuous memory
            sys.stdout.write("Using buffer allocated by user program\n")

        # set up buffer for data transfer
        spcm_dwDefTransfer_i64(self.hCard, SPCM_BUF_DATA, SPCM_DIR_CARDTOPC, self.lNotifySize, pvBuffer, uint64(0), self.qwBufferSize)

    
    
    def on_activate(self) -> None:
        # start everything
        self.dwError = spcm_dwSetParam_i32(self.hCard, SPC_M2CMD, M2CMD_CARD_START | M2CMD_CARD_ENABLETRIGGER | M2CMD_DATA_STARTDMA)
        # check for error
        if self.dwError != 0:  # != ERR_OK
            spcm_dwGetErrorInfo_i32(self.hCard, None, None, self.szErrorTextBuffer)
            sys.stdout.write("{0}\n".format(self.szErrorTextBuffer.value))
            spcm_vClose(self.hCard)
            exit(1)

        # run the FIFO mode and loop through the data
            #... here we would do something with the data

    def on_deactivate(self) -> None:
        spcm_vClose(self.hCard)
        sys.stdout.write("card closed...\n")


    
    