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
from scipy.signal import find_peaks

from qudi.core.module import LogicBase
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.core.statusvariable import StatusVar
from qudi.util.mutex import RecursiveMutex
from qudi.util.enums import SamplingOutputMode
from qudi.util.datafitting import FitContainer, FitConfigurationsModel


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
    _default_scan_mode_mw2 = ConfigOption(name='default_scan_mode_mw2',
                                      default='JUMP_LIST',
                                      constructor=lambda x: SamplingOutputMode[x.upper()])
    
    # declare status variables
    _power_mw1 = StatusVar(name='cw_power_mw1', default=-np.inf)
    _power_mw2 = StatusVar(name='cw_power_mw2', default=-np.inf)
    _scan_frequency_ranges_odmr = StatusVar(name='scan_frequency_ranges_odmr',
                                       default=[(2820e6, 2920e6, 200)])
    _scan_frequency_ranges_diff1 = StatusVar(name='scan:frequebcy_ranges_diff1',
                                             default=[(2830e6, 2940e6, 200)])
    _scan_frequency_ranges_diff2 = StatusVar(name='scan:frequebcy_ranges_diff1',
                                             default=[(2900e6, 2910e6, 200)])
    _run_time = StatusVar(name='run_time', default=60)
    _scans_to_average = StatusVar(name='scans_to_average', default=1)
    _mode = StatusVar(name='Mode',default='odmr')
    _data_rate = StatusVar(name='data_rate', default=200)
    _fit_configs = StatusVar(name='fit_configs', default=None)
    
    
    # Internal signals
    #TODO everything there?
    _sigNextLine = QtCore.Signal()


    # Update signals
    #TODO everything there?
    sigElapsedUpdated = QtCore.Signal(float, int)
    sigScanDataUpdated = QtCore.Signal()
    sigScanParametersUpdated = QtCore.Signal(dict)
    sigScanStateUpdated = QtCore.Signal(bool)
    

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
        self._signal_data_odmr = None
        self._signal_data_diff1 = None
        self._signal_data_diff2 = None
        
        self._frequency_data_odmr = None
        self._frequency_data_diff1 = None
        self._frequency_data_diff2 = None
        
        self._fit_results_diff1 = None
        self._fit_results_diff2 = None
        self._fit_results_diff_dr = None
        self._init_counter = None # Counter to determine in which part of the init the programm is, determines various ifs

        self._scan_frequency_ranges_diff1 = None
        self._scan_frequency_ranges_diff2 = None
        

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        # Recall status variables and check against constraints
        mw1_constraints = self._microwave1().constraints
        mw2_constraints = self._microwave2().constraints
        data_constraints = self._data_scanner().constraints

        self._power_mw1 = mw1_constraints.power_in_range(self._power_mw1)[1]
        self._power_mw2 = mw2_constraints.power_in_range(self._power_mw2)[1]
        self._run_time = max(1., self._run_time)
        self._scans_to_average = max(0, int(self._scans_to_average))
        self._init_counter = 0
        for ii, freq_range in enumerate(self._scan_frequency_ranges_odmr):
            self._scan_frequency_ranges_odmr[ii] = (
                mw1_constraints.frequency_in_range(freq_range[0])[1],
                mw1_constraints.frequency_in_range(freq_range[1])[1],
                mw1_constraints.scan_size_in_range(int(freq_range[2]))[1]
            )
        for ii, freq_range in enumerate(self._scan_frequency_ranges_diff1):
            self._scan_frequency_ranges_diff1[ii] = (
                mw1_constraints.frequency_in_range(freq_range[0])[1],
                mw1_constraints.frequency_in_range(freq_range[1])[1],
                mw1_constraints.scan_size_in_range(int(freq_range[2]))[1]
            )
        for ii, freq_range in enumerate(self._scan_frequency_ranges_diff2):
            self._scan_frequency_ranges_diff2[ii] = (
                mw2_constraints.frequency_in_range(freq_range[0])[1],
                mw2_constraints.frequency_in_range(freq_range[1])[1],
                mw2_constraints.scan_size_in_range(int(freq_range[2]))[1]
            )
        
        #TODO: Check against data sampler constraints
        # self._data_rate =

        # Set up fit model and container
        #TODO: How to set these?
        self._fit_config_model = FitConfigurationsModel(parent=self)
        self._fit_config_model.load_configs(self._fit_configs)
        self._fit_container = FitContainer(parent=self, config_model=self._fit_config_model)

        # Elapsed measurement time and number of sweeps
        self._elapsed_time = 0.0
        self._elapsed_sweeps = 0
        self._start_time = 0.0
        self.__estimated_lines = 0


        # Initialize the ODMR data arrays (mean signal and sweep matrix)
        self._initialize_odmr_data()

        self._initialize_diff_data1()
        self._initialize_diff_data2()
        self._initialize_dr_data()
        
        # Connect signals
        self._sigNextLine.connect(self._scan_line, QtCore.Qt.QueuedConnection)


    def _initialize_odmr_data(self):
        """ Initializing the ODMR data arrays (signal and raw data matrix). 
        Note, that for the raw data variables the same ones are used for all datasets"""
        self._frequency_data_odmr = [np.linspace(*r) for r in self._scan_frequency_ranges_odmr]

        self._raw_data = dict()
        self._signal_data_odmr = dict()
        self._freq1 = dict()
        self._freq2 = dict()
        estimated_samples = self._scans_to_average * self._data_rate
        samples_per_line = sum(freq_range[-1] for freq_range in self._scan_frequency_ranges_odmr)
        # Add 5% Safety; Minimum of 1 line
        self.__estimated_lines = max(1, int(1.05 * estimated_samples / samples_per_line))
        for channel in self._data_scanner().constraints.channel_names:
            self._raw_data[channel] = [
                np.full((freq_arr.size, self.__estimated_lines), np.nan) for freq_arr in
                self._frequency_data_odmr
            ]
            self._signal_data_odmr[channel] = [
                np.zeros(freq_arr.size) for freq_arr in self._frequency_data_odmr
            ]
            self._freq1[channel] = [
                np.zeros(1) for freq_arr in self._frequency_data_odmr
            ]
            self._freq2[channel] = [
                np.zeros(1) for freq_arr in self._frequency_data_odmr
            ]

    def _initialize_diff_data1(self):
        """ Initializing the Diff1 data arrays (signal and raw data matrix). """
        self._frequency_data_diff1 = [np.linspace(*r) for r in self._scan_frequency_ranges_diff1]

        self._raw_data = dict()
        self._fit_results_diff1 = dict()
        self._signal_data_diff1 = dict()
        estimated_samples = self._scans_to_average * self._data_rate
        samples_per_line = sum(freq_range[-1] for freq_range in self._scan_frequency_ranges_diff1)
        # Add 5% Safety; Minimum of 1 line
        self.__estimated_lines = max(1, int(1.05 * estimated_samples / samples_per_line))
        for channel in self._data_scanner().constraints.channel_names:
            self._raw_data[channel] = [
                np.full((freq_arr.size, self.__estimated_lines), np.nan) for freq_arr in
                self._frequency_data_diff1
            ]
            self._signal_data_diff1[channel] = [
                np.zeros(freq_arr.size) for freq_arr in self._frequency_data_diff1
            ]
            self._fit_results_diff1[channel] = [None] * len(self._frequency_data_diff1)
    
    
    def _initialize_diff_data2(self):
        """ Initializing the Diff2 data arrays (signal and raw data matrix). """
        self._frequency_data_diff2 = [np.linspace(*r) for r in self._scan_frequency_ranges_diff2]

        self._raw_data = dict()
        self._fit_results_diff2 = dict()
        self._signal_data_diff2 = dict()
        estimated_samples = self._scans_to_average * self._data_rate
        samples_per_line = sum(freq_range[-1] for freq_range in self._scan_frequency_ranges_diff2)
        # Add 5% Safety; Minimum of 1 line
        self.__estimated_lines = max(1, int(1.05 * estimated_samples / samples_per_line))
        for channel in self._data_scanner().constraints.channel_names:
            self._raw_data[channel] = [
                np.full((freq_arr.size, self.__estimated_lines), np.nan) for freq_arr in
                self._frequency_data_diff2
            ]
            self._signal_data_diff2[channel] = [
                np.zeros(freq_arr.size) for freq_arr in self._frequency_data_diff2
            ]
            self._fit_results_diff2[channel] = [None] * len(self._frequency_data_diff2)


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # Stop measurement if it is still running
        self._sigNextLine.disconnect()
        if self.module_state() == 'locked':
            self.stop_scan()


    @QtCore.Slot()
    def stop_scan(self):
        """ Stop the whole calibration operation, regardless where exactly it 
        currently is.

        @return int: error code (0:OK, -1:error)
        """
        with self._threadlock:
            if self.module_state() == 'locked':
                self._microwave1().off()
                self._microwave2().off()
                self.module_state.unlock()
            self.sigScanStateUpdated.emit(False)


    #TODO: Does this logic work with the LockIn?
    @QtCore.Slot()
    def _scan_line(self):
        """ Perform a scans over the specified frequency range until the number 
        of averages is reached
        """
        with self._threadlock:
            # If the odmr measurement is not running do nothing and break the Qt signal loop
            if self.module_state() != 'locked':
                return
            try:
                scanner = self._data_scanner()
                new_counts = scanner.acquire_frame()
                self._microwave1().reset_scan()
                self._microwave2().reset_scan()
            except:
                self.log.exception('Error while trying to read ODMR scan data from hardware:')
                self.stop_scan()
                return
            
            if self._init_counter == 0:
                freq_range = self._scan_frequency_ranges_odmr
            elif self._init_counter == 1:
                freq_range = self._scan_frequency_ranges_diff1
            elif self._init_counter == 2:
                freq_range = self._scan_frequency_ranges_diff2
            elif self._init_counter == 3:
                freq_range = self._scan_frequency_ranges_diff1

            # Add new count data to raw_data array and append if array is too small
            current_line_buffer_size = next(iter(self._raw_data.values()))[0].shape[1]
            if self._elapsed_sweeps == current_line_buffer_size:
                self.log.debug(f'extending data grid for sweep number {self._elapsed_sweeps}')
                expand_arrays = tuple(np.full((r[-1], self.__estimated_lines), np.nan) for r in
                                      freq_range)
                self._raw_data = {
                    ch: [np.concatenate((r, expand_arrays[ii]), axis=0) for ii, r in
                         enumerate(range_list)] for ch, range_list in self._raw_data.items()
                }
                self.log.warning(
                    'raw data scan line buffer was not big enough for the entire measurement. '
                    'Buffer will be expanded.\nOld line buffer size was {0:d}, new line buffer '
                    'size is {1:d}.'.format(current_line_buffer_size,
                                            current_line_buffer_size + self.__estimated_lines)
                )

            # shift data in the array "up" and add new data at the "bottom"
            for ch, range_list in self._raw_data.items():
                start = 0
                for range_index, range_params in enumerate(freq_range):
                    range_list[range_index] = np.roll(range_list[range_index], 1, axis=1)
                    tmp = new_counts[ch][start:start + range_params[-1]]
                    range_list[range_index][0:len(tmp), 0] = tmp
                    start += range_params[-1]

            # Calculate averaged signal
            if self._init_counter == 0:
                self._calculate_signal_odmr()
            elif self._init_counter == 1:
                self._calculate_signal_data1()
            elif self._init_counter == 2:
                self._calculate_signal_data2()
            elif self._init_counter == 3:
                self._calculate_signal_dr()

            # Update elapsed time/sweeps
            self._elapsed_sweeps += 1
            
            # Fire update signals
            self.sigElapsedUpdated.emit(self._elapsed_sweeps)
            self.sigScanDataUpdated.emit()
            if self._scans_to_average >= self._elapsed_sweeps:
                self.stop_scan()
            else:
                self._sigNextLine.emit()
            return
    
    #TODO: Does this work with Lock in?
    def _calculate_signal_odmr(self):
        for channel, raw_data_list in self._raw_data.items():
            for range_index, raw_data in enumerate(raw_data_list):
                masked_raw_data = np.ma.masked_invalid(raw_data)
                if masked_raw_data.compressed().size == 0:
                    arr_size = self._frequency_data_odmr[range_index].size
                    self._signal_data_odmr[channel][range_index] = np.zeros(arr_size)
                elif self._scans_to_average > 0:
                    self._signal_data_odmr[channel][range_index] = np.mean(
                        masked_raw_data[:, :self._scans_to_average],
                        axis=1
                    ).compressed()
                    if self._signal_data_odmr[channel][range_index].size == 0:
                        arr_size = self._frequency_data_odmr[range_index].size
                        self._signal_data_odmr[channel][range_index] = np.zeros(arr_size)
                else:
                    self._signal_data_odmr[channel][range_index] = np.mean(masked_raw_data,
                                                                    axis=1).compressed()
            #TODO: Integrate data to real odmr


    def _calculate_signal_data1(self):
        for channel, raw_data_list in self._raw_data.items():
            for range_index, raw_data in enumerate(raw_data_list):
                masked_raw_data = np.ma.masked_invalid(raw_data)
                if masked_raw_data.compressed().size == 0:
                    arr_size = self._frequency_data_diff1[range_index].size
                    self._signal_data_diff1[channel][range_index] = np.zeros(arr_size)
                elif self._scans_to_average > 0:
                    self._signal_data_diff1[channel][range_index] = np.mean(
                        masked_raw_data[:, :self._scans_to_average],
                        axis=1
                    ).compressed()
                    if self._signal_data_diff1[channel][range_index].size == 0:
                        arr_size = self._frequency_data_diff1[range_index].size
                        self._signal_data_diff1[channel][range_index] = np.zeros(arr_size)
                else:
                    self._signal_data_diff1[channel][range_index] = np.mean(masked_raw_data,
                                                                    axis=1).compressed()

    
    def _calculate_signal_data2(self):
        for channel, raw_data_list in self._raw_data.items():
            for range_index, raw_data in enumerate(raw_data_list):
                masked_raw_data = np.ma.masked_invalid(raw_data)
                if masked_raw_data.compressed().size == 0:
                    arr_size = self._frequency_data_diff2[range_index].size
                    self._signal_data_diff2[channel][range_index] = np.zeros(arr_size)
                elif self._scans_to_average > 0:
                    self._signal_data_diff2[channel][range_index] = np.mean(
                        masked_raw_data[:, :self._scans_to_average],
                        axis=1
                    ).compressed()
                    if self._signal_data_diff2[channel][range_index].size == 0:
                        arr_size = self._frequency_data_diff1[range_index].size
                        self._signal_data_diff2[channel][range_index] = np.zeros(arr_size)
                else:
                    self._signal_data_diff2[channel][range_index] = np.mean(masked_raw_data,
                                                                    axis=1).compressed()


####################################
############ Properties ############
####################################
    @property
    def fit_config_model(self):
        return self._fit_config_model

    @property
    def fit_container(self):
        return self._fit_container

    @property
    def fit_results_diff1(self):
        return self._fit_results_diff1.copy()

    @property
    def fit_results_diff2(self):
        return self._fit_results_diff2.copy()
    
    @property
    def data_constraints(self):
        return self._data_scanner().constraints

    @property
    def microwave_constraints(self):
        return self._microwave1().constraints

    @property
    def microwave_constraints(self):
        return self._microwave2().constraints
    
    @property
    def signal_data_odmr(self):
        return self._signal_data_odmr.copy()

    @property
    def signal_data_diff1(self):
        return self._signal_data_diff1.copy()

    @property
    def signal_data_diff2(self):
        return self._signal_data_diff2.copy()

    @property
    def raw_data(self):
        return self._raw_data.copy()

    @property
    def frequency_data_odmr(self):
        return self._frequency_data_odmr.copy()
    
    @property
    def frequency_data_diff1(self):
        return self._frequency_data_diff1.copy()
    
    @property
    def frequency_data_diff2(self):
        return self._frequency_data_diff2.copy()

    @property
    def scans_to_average(self):
        return self._scans_to_average

    @scans_to_average.setter
    def scans_to_average(self, number_of_scans):
        self.set_scans_to_average(number_of_scans)

    @QtCore.Slot(int)
    def set_scans_to_average(self, number_of_scans):
        """ Sets the number of scans to average for the sum of the data.
        Note that the averages for the odmr and the differential are the same

        @param int number_of_scans: desired number of scans to average
        """
        with self._threadlock:
            scans_to_average = int(number_of_scans)
            if scans_to_average != self._scans_to_average:
                self._scans_to_average = scans_to_average
                self._calculate_signal_data1()
                self._calculate_signal_data2()
                self.sigScanParametersUpdated.emit({'averaged_scans': self._scans_to_average})
                self.sigScanDataUpdated.emit()


############################################
############# Main #########################
############################################


    @QtCore.Slot()
    def start_calibration(self):
        """Does the whole calibration: ODMR scans of the whole spectrum, zoomed 
        in differentials of the (automatically) selected transition and calculation 
        of the scalar factors
        """
        with self._threadlock:
            if self.module_state() != 'idle':
                self.log.error('Can not start calibration. Measurement is already running.')
                self.sigScanStateUpdated.emit(True)
                return

            # Full ODMR scan
            try:
                self.run_initial_odmr()
            except:
                self.module_state.unlock()
                self.log.exception('Unable to start initial ODMR scan. Error while trying:')
                self.sigScanStateUpdated.emit(False)
                return  

            try:
                self.freq_finder_odmr()
            except:
                self.module_state.unlock()
                self.log.exception('Unable to find the frequencies for differenttial sweeps. Error while trying:')
                self.sigScanStateUpdated.emit(False)
                return  

            # Find freq1
            self._frequency_data_diff1 = np.linspace()
            self._init_counter = 1
            try:
                self.run_locking_f1()
            except:
                self.module_state.unlock()
                self.log.exception('Unable to start first differential scan. Error while trying:')
                self.sigScanStateUpdated.emit(False)
                return

            # Find freq2
            self._init_counter = 2
            try:
                self.run_locking_f2()
            except:
                self.module_state.unlock()
                self.log.exception('Unable to start second differential scan. Error while trying:')
                self.sigScanStateUpdated.emit(False)
                return


    def run_initial_odmr(self):
        microwave = self._microwave1()
        sampler = self._data_scanner()
        sample_rate = self._data_rate
        freq_data = self._frequency_data_odmr
        
        # switch scan mode if necessary
        if self._default_scan_mode_mw1 != SamplingOutputMode.JUMP_LIST and len(
                self._scan_frequency_ranges_diff1) > 1:
            mode = SamplingOutputMode.JUMP_LIST
            self.log.info('Multiple ODMR scan ranges set up. Trying to switch scanner to '
                            'output mode "JUMP_LIST".')
        else:
            mode = self._default_scan_mode_mw1
        if mode == SamplingOutputMode.JUMP_LIST:
            frequencies = np.concatenate(freq_data)
            samples = len(frequencies)
        elif mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
            frequencies = self._scan_frequency_ranges_diff1[0]
            samples = frequencies[-1]

        
        # Set up data acquisition device
        sampler.set_sample_rate(sample_rate)
        sampler.set_frame_size(samples)
        # Set up microwave scan and start it
        microwave.configure_scan(self._scan_power, frequencies, mode, sample_rate)
        microwave.start_scan()

        self._elapsed_sweeps = 0
        self.sigElapsedUpdated.emit(self._elapsed_sweeps)
        self._initialize_odmr_data()
        self.sigScanDataUpdated.emit()
        self.sigScanStateUpdated.emit(True)
        self._sigNextLine.emit()

            
    def run_locking_f1(self):
        microwave = self._microwave1()
        sampler = self._data_scanner()

        sample_rate = self._data_rate
        
        freq_data = self._frequency_data_diff1
        # switch scan mode if necessary
        if self._default_scan_mode_mw1 != SamplingOutputMode.JUMP_LIST and len(
                self._scan_frequency_ranges_diff1) > 1:
            mode = SamplingOutputMode.JUMP_LIST
            self.log.info('Multiple ODMR scan ranges set up. Trying to switch scanner to '
                            'output mode "JUMP_LIST".')
        else:
            mode = self._default_scan_mode_mw1
        if mode == SamplingOutputMode.JUMP_LIST:
            frequencies = np.concatenate(freq_data)
            samples = len(frequencies)
        elif mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
            frequencies = self._scan_frequency_ranges_diff1[0]
            samples = frequencies[-1]



        # Set up data acquisition device
        sampler.set_sample_rate(sample_rate)
        sampler.set_frame_size(samples)
        # Set up microwave scan and start it
        microwave.configure_scan(self._power_mw1, frequencies, mode, sample_rate)
        microwave.start_scan()

        self._elapsed_sweeps = 0
        self.sigElapsedUpdated.emit(self._elapsed_sweeps)
        self._initialize_diff_data1()
        self.sigScanDataUpdated.emit()
        self.sigScanStateUpdated.emit(True)
        self._sigNextLine.emit()

    def run_locking_f2(self):
        microwave = self._microwave2()
        sampler = self._data_scanner()

        sample_rate = self._data_rate
        
        freq_data = self._frequency_data_diff2
        # switch scan mode if necessary
        if self._default_scan_mode_mw2 != SamplingOutputMode.JUMP_LIST and len(
                self._scan_frequency_ranges_diff2) > 1:
            mode = SamplingOutputMode.JUMP_LIST
            self.log.info('Multiple ODMR scan ranges set up. Trying to switch scanner to '
                            'output mode "JUMP_LIST".')
        else:
            mode = self._default_scan_mode_mw2
        if mode == SamplingOutputMode.JUMP_LIST:
            frequencies = np.concatenate(freq_data)
            samples = len(frequencies)
        elif mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
            frequencies = self._scan_frequency_ranges_diff2[0]
            samples = frequencies[-1]



        # Set up data acquisition device
        sampler.set_sample_rate(sample_rate)
        sampler.set_frame_size(samples)
        # Set up microwave scan and start it
        microwave.configure_scan(self._power_mw2, frequencies, mode, sample_rate)
        microwave.start_scan()

        self._elapsed_sweeps = 0
        self.sigElapsedUpdated.emit(self._elapsed_sweeps)
        self._initialize_diff_data2()
        self.sigScanDataUpdated.emit()
        self.sigScanStateUpdated.emit(True)
        self._sigNextLine.emit()

    def freq_finder_odmr(self):
        """Note: Assumes the odmr peaks of interest are the central ones 
        of the highest and lowest frequency triplet triplet """
        for channel in self._signal_data_odmr:
            for range_index in self._signal_data_odmr[channel]:
                minima = find_peaks(-self._signal_data_odmr[channel])
                self._freq1[channel][range_index] = self.frequency_data_odmr[minima[1]]
                self._freq2[channel][range_index] = self.frequency_data_odmr[minima[-2]]
        return