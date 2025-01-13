"""
This file contains the Qudi Interface file to control lockin devices.

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
from qudi.util.enums import SamplingOutputMode
from qudi.util.helpers import in_range


class LockinInterface(Base):
    """This class defines the interface to simple lockins with or without all 
    lock-in capabilities.
    """


#------- General Status ------------    
    @property
    @abstractmethod
    def constraints(self):
        """The lock-in constraints object for this device.

        @return LockinConstraints:
        """
        raise NotImplementedError
    
    @property
    @abstractmethod
    def demod_status(self):
        """Status of all demodulator modules in the form
        '/devXXXX/demods/0/adcselect': <value>,
        '/devXXXX/demods/0/order': <value>, 
        '/devXXXX/demods/0/timeconstant': <value>, 
        '/devXXXX/demods/0/rate': <value>, 
        '/devXXXX/demods/0/trigger': <value>, 
        '/devXXXX/demods/0/enable': <value>, 
        '/devXXXX/demods/0/oscselect': <value>, 
        '/devXXXX/demods/0/harmonic': <value>, 
        '/devXXXX/demods/0/freq': <value>, 
        '/devXXXX/demods/0/phaseshift': <value>, 
        '/devXXXX/demods/0/sinc': <value>, 
        '/devXXXX/demods/0/sample': {'timestamp': array([<value>], 
        dtype=uint64), 'x': array([<values>]), 'y': array([<value>]), 
        'frequency': array([<value>]), 'phase': array([<value>]), 
        'dio': array([<value>], dtype=uint32), 
        'trigger': array([<value>], dtype=uint32), 'auxin0': array([<value>]), 
        'auxin1': array([<value>]), 
        'time': {'trigger': 0, 'dataloss': False, 'blockloss': False, 
        'ratechange': False, 'invalidtimestamp': False, 'mindelta': 0}}, 
        '....'

        @return struct: Current status
        """
        raise NotImplementedError
    
    @property
    @abstractmethod
    def sigouts_status(self):
        """Status of the Output Channels

        @return struct: Output status
        """
        raise NotImplementedError
    
    @property
    @abstractmethod
    def sigins_status(self):
        """Status of the Input Channels

        @return struct: Input status
        """
        raise NotImplementedError
    
    @property
    @abstractmethod
    def pll_status(self):
        """Status of the PLL Channels

        @return struct: PLL status
        """
        raise NotImplementedError
    
#--------- Demod Status ----------

    @property
    @abstractmethod
    def get_demod_bandwidth(self,module):
        """Read-Only property returning the bandwidth of the low-pass filter 
        for the specified module. 
        
        The bandwidth is returned as time constant and converted seperatly to a 
        frequency. For details see: 
        https://docs.zhinst.com/mfli_user_manual/signal_processing_basics.html
        
        @param int module: module of the LIA
        @return float bandwidth: Current bandwidth of the module in Hz
        """
        raise NotImplementedError
    
    
    @property
    @abstractmethod
    def get_demod_enable(self,module):
        """Read-Only flag indicating if the module is turned on

        @param int module: module of the LIA
        @return bool: Flag if the module is running (1) or not (0)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def get_demod_harmonic(self,module):
        """Read-Only property returning the harmonic order of the used 
        oscillator and the specified module. "1" is the fundamental frequency.

        @param int module: module of the LIA
        @return int: Harmonic of the used oscillator for the module
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def get_demod_order(self,module):
        """Read-Only property returning the order of the low-pass filter
        for the specified module.
        1 --> 6 dB/oct slope
        2 --> 12 dB/oct slope
        3 --> 18 dB/oct slope
        4 --> 24 dB/oct slope
        5 --> 30 dB/oct slope
        6 --> 36 dB/oct slope
        7 --> 42 dB/oct slope
        8 --> 48 dB/oct slope

        @param int module: module of the LIA
        @return int: Order of the low-pass filter for the module
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def get_demod_osc(self,module):
        """Read-Only property returning the selected oscillator for the 
        specified module

        @param int module: module of the LIA
        @return int: Oscillator number specified for the module
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def get_demod_phase(self,module):
        """Read-Only property returning the current phase of the specified
        module
        @param int module: module of the LIA
        @return float: Current phase of the module
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def get_demod_rate(self,module):
        """Read-Only property returning the sample rate for the specified 
        module
        @param int module: module of the LIA
        @return float: Current sample rate for the module
        """
        raise NotImplementedError
    
    @property
    @abstractmethod
    def get_demod_sinc(self,module):
        """Read-Only flag if the sinc filter is running for the specified 
        module

        @param int module: module of the LIA
        @return bool: Flag if sinc filter is enabled
        """
        raise NotImplementedError
    
    @property
    @abstractmethod
    def get_demod_trigger(self,module):
        """Read-Only property returning the trigger status of the specified
        module bit decoded as follows:
        0 --> "Continuous"
        1 --> "b0": DIO0 rising edge
        2 --> "b1": DIO0 falling edge
        4 --> "b2": DIO1 rising edge
        8 --> "b3": DIO1 falling edge
        16 --> "b4": DIO0 high
        32 --> "b5": DIO0 low
        64 --> "b6": DIO1 high
        128 --> "b7": DIO1 low


        @param int module: module of the LIA
        @return int: Trigger status decoded as bit
        """
        raise NotImplementedError

#------- Signal Output Status -----------

    @property
    @abstractmethod
    def get_sigout_enable(self,channel):
        """Read-Only flag indicating if the specified output channel is 
        turned on

        @param int channel: output channel of the LIA
        @return bool: Flag if the channel is running (1) or not (0)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def get_sigout_add(self,channel):
        """Read-Only flag indicating if an external input is added to the 
        specified output channel 

        @param int channel: output channel of the LIA
        @return bool: Flag if a signal is added (1) or not (0)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def get_sigout_enable(self,channel):
        """Read-Only flag indicating if the specified output channel is 
        turned on

        @param int channel: output channel of the LIA
        @return bool: Flag if the channel is running (1) or not (0)
        """
        raise NotImplementedError
    
    @property
    @abstractmethod
    def get_sigout_ampEnable(self,channel):
        """Read-Only flag indicating if the amplitude mixer is activated for the
        specified output channel

        @param int channel: output channel of the LIA
        @return bool: Flag if the amplitude mixer is activated (1) or not (0)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def get_sigout_offset(self,channel):
        """Read-Only property returning the voltage offset of the selected 
        channel

        @param int channel: output channel of the LIA
        @return float: Current set offset in V
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def get_sigout_range(self,channel):
        """Read-Only property returning the current set voltage range of the 
        specified channel.
        WARNING: The range is returned as int although "0.01" and "0.1" V are 
        possible. Both cases are returned as "0".

        @param int channel: output channel of the LIA
        @return int: Current set voltage range in V
        """
        raise NotImplementedError

#--------- Signal Input Status ----------

    @property
    @abstractmethod
    def get_sigin_ac(self,channel):
        """Read-Only flag indicating if the AC coupling of the specified input 
        channel is turned on

        @param int channel: input channel of the LIA
        @return bool: Flag if the AC is turned on (1) or not (0)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def get_sigin_diff(self,channel):
        """Read-Only flag indicating if the differential input mode of the 
        specified input channel is turned on

        @param int channel: input channel of the LIA
        @return bool: Flag if the differential mode is turned on (1) or not (0)
        """
        raise NotImplementedError
    
    @property
    @abstractmethod
    def get_sigin_impedance(self,channel):
        """Read-Only flag indicating if the 50 Ohm impedance of the specified 
        input channel is selected

        @param int channel: input channel of the LIA
        @return bool: Flag if the 50 Ohm impedance is selected on (1) or not (0)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def get_sigin_range(self,channel):
        """Read-Only property returning the set voltage range of the specified 
        input channel is turned on

        @param int channel: input channel of the LIA
        @return float: Current set voltage range in V
        """
        raise NotImplementedError

#---------- PLL Status --------------

    @property
    @abstractmethod
    def get_pll_adcselect(self,channel):
        """Read-Only property returning the input channel selected for the 
        specified PLL channel

        @param int channel: input channel of the LIA
        @return int: Current set input channel
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def get_pll_enable(self,channel):
        """Read-Only flag indicating if the specified PLL channel is set to
        external or internal reference

        @param int channel: input channel of the LIA
        @return bool: Indicating if the channel is in ExtRef (1) or Man (0) mode
        """
        raise NotImplementedError


#------- Demod Implemetation --------------------

    @abstractmethod
    def set_demod_enable(self,module):
        """Enables the specified module to allow for data collection
        
        @param int module: module of the LIA
        """
        raise NotImplementedError

    @abstractmethod
    def set_demod_disable(self,module):
        """Disables the specified module
        
        @param int module: module of the LIA
        """
        raise NotImplementedError

    @abstractmethod
    def set_demod_bandwidth(self,module,bw):
        """Set the bandwidth of the low-pass filter
        
        The bandwidth is converted into a time constant which depends on the
        order of the low-pass filter

        @param int module: module of the LIA
        @param float bw: bandwidth of the filter
        """
        raise NotImplementedError

    @abstractmethod
    def set_demod_harmonic(self,module,harmonic):
        """Set the harmonic of the base modulation freqeuncy used. "1" is the 
        fundamental frequency
        
        @param int module: module of LIA
        @param int harmonic: harmonic order
        """
        raise NotImplementedError

    @abstractmethod
    def set_demod_order(self,module,order=4):
        """Set the order of the low pass filter
                
        @param int module: module of the LIA
        @param int order: Order of the filter
        """
        raise NotImplementedError
    
    @abstractmethod
    def set_demod_oscillator(self,module,osc):
        """Set the index of the oscillator in use to demodulate

        @param int module: module of LIA
        @param int osc: index of oscillator; valid inputs: 0 or 1
        """
        raise NotImplementedError
    
    @abstractmethod
    def set_demod_phase(self,module,phase):
        """Set the phaseshift of the specified module
        
        @param int module: module of the LIA
        @param float phase: phase shift in deg
        """
        raise NotImplementedError
    
    @abstractmethod
    def set_demod_rate(self,module,rate):
        """Set the data rate of the specified module
        
        Note: The actual data rate might differ slightly
        @param int module: module of the LIA
        @param float rate: data rate in Samples/s --> (Hz)
        """
        raise NotImplementedError
    
    @abstractmethod
    def set_demod_sinc(self,module,status):
        """Enables and Disables the Sinc filter function for the specified 
        module
        
        @param int module: module of the LIA
        @param bool status: Enables/Disables the Sinc filter
        """
        raise NotImplementedError
    
    @abstractmethod
    def set_demod_trigger(self,module,bit=0):
        """Set the trigger channel of the module
        
        @param int module: module of the LIA
        @param int bit: bit decoded trigger channel
        """
        raise NotImplementedError

#------- Signal Output Implemetation ------------

    @abstractmethod
    def set_sigout_enable(self,channel):
        """Enables the output of the specified output channel
        
        @param int channel: output channel of the LIA
        """
        raise NotImplementedError

    @abstractmethod
    def set_sigout_disable(self,channel):
        """Disables the output of the specified output channel
        
        @param int channel: output channel of the LIA
        """
        raise NotImplementedError
    
    @abstractmethod
    def set_sigout_add(self,channel,status):
        """"Enables and disables if an external input is added to the signal
        
        @param int channel: output channel of the LIA
        @param bool status: enable/disable the adding of a signal
        """
        raise NotImplementedError

    @abstractmethod
    def set_sigout_amplitudeEnable(self,channel,status):
        """Enables or disables the amplitude mixer for the specified channel
        
        Note: Each channel has access to all mixers, however only the appropriate 
        one will effect the channel, i.e. device[0].enable() returns 
        {'/dev1492/sigouts/0/enables/6': 0, '/dev1492/sigouts/0/enables/7': 0}
        For savety measures all mixers should be switched simultaniously

        @param int channel: output channel of the LIA
        @param bool status: enable/disable the amplitude mixer
        """
        raise NotImplementedError

    @abstractmethod
    def set_sigout_offset(self,channel,offset):
        """Set the offset added to the specified signal output. 
        The offset is transmitted as a gain value: offset/range
        
        @param int channel: output channel of the LIA
        @param float offset: Offset in V
        """
        raise NotImplementedError
    
    @abstractmethod
    def set_sigout_range(self,channel,range):
        """Set the range of the specified signal output.
        
        Note: In the documentary the range is set as int, however it is
        still possible to set the values of 0.01V and 0.1V correctly.

        @param int channel: output channel of the LIA
        @param float range: output range of the signal in V
        """

#------- Signal Input Implementation --------

    @abstractmethod
    def set_sigin_ac(self,channel,status):
        """Enables and disables the AC coupling of the specified signal input 
        channel

        @param int channel: input channel of the LIA
        @param bool status: enable/disable the AC coupling
        """
        raise NotImplementedError

    @abstractmethod
    def set_sigin_diff(self,channel,status):
        """Enables and disables the Differential Input mode of the specified
        signal input channel
        
        @param int channel: input channel of the LIA
        @param bool status: enables/disables the AC coupling
        """
        raise NotImplementedError
    
    @abstractmethod
    def set_sigin_impedance(self,channel,status):
        """Enables and disables the 50 Ohm impedance termination of the 
        specified signal input channel
        
        @param int channel: input channel of the LIA
        @param bool status: Switches bettwen High impedance ("0") and 50 Ohm 
        impedance ("1")
        """
        raise NotImplementedError
    
    @abstractmethod
    def set_sigin_range(self,channel,range):
        """Set the voltage range of the specified signal input channel
        
        @param int channel: input channel of the LIA
        @param float range: voltage range in V
        """
        raise NotImplementedError
    
#---------- PLL Implementation ---------------

    @abstractmethod
    def set_pll_adcselect(self,channel,inputChannel):
        """Set the input channel for the specified PLL channel

        @param int channel: PLL channel of the LIA
        @param int inputChannel: Input channel number
        """
        raise NotImplementedError
    
    @abstractmethod
    def set_pll_enable(self,channel,status):
        """Enables and disables the specified PLL channel. 
         In reality this refers to the used reference oscillator mode. An 
         enabled PLL uses the external reference (ExtRef), a disabled PLL the 
         manual set internal reference (Man)
         
         @param int channel: PLL channel of the LIA
         @param bool status: enables/disables the PLL
         """
        raise NotImplementedError
























class LockinConstraints:
    """A container to hold all constraints for lockin sources.
    """
    def __init__(self, demodsNum, oscNum, trigger_states, output_ranges, 
                 pll_adcChannels, input_range):
        """
        @param int demodsNum: Number of available Demdulator channels
        @param int oscNum: Number of available Oscillator channels
        @param dict trigger_states: Dictionary containing all available options
        for the demodulator trigger state
        @param list output_ranges: Possible Ranges for the output signal to set
        """
        self._demodsNum = demodsNum
        self._oscNum = oscNum
        self._trigger_states = trigger_states
        self._output_ranges = output_ranges
        self._pll_adcChannels = pll_adcChannels
        self._input_range = input_range


    @property
    def demodsNum(self):
        return self._demodsNum
    
    @property
    def oscNum(self):
        return self._oscNum
    
    @property
    def trigger_states(self):
        return self._trigger_states