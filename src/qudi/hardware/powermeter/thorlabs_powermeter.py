# -*- coding: utf-8 -*-

"""
This file contains the qudi hardware module to use a Thorlabs power meter as a process value device.
It uses the TLPM library, which supersedes the PM100D driver. It is installed
together with the Optical Power Monitor software.

Compatible devices according to Thorlabs:
- PM100A, PM100D, PM100USB
- PM101 Series, PM102 Series, PM103 Series
- PM16 Series, PM160, PM160T, PM160T-HP
- PM200, PM400
"""

import platform
from ctypes import byref, c_bool, c_char_p, cdll, c_double, c_int, c_int16, c_long, create_string_buffer, c_uint32

from qudi.core.configoption import ConfigOption
from qudi.interface.process_control_interface import ProcessValueInterface, ProcessControlConstraints

# constants
SET_VALUE = c_int16(0)
MIN_VALUE = c_int16(1)
MAX_VALUE = c_int16(2)


class ThorlabsPowermeter(ProcessValueInterface):
    """ Hardware module for Thorlabs powermeter using the TLPM library.

    Example config:

    powermeter:
        module.Class: 'thorlabs_powermeter.ThorlabsPowermeter'
        options:
            address: 'USB0::0x1313::0x8078::P0012345::INSTR'
            wavelength: 637.0
    """

    _address = ConfigOption('address', missing='error')
    _wavelength = ConfigOption('wavelength', default=None, missing='warn')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._channel_name = 'Power'
        self._constraints = None
        self._is_active = False

        self.dll = None
        self.devSession = c_long()
        self.devSession.value = 0

    def _test_for_error(self, status):
        if status < 0:
            msg = create_string_buffer(1024)
            self.dll.TLPM_errorMessage(self.devSession, c_int(status), msg)
            self.log.error(c_char_p(msg.raw).value)
            return True
        return False

    def on_activate(self):
        """ Startup the module """
        # load the dll
        try:
            if platform.architecture()[0] == '32bit':
                self.dll = cdll.LoadLibrary('C:/Program Files (x86)/IVI Foundation/VISA/WinNT/Bin/TLPM_32.dll')
            else:
                self.dll = cdll.LoadLibrary('C:/Program Files/IVI Foundation/VISA/Win64/Bin/TLPM_64.dll')
        except FileNotFoundError as e:
            self.log.error('TLPM DLL not found. Is the Thorlabs Optical Power Monitor software installed?')
            raise e

        # get list of available power meters
        device_count = c_uint32()
        result = self.dll.TLPM_findRsrc(self.devSession, byref(device_count))
        self._test_for_error(result)

        available_power_meters = []
        resource_name = create_string_buffer(1024)

        for i in range(0, device_count.value):
            result = self.dll.TLPM_getRsrcName(self.devSession, c_int(i), resource_name)
            self._test_for_error(result)
            available_power_meters.append(c_char_p(resource_name.raw).value)

        self.log.info(f'Available power meters: {available_power_meters}')

        # try to connect to power meter
        address = create_string_buffer(self._address.encode('utf-8'))
        if address.value in available_power_meters:
            id_query, reset_device = c_bool(True), c_bool(True)
            result = self.dll.TLPM_init(address, id_query, reset_device, byref(self.devSession))
            if self._test_for_error(result):
                self.log.error('Connection to powermeter was unsuccessful. Try using the Power Meter Driver '
                               + 'Switcher application to switch your powermeter to the TLPM driver.')
                raise ValueError
        else:
            raise ValueError(f'No powermeter with address {self._address} found.')

        # set wavelength if defined in config
        if self._wavelength is not None:
            self._set_wavelength(self._wavelength)

        # get power range
        min_power, max_power = c_double(), c_double()
        result = self.dll.TLPM_getPowerRange(self.devSession, MIN_VALUE, byref(min_power))
        self._test_for_error(result)
        result = self.dll.TLPM_getPowerRange(self.devSession, MAX_VALUE, byref(max_power))
        self._test_for_error(result)

        # set constraints
        self._constraints = ProcessControlConstraints(
            process_channels=(self._channel_name,),
            units={self._channel_name: 'W'},
            limits={self._channel_name: (min_power.value, max_power.value)},
            dtypes={self._channel_name: float},
        )

    def on_deactivate(self):
        """ Stops the module """
        result = self.dll.TLPM_close(self.devSession)
        self._test_for_error(result)

    @property
    def process_values(self):
        """ Read-Only property returning a snapshot of current process values for all channels.

        @return dict: Snapshot of the current process values (values) for all channels (keys)
        """
        value = self.get_process_value(self._channel_name)
        return {self._channel_name: value}

    @property
    def constraints(self):
        """ Read-Only property holding the constraints for this hardware module.
        See class ProcessControlConstraints for more details.

        @return ProcessControlConstraints: Hardware constraints
        """
        return self._constraints

    def set_activity_state(self, channel, active):
        """ Set activity state. State is bool type and refers to active (True) and inactive (False).
        """
        if channel != self._channel_name:
            raise AssertionError(f'Invalid channel name. Only valid channel is: {self._channel_name}')
        if active != self._is_active:
            self._is_active = active

    def get_activity_state(self, channel):
        """ Get activity state for given channel.
        State is bool type and refers to active (True) and inactive (False).
        """
        if channel != self._channel_name:
            raise AssertionError(f'Invalid channel name. Only valid channel is: {self._channel_name}')
        return self._is_active

    @property
    def activity_states(self):
        """ Current activity state (values) for each channel (keys).
        State is bool type and refers to active (True) and inactive (False).
        """
        return {self._channel_name: self._is_active}

    @activity_states.setter
    def activity_states(self, values):
        """ Set activity state (values) for multiple channels (keys).
        State is bool type and refers to active (True) and inactive (False).
        """
        for ch, enabled in values.items():
            if ch != self._channel_name:
                raise AssertionError(f'Invalid channel name. Only valid channel is: {self._channel_name}')
            self.set_activity_state(ch, enabled)

    def get_process_value(self, channel):
        """ Return a measured value """
        if channel != self._channel_name:
            raise AssertionError(f'Invalid channel name. Only valid channel is: {self._channel_name}')
        return self._get_power()

    def _get_power(self):
        """ Return the power reading from the power meter """
        power = c_double()
        result = self.dll.TLPM_measPower(self.devSession, byref(power))
        self._test_for_error(result)
        return power.value

    def _get_wavelength(self):
        """ Return the current measurement wavelength in nanometers """
        wavelength = c_double()
        result = self.dll.TLPM_getWavelength(self.devSession, SET_VALUE, byref(wavelength))
        self._test_for_error(result)
        return wavelength.value

    def _get_wavelength_range(self):
        """ Return the measurement wavelength range of the power meter in nanometers """
        wavelength_min = c_double()
        wavelength_max = c_double()
        result = self.dll.TLPM_getWavelength(self.devSession, MIN_VALUE, byref(wavelength_min))
        self._test_for_error(result)
        result = self.dll.TLPM_getWavelength(self.devSession, MAX_VALUE, byref(wavelength_max))
        self._test_for_error(result)

        return wavelength_min.value, wavelength_max.value

    def _set_wavelength(self, value):
        """ Set the new measurement wavelength in nanometers """
        min_wl, max_wl = self._get_wavelength_range()
        if min_wl <= value <= max_wl:
            result = self.dll.TLPM_setWavelength(self.devSession, c_double(value))
            self._test_for_error(result)
        else:
            self.log.error(f'Wavelength {value} nm is out of the range {min_wl} to {max_wl} nm.')
