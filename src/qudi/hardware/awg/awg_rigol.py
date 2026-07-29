# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control Rigol AWG devices.

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

try:
    import pyvisa as visa
except ImportError:
    import visa

import numpy as np

from qudi.util.mutex import Mutex
from qudi.core.configoption import ConfigOption
#TODO: Proper interface needs to be implemented
from qudi.interface.awg_interface import AWGInterface, AWGConstraints

class AWGRigol(AWGInterface):
    """This is the Interface class to define the controls for the simple
        AWG hardware. Under construction and only a crude implementation of essential commands.

    Example config for copy-paste:
    
    
    """

    _visa_address = ConfigOption('visa_address', missing='error')
    _comm_timeout = ConfigOption('comm_timeout', default=10, missing='warn')
    _visa_baud_rate = ConfigOption('visa_baud_rate', default=None)
    

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = Mutex()
        self._rm = None
        self._device = None
        self._model = ''
        self._constraints = None
        

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        # Connect to hardware
        self._rm = visa.ResourceManager()
        if self._visa_baud_rate is None:
            self._device = self._rm.open_resource(self._visa_address,
                                                  timeout=self._comm_timeout)
        else:
            self._device = self._rm.open_resource(self._visa_address,
                                                  timeout=self._comm_timeout,
                                                  baud_rate=self._visa_baud_rate)

        self._model = self._device.query('*IDN?').split(',')[1]
        # Reset device
        self._command_wait('*CLS')
        self._command_wait('*RST')

        # Generate constraints
        #TODO: Look up proper model names
        if self._model == 'DG1022':

        elif self._model == 'DG5072':

        elif self._model == 'DG1032z':

        else:

            self.log.warning('Model string unknown, hardware limits may be wrong.')

        