# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface file to control microwave devices.

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

from abc import abstractmethod

from qudi.core.module import Base
from qudi.util.enums import SamplingOutputMode, FrequencyModulationSource, FrequencyModulationChannel
from qudi.util.helpers import in_range


class MicrowaveInterface(Base):
    """This class defines the interface to simple microwave generators with or without frequency
    scan capability.
    """

    @property
    @abstractmethod
    def constraints(self):
        """The microwave constraints object for this device.

        @return MicrowaveConstraints:
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def is_scanning(self):
        """Read-Only boolean flag indicating if a scan is running at the moment. Can be used
        together with module_state() to determine if the currently running microwave output is a
        scan or CW.
        Should return False if module_state() is 'idle'.

        @return bool: Flag indicating if a scan is running (True) or not (False)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def cw_power(self):
        """Read-only property returning the currently configured CW microwave power in dBm.

        @return float: The currently set CW microwave power in dBm.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def cw_frequency(self):
        """Read-only property returning the currently set CW microwave frequency in Hz.

        @return float: The currently set CW microwave frequency in Hz.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def scan_power(self):
        """Read-only property returning the currently configured microwave power in dBm used for
        scanning.

        @return float: The currently set scanning microwave power in dBm
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def scan_frequencies(self):
        """Read-only property returning the currently configured microwave frequencies used for
        scanning.

        In case of self.scan_mode == SamplingOutputMode.JUMP_LIST, this will be a 1D numpy array.
        In case of self.scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP, this will be a tuple
        containing 3 values (freq_begin, freq_end, number_of_samples).
        If no frequency scan has been configured, return None.

        @return float[]: The currently set scanning frequencies. None if not set.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def scan_mode(self):
        """Read-only property returning the currently configured scan mode Enum.

        @return SamplingOutputMode: The currently set scan mode Enum
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def scan_sample_rate(self):
        """Read-only property returning the currently configured scan sample rate in Hz.

        @return float: The currently set scan sample rate in Hz
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def modulation_deviation(self):
        """Read-only property of the configured frequency modulation deviation in Hz

        @return float: Current frquency modulation deviation in Hz
        """

    @property
    @abstractmethod
    def modulation_source(self):
        """Read-only property of the configured frequency modulation source.

        @return FrequencyModulationSource: Current frequency modulation source
        """

    @property
    @abstractmethod
    def modulation_channel(self):
        """Read-only property of the configured frequency modulation channel.

        @return FrequencyModulationChannel: Current frequency modulation channel
        """

    @abstractmethod
    def off(self):
        """Switches off any microwave output (both scan and CW).
        Must return AFTER the device has actually stopped.
        """
        raise NotImplementedError

    @abstractmethod
    def set_cw(self, frequency, power):
        """Configure the CW microwave output. Does not start physical signal output, see also
        "cw_on".

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        """
        raise NotImplementedError

    @abstractmethod
    def cw_on(self):
        """Switches on preconfigured cw microwave output, see also "set_cw".

        Must return AFTER the output is actually active.
        """
        raise NotImplementedError

    @abstractmethod
    def configure_scan(self, power, frequencies, mode, sample_rate):
        """
        """
        raise NotImplementedError

    @abstractmethod
    def start_scan(self):
        """Switches on the preconfigured microwave scanning, see also "configure_scan".

        Must return AFTER the output is actually active (and can receive triggers for example).
        """
        raise NotImplementedError

    @abstractmethod
    def reset_scan(self):
        """Reset currently running scan and return to start frequency.
        Does not need to stop and restart the microwave output if the device allows soft scan reset.
        """
        raise NotImplementedError

    @abstractmethod
    def set_frequency(self,frequency):
        """
        Configuration of the CW frequency. Does not change the physical output state.
        Use with caution, as no runtime checks are performed to allow for in-situ
        changes, necessary for something like a magnetometer.

        NOTE: The proper way would be to implement this as setter of cw_frequency, 
            however this could lead to unexpected behaviour and accidental set 
            parameters in existing code and is therefore ommited

        @param float frequency: frequency set in Hz
        """
        raise NotImplementedError

    def set_power(self,power):
        """
        Configuration of the CW power. Does not change the physical output state.
        Use with caution, as no runtime checks are performed to allow for in-situ
        changes, necessary for something like a magnetometer.

        NOTE: The proper way would be to implement this as setter of cw_power, 
            however this could lead to unexpected behaviour and accidental set 
            parameters in existing code and is therefore ommited

        @param float power: power set in dBm
        """
        raise NotImplementedError

    def configure_modulation(self,deviation=100e3,internal_frequency=None):
        """
        For now only external coupling with AC is implemented.
        Does not change the modulation state, see also "set_mod_state".

        @param float deviation: optional argument to set the initial modulation 
        deviation in Hz (if state: INT) or Hz/V (if state: EXT); default value 100 kHz
        @param float internal_frequency: optional internal modulation frequency 
        if the internal modulation is used; default is None, needs to be explicitly set
        """
        raise NotImplementedError

    def set_mod_deviation(self,deviation):
        """
        Configuration of the modulation deviation in Hz (if state: INT) or 
        Hz/V (if state: EXT).
        Use with caution, as no runtime checks are performed to allow for in-situ
        changes, necessary for something like a magnetometer.

        @param float deviation: modulation depth/deviation to be set
        """
        raise NotImplementedError

    def set_mod_state(self,state):
        """
        Changes the state of the modulation to ON/OFF
        """
        raise NotImplementedError

    
    # ToDo: Think about if the logic should handle trigger settings and expand the interface if so.
    #  But I would argue the trigger config is something static and hard-wired for a specific setup,
    #  so it should be configurable via config and not handled by logic at runtime.

    def _assert_cw_parameters_args(self, frequency, power):
        """ Helper method to unify argument type and value checking against hardware constraints.
        Useful in implementation of "set_cw()".
        """
        # Check power
        assert self.constraints.power_in_range(power)[0], \
            f'CW power to set ({power} dBm) is out of bounds for allowed range ' \
            f'{self.constraints.power_limits}'
        # Check frequency
        assert self.constraints.frequency_in_range(frequency)[0], \
            f'CW frequency to set ({frequency:.9e} Hz) is out of bounds for allowed range ' \
            f'{self.constraints.frequency_limits}'

    def _assert_scan_configuration_args(self, power, frequencies, mode, sample_rate):
        """ Helper method to unify argument type and value checking against hardware constraints.
        Useful in implementation of "configure_scan()".
        """
        # Check power
        assert self.constraints.power_in_range(power)[0], \
            f'Scan power to set ({power} dBm) is out of bounds for allowed range ' \
            f'{self.constraints.power_limits}'
        # Check mode
        assert isinstance(mode, SamplingOutputMode), \
            'Scan mode must be Enum type qudi.util.enums.SamplingOutputMode'
        assert self.constraints.mode_supported(mode), \
            f'Unsupported scan mode "{mode}" encountered'
        # Check sample rate
        assert self.constraints.sample_rate_in_range(sample_rate)[0], \
            f'Sample rate to set ({sample_rate:.9e} Hz) is out of bounds for allowed range ' \
            f'{self.constraints.sample_rate_limits}'
        # Check frequencies
        if mode == SamplingOutputMode.JUMP_LIST:
            samples = len(frequencies)
            min_freq, max_freq = min(frequencies), max(frequencies)
        elif mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
            assert len(frequencies) == 3, \
                'Setting scan frequencies for "EQUIDISTANT_SWEEP" mode requires iterable of 3 ' \
                'values: (start, stop, number_of_points)'
            samples = frequencies[-1]
            min_freq, max_freq = frequencies[:2]
        assert self.constraints.scan_size_in_range(samples)[0], \
            f'Number of samples for frequency scan ({samples}) is out of bounds for ' \
            f'allowed scan size limits {self.constraints.scan_size_limits}'
        assert self.constraints.frequency_in_range(min_freq)[0] and \
               self.constraints.frequency_in_range(max_freq)[0], \
            f'Frequency samples to scan out of bounds.'


class MicrowaveConstraints:
    """A container to hold all constraints for microwave sources.
    """
    def __init__(self, power_limits, frequency_limits, scan_size_limits, sample_rate_limits,
                 scan_modes, fm_sources=None, fm_channels=None, fm_limits = None, fm_interal_frequency = None):
        """
        @param float[2] power_limits: Allowed min and max power
        @param float[2] frequency_limits: Allowed min and max frequency
        @param int[2] scan_size_limits: Allowed min and max number of samples for scanning
        @param float[2] sample_rate_limits: Allowed min and max scan sample rate (in Hz)
        @param SamplingOutputMode[] scan_modes: Allowed scan mode Enums
        @param FrequencyModulationSource[] fm_sources: optional, allowed frequency 
                modulation scoures Enums; default: None, to allow compatibility with all existing code
                NOTE: all parameters regarding frequency modulation need to be explicitly set 
        @param FrequencyModulationChannel[] fm_sources: optional, allowed frequency 
                modulation channels Enums; default: None, to allow compatibility with all existing code
        @param float[2] fm_limits: optional, allowed min and max frequency modulation deviations; 
                default: None, to allow compatibility with all existing code
        @param float[2] fm_internal_frequency: optional, allowed min and max frequencies 
                of the internal modulation; default: None, to allow for compatibility with all existing code        
        """
        assert len(power_limits) == 2, 'power_limits must be iterable of length 2 (min, max)'
        assert len(frequency_limits) == 2, \
            'frequency_limits must be iterable of length 2 (min, max)'
        assert len(scan_size_limits) == 2, \
            'scan_size_limits must be iterable of length 2 (min, max)'
        assert len(sample_rate_limits) == 2, \
            'sample_rate_limits must be iterable of length 2 (min, max)'
        assert all(isinstance(mode, SamplingOutputMode) for mode in scan_modes), \
            'scan_modes must be iterable containing only qudi.util.enums.SamplingOutputMode Enums'
        assert all(isinstance(source, FrequencyModulationSource) for source in fm_sources), \
            'fm_source must be iterable containing only qudi.util.enums.FrequencyModulationSource Enums'
        assert all(isinstance(channel, FrequencyModulationChannel) for channel in fm_channels), \
            'fm_channels must be iterable containing only qudi.util.enums.FrequencyModulationChannel Enums'
        assert len(fm_limits) == 2, \
            'fm_limits must be iterable of length 2 (min, max)'
        assert len(fm_interal_frequency) == 2, \
            'fm_internal_frequency must be iterable of length 2 (min, max)'
                
        
        tmp = [int(lim) for lim in scan_size_limits]
        self._scan_size_limits = (min(tmp), max(tmp))
        self._sample_rate_limits = (min(sample_rate_limits), max(sample_rate_limits))
        self._scan_modes = frozenset(scan_modes)
        self._fm_sources = (frozenset(fm_sources) if fm_sources is not None else None)
        self._fm_channels = (frozenset(fm_channels) if fm_channels is not None else None)
        self._power_limits = (min(power_limits), max(power_limits))
        self._frequency_limits = (min(frequency_limits), max(frequency_limits))
        self._fm_limits = (min(fm_limits), max(fm_limits))
        self._fm_internal_frequency = (min(fm_interal_frequency), max(fm_interal_frequency))     

    @property
    def scan_size_limits(self):
        return self._scan_size_limits

    @property
    def min_scan_size(self):
        return self._scan_size_limits[0]

    @property
    def max_scan_size(self):
        return self._scan_size_limits[1]

    @property
    def sample_rate_limits(self):
        return self._sample_rate_limits

    @property
    def min_sample_rate(self):
        return self._sample_rate_limits[0]

    @property
    def max_sample_rate(self):
        return self._sample_rate_limits[1]

    @property
    def power_limits(self):
        return self._power_limits

    @property
    def min_power(self):
        return self._power_limits[0]

    @property
    def max_power(self):
        return self._power_limits[1]

    @property
    def frequency_limits(self):
        return self._frequency_limits

    @property
    def min_frequency(self):
        return self._frequency_limits[0]

    @property
    def max_frequency(self):
        return self._frequency_limits[1]

    @property
    def scan_modes(self):
        return self._scan_modes

    @property
    def fm_sources(self):
        return self._fm_sources

    @property
    def fm_channels(self):
        return self._fm_channels

    @property
    def fm_limits(self):
        return self.fm_limits

    @property
    def max_fm(self):
        return self._fm_limits[0]

    @property
    def min_fm(self):
        return self._fm_limits[1]

    @property
    def fm_internal_frequency(self):
        return self._fm_internal_frequency

    @property
    def max_fm_internal_frequency(self):
        return self._fm_internal_frequency[0]

    @property
    def min_fm_internal_frequency(self):
        return self._fm_internal_frequency[1]

    def frequency_in_range(self, value):
        return in_range(value, *self._frequency_limits)

    def power_in_range(self, value):
        return in_range(value, *self._power_limits)

    def scan_size_in_range(self, value):
        return in_range(value, *self._scan_size_limits)

    def sample_rate_in_range(self, value):
        return in_range(value, *self._sample_rate_limits)

    def mode_supported(self, mode):
        return mode in self._scan_modes

    def fm_source_supported(self, fm_source):
        return fm_source in self._fm_sources

    def fm_channel_supported(self, fm_channel):
        return fm_channel in self._fm_channels

    def fm_in_range(self, value):
        return in_range(value, *self._fm_limits)

    def fm_internal_frequency_in_range(self,value):
        return in_range(value, *self._fm_internal_frequency)