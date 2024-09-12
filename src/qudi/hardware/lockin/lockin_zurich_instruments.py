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
import time
import numpy as np

from qudi.util.mutex import Mutex
from qudi.core.configoption import ConfigOption
from qudi.interface.lockin_interface import LockinInterface, LockinConstraints
from qudi.util.enums import SamplingOutputMode


class LockinZurichInstrumentsHF2(LockinInterface):
    """ This is the Interface class to define the controls for the HF2LI

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

    def on_deactivate(self):
        """ Cleanup performed during deactivation of the module. """
        self._session.disconnect_device(self._device_name)
        time.sleep(1) # safety margin, as the command immediatly returns but the device may not be as fast

        self._device = None
        
        