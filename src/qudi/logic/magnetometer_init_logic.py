# -*- coding: utf-8 -*-

"""
This file contains the Qudi Logic module base class.

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
import time
import datetime
import matplotlib.pyplot as plt
from PySide2 import QtCore

from qudi.core.module import LogicBase
from qudi.core.connector import Connector
from qudi.util.mutex import RecursiveMutex
from qudi.core.configoption import ConfigOption
from qudi.core.statusvariable import StatusVar
from qudi.util.enums import SamplingOutputMode


class MagnetometerInitLogic(LogicBase):
    """
    This is the Logic class for the initialization based on CW lock-in 
    measurements

    example config for copy-paste:

    magnetometer_init_logic:
        module.Class: 'magnetometer_init_logic.MagnetometerInitLogic'
        connect:
            microwave1: <microwave_name>
            microwave2: <microwave_name>
            .... #TODO everything there?
        options:
            default_scan_mode_mw1: 'JUMP_LIST'  # optional
            default_scan_mode_mw2: 'JUMP_LIST'  # optional
            .... #TODO everything there?
            
    """
    # declare connectors
    _microwave1 = Connector(name='microwave1', interface='MicrowaveInterface')
    _microwave2 = Connector(name='microwave2', interface='MicrowaveInterface')
    _data_scanner = Connector(name='data_scanner', interface='LockinInterface')

    # declare config options
    #TODO everything there?
    _default_scan_mode_mw1 = ConfigOption(name='default_scan_mode_mw1',
                                      default='JUMP_LIST',
                                      constructor=lambda x: SamplingOutputMode[x.upper()])
    _default_scan_mode_mw1 = ConfigOption(name='default_scan_mode_mw2',
                                      default='JUMP_LIST',
                                      constructor=lambda x: SamplingOutputMode[x.upper()])
    
    # declare status variables
    #TODO how to set freqeuncies: fully automated, center+range, begin+end?
    _cw_frequency_mw1 = StatusVar(name='cw_frequency_mw1', default=2850e6)
    _cw_frequency_mw2 = StatusVar(name='cw_frequency_mw1', default=2880e6)
    _cw_power_mw1 = StatusVar(name='cw_power_mw1', default=-np.inf)
    _cw_power_mw2 = StatusVar(name='cw_power_mw2', default=-np.inf)
    _scan_frequency_ranges = StatusVar(name='scan_frequency_ranges',
                                       default=[(2820e6, 2920e6, 101)])
    _run_time = StatusVar(name='run_time', default=60)
    _scans_to_average = StatusVar(name='scans_to_average', default=0)
    
    # Internal signals
    #TODO everything there?

    # Update signals
    #TODO everything there?


    __default_fit_configs = (
        {'name'             : 'Gaussian Dip',
         'model'            : 'Gaussian',
         'estimator'        : 'Dip',
         'custom_parameters': None},

        {'name'             : 'Lorentzian Dip',
         'model'            : 'Lorentzian',
         'estimator'        : 'Dip',
         'custom_parameters': None},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._threadlock = RecursiveMutex()

        self._elapsed_time = 0.0
        self._elapsed_sweeps = 0
        self.__estimated_lines = 0
        self._start_time = 0.0
        self._fit_container = None
        self._fit_config_model = None

        self._raw_data = None
        self._signal_data = None
        self._frequency_data = None
        self._fit_results = None

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        # Recall status variables and check against constraints
        mw1_constraints = self._microwave1().constraints
        mw2_constraints = self._microwave2().constraints
        data_constraints = self._data_scanner().constraints

        self._cw_power_mw1 = mw1_constraints.power_in_range(self._cw_power_mw1)[1]
        self._cw_power_mw2 = mw2_constraints.power_in_range(self._cw_power_mw2)[1]
        self._run_time = max(1., self._run_time)
        self._scans_to_average = max(0, int(self._scans_to_average))
        
        #TODO: Check against data sampler constraints
        # self._data_rate =


        # Elapsed measurement time and number of sweeps
        self._elapsed_time = 0.0
        self._elapsed_sweeps = 0
        self._start_time = 0.0
        self.__estimated_lines = 0


        # Initialize the ODMR data arrays (mean signal and sweep matrix)
        self._initialize_odmr_data()
        















    def _initialize_odmr_data(self):
        """ Initializing the ODMR data arrays (signal and raw data matrix). """
        self._frequency_data = [np.linspace(*r) for r in self._scan_frequency_ranges]

        self._raw_data = dict()
        self._fit_results = dict()
        self._signal_data = dict()
        estimated_samples = self._run_time * self._data_rate
        samples_per_line = sum(freq_range[-1] for freq_range in self._scan_frequency_ranges)
        # Add 5% Safety; Minimum of 1 line
        self.__estimated_lines = max(1, int(1.05 * estimated_samples / samples_per_line))
        for channel in self._data_scanner().constraints.channel_names:
            self._raw_data[channel] = [
                np.full((freq_arr.size, self.__estimated_lines), np.nan) for freq_arr in
                self._frequency_data
            ]
            self._signal_data[channel] = [
                np.zeros(freq_arr.size) for freq_arr in self._frequency_data
            ]
            self._fit_results[channel] = [None] * len(self._frequency_data)