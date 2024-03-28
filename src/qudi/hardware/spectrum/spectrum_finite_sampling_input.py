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
import time
import numpy as np
import multiprocessing as mp
from pyspcm import *
from spcm_tools import *

from qudi.core.configoption import ConfigOption
from qudi.util.helpers import natural_sort
from qudi.interface.finite_sampling_input_interface import FiniteSamplingInputInterface, FiniteSamplingInputConstraints


#use spectrum card to acquire data
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

    
    def on_activate(self) -> None:
        hCard = spcm_hOpen(create_string_buffer(b'/dev/spcm0'))
        if not hCard:
            sys.stdout.write("no card found...\n")
            exit(1)

    def on_deactivate(self) -> None:
        spcm_vClose(hCard)
        sys.stdout.write("card closed...\n")

    @property
    def constraints(self):
        return FiniteSamplingInputConstraints(
            sample_rate={'min': 0.1, 'max': 200, 'step': 0.1, 'unit': 'MHz'},
            frame_size={'min': 1, 'max': 4096, 'step': 1, 'unit': 'samples'},
            samples_in_buffer={'min': 0, 'max': 4096, 'step': 1, 'unit': 'samples'}
        )
    
    @property
    def active_channels(self):
        return frozenset([f'channel_{self.channel}'])
    
    @property
    def sample_rate(self):
        return self.samplerate
    
    @property
    def frame_size(self):
        return self.lSegmentSize
    
    @property
    def samples_in_buffer(self):
        return self.qwToTransfer
    
    

    def set_sample_rate(self, rate):
        """
        """
    
    def set_active_channels(self, channels):
        if channels != self.active_channels:
            raise ValueError(f'Invalid channel(s) selected: {channels}')
    

    
    