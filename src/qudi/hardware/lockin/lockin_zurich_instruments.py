"""
This file contains the Qudi hardware file to control the Zurich Instruments LockIn device.

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

from zhinst.toolkit import Session
from zhinst.utils import bw2tc, bwtc_scaling_factor
import time
import numpy as np

from qudi.util.mutex import Mutex
from qudi.core.configoption import ConfigOption
from qudi.interface.lockin_interface import LockinInterface, LockinConstraints
from qudi.util.enums import SamplingOutputMode


class LockinZurichInstrumentsHF2(LockinInterface):
    """ This is the Interface class to define the controls for the HF2LI
        NOTE: The LIA supports a myriade of options only some necessary for continous magnetic detection are implemented yet

    Example config for copy-paste:

    mw_source_smiq:
        module.Class: 'lockin.lockin_zurich_instruments.LockinZurichInstrumentsHF2'
        options:
            address: 'localhost # optional
            device_name: 'DEVxxxx'
    """
    _address = ConfigOption('address',default='localhost')
    _device_name = ConfigOption('device_name',missing='error')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._thread_lock = Mutex()
        self._session = None
        self._device = None



    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        # Note: HF2 needs it own session apart from other ZHinst devices
        # TODO: Check how multiple simultaneous sessions behave; as it seems sessions cannot be closed?
        self._session = Session(self._address,8005,hf2=True)
        self._device = self._session.connect_device(self._device_name)

        # TODO: Find out constraints
        self._demodsNum = len(self._device.demods()/12)-1 # find out maximum of demod channels; TODO: Better way
        self._oscillatorNum = 1 # highest availabel oscillator number
        self._constraints = LockinConstraints()

    def on_deactivate(self):
        """ Cleanup performed during deactivation of the module. """
        self._session.disconnect_device(self._device_name)
        time.sleep(1) # safety margin, as the command immediatly returns but the device may not be as fast

        self._device = None
        
# ---------------------- Outputs ------------------------------------------
    @property
    def constraints(self):
        """The LIA constraints object for this device.

        @return LockInConstraints:
        """
        return self._constraints
    
    @property
    def demod_status(self):
        """The full status of every demod module.
        """
        pass

    @property
    def sigouts_status(self):
        pass

    
    def get_demod_order(self,module):
        return self._device.demods[module].order()
    
    def get_demod_bandwidth(self,module):
        """The bandwidth of the low-pass filter for the specified module. 
        Must implement setter as well.

        The bandwidth is returned as time constant and converted seperatly to a 
        frequency. For details see: 
        https://docs.zhinst.com/mfli_user_manual/signal_processing_basics.html
        
        @param int module: module of the LIA
        @return double bandwidth: Current bandwidth of the module in Hz
        """
        tc = self._device.demods[module].timeconstant()
        order = self.get_demod_order(module)
        scaling_factor = bwtc_scaling_factor(order)
        return scaling_factor/(np.pi*tc)

    def get_sigout_range(self,channel):
        """The range of the specified output channel
        Must implement setter as well.

        NOTE: The range is returned as int, which means a range of "0.01 V" and "0.1 V" is a "0"!!!
        
        @param int channel: channel of the LIA
        @return int range: range of the output in V
        """
        range = self._device.sigouts[channel].range()
        if range == 0:
            Warning('Range set to "0.1" or "0.01". Cannot differentiate. Set arbitrary to 0.1V')
            range = 0.1
        return range

# -------------------- Inputs --------------------------------------

# ------ Demod -------------
    def set_demod_enable(self,module):
        """Enable the specified module to allow for data collection
        
        Must return AFTER the output is actually active.
        @param int module: module of the LIA
        """
        with self._thread_lock:
            self._device.demods[module].enable(1) 

    def set_demod_disable(self,module):
        """Disable the specified module

        @param int module: module of the LIA
        """
        with self._thread_lock:
            self._device.demods[module].enable(0)

    def set_demod_bandwidth(self,module,bw):
        """Set the bandwidth of the low-pass filter
        
        The bandwidth is converted into a time constant which depends on the
        order of the low-pass filter

        @param int module: module of the LIA
        @param double bw: bandwidth of the filter
        """
        with self._thread_lock:
            order = self.get_demod_order(module)
            tc = bw2tc(bw,order)
            self._device.demods[module].timeconstant(tc)

    def set_demod_harmonic(self,module,harmonic):
        """Set the harmonic of the base modulation freqeuncy used. "1" is the 
        fundamental frequency
        
        @param int module: module of LIA
        @param int harmonic: harmonic order
        """
        with self._thread_lock:
            self._device.demods[module].harmonic[harmonic]

    def set_demod_order(self,module,order=4):
        """Set the order of the low pass filter
        1 --> 6 dB/oct slope
        2 --> 12 dB/oct slope
        3 --> 18 dB/oct slope
        4 --> 24 dB/oct slope (default)
        5 --> 30 dB/oct slope
        6 --> 36 dB/oct slope
        7 --> 42 dB/oct slope
        8 --> 48 dB/oct slope
        
        @param int module: module of the LIA
        @param int order: Order of the filter
        """
        with self._thread_lock:
            self._device.demods[module].order(order)

    def set_demod_oscillator(self,module,osc):
        """Set the index of the oscillator in use to demodulate

        @param int module: module of LIA
        @param int osc: index of oscillator; valid inputs: 0 or 1
        """
        with self._thread_lock:
            self._device.demods[module].oscselect(osc)

    def set_demod_phase(self,module,phase):
        """Set the phaseshift of the specified module
        
        @param int module: module of the LIA
        @param double phase: phase shift in deg
        """
        with self._thread_lock:
            self._device.demods[module].phaseshift(phase)

    def set_demod_rate(self,module,rate):
        """Set the data rate of the specified module
        
        Note: The actual data rate might differ slightly
        @param int module: module of the LIA
        @param double rate: data rate in Samples/s --> (Hz)
        """
        with self._thread_lock:
            self._device.demods[module].rate(rate)

    def set_demod_sinc(self,module,status):
        """Enables and Disables the Sinc filter function for the specified 
        module
        
        @param int module: module of the LIA
        @param bool status: Enables/Disables the Sinc filter
        """
        with self._thread_lock:
            self._device.demods[module].sinc(status)

    def set_demod_trigger(self,module,bit=0):
        """Set the trigger channel of the module
        
        The setting is bit decoded as follows:

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
        @param int bit: bit decoded trigger channel
        """
        with self._thread_lock:
            self._device.demods[module].trigger(bit)
    
# ------ Sig Output --------

    def set_sigout_enable(self,channel):
        """Enables the output of the specified output channel
        
        @param int channel: output channel of the LIA
        """
        with self._thread_lock:
            self._device.sigouts[channel].on(1)

    def set_sigout_disable(self,channel):
        """Disables the output of the specified output channel
        
        @param int channel: output channel of the LIA
        """
        with self._thread_lock:
            self._device.sigouts[channel].on(0)

    def set_sigout_add(self,channel,status):
        """"Enables and disables if an external output is added to the signal
        
        @param int channel: output channel of the LIA
        @param bool status: enable/disable the adding of a signal
        """
        with self._thread_lock:
            self._device.sigouts[channel].add(status)

    def set_sigout_amplitudeEnable(self,channel,status):
        """Enables or disables the amplitude mixer for the specified channel
        
        NOTE: Each channel has access to all mixers, however only the appropriate 
        one will effect the channel, i.e. device[0].enable() returns 
        {'/dev1492/sigouts/0/enables/6': 0, '/dev1492/sigouts/0/enables/7': 0}
        For savety measures all mixers will be switched simultaniously

        @param int channel: output channel of the LIA
        @param bool status: enable/disable the amplitude mixer
        """
        with self._thread_lock:
            self._device.sigouts[channel].enable(status)

    def set_sigout_offset(self,channel,offset):
        """Set the offset added to the specified signal output. 
        The offset is transmitted as a gain value: offset/range
        
        @param int channel: output channel of the LIA
        @param double offset: Offset in V
        """
        with self._thread_lock:
            current_range = self.get_sigout_range(channel) 
            offset_val = offset/current_range
            self._device.sigouts[channel].offset(offset_val)

    def set_sigout_range(self,channel,range):
        """Set the range of the specified signal output.
        
        Technical note: In the documentary the range is set as int however it is
        still possible to set a value of 0.01V and 0.1V.

        @param int channel: output channel of the LIA
        @param double range: output range of the signal in V
        """
        with self._thread_lock:
            self._device.sigouts[channel].range(range)


# ------ Sig Input ---------
    
    def set_sigin_ac(self,channel,status):
        """Enables and disables the AC coupling of the specified signal input 
        channel

        @param int channel: input channel of the LIA
        @param bool status: enable/disable the AC coupling
        """
        with self._thread_lock:
            self._device.sigins[channel].ac(status)

    def set_sigin_diff(self,channel,status):
        """Enables and disables the Differential Input mode of the specified
        signal input channel
        
        @param int channel: input channel of the LIA
        @param bool status: enables/disables the AC coupling
        """
        with self._thread_lock:
            self._device.sigins[channel].diff(status)

    def set_sigin_impedance(self,channel,status):
        """Enables and disables the 50 Ohm impedance termination of the 
        specified signal input channel
        
        @param int channel: input channel of the LIA
        @param bool status: Switches bettwen High impedance ("0") and 50 Ohm 
        impedance ("1")
        """
        with self._thread_lock:
            self._device.sigins[channel].imp50(status)

    def set_sigin_range(self,channel,range):
        """Set the voltage range of the specified signal input channel
        
        @param int channel: input channel of the LIA
        @param double range: voltage range in V
        """
        with self._thread_lock:
            self._device.sigins[channel].range(range)

# ------ PLLs --------------
    def set_pll_adcselect(self,channel,inputChannel):
        """Set the input channel for the specified PLL channel
        
        0 --> Signal Input 1
        1 --> Signal Input 2
        2 --> Aux Input 1
        3 --> Aux Input 2
        4 --> DIO 0
        5 --> DIO 1

        @param int channel: PLL channel of the LIA
        @param int inputChannel: Input channel number
        """
        with self._thread_lock:
            self._device.plls[channel].adcselect(inputChannel)

    def set_pll_enable(self,channel,status):
        """Enables and disables the specified PLL channel.
         In reality this refers if to the used reference oscillator mode. An 
         enabled PLL uses the external reference (ExtRef), a disabled PLL the 
         manual set internal reference (Man)
         
         @param int channel: PLL channel of the LIA
         @param bool status: enables/disables the PLL
         """
        with self._thread_lock:
            self._device.plls[channel].enable(status)