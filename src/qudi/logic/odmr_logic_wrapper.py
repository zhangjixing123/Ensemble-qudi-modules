# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module for ODMR control.

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

from PySide2 import QtCore

from qudi.logic.odmr_logic import OdmrLogic
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption
from qudi.util.enums import SamplingOutputMode

class OdmrLogicWrapper(OdmrLogic):
    """
    This is a wrapper for the Logic class for CW ODMR measurements. It introduces
    a connector to a pulse blaster (or other timing device) for a more convenient 
    switch between CW and pulsed ones measurements.

    example config for copy-paste:

    odmr_logic:
        module.Class: 'odmr_logic.OdmrLogic'
        connect:
            microwave: <microwave_name>
            data_scanner: <data_scanner_name>
            timing_generator: <timing_generator_name>
        options:
            active_channels: [0]
            default_scan_mode: 'JUMP_LIST'  # optional
            save_thumbnails: False

    """
    # declare connectors
    #_microwave = Connector(name='microwave', interface='MicrowaveInterface')
    #_data_scanner = Connector(name='data_scanner', interface='FiniteSamplingInputInterface')
    _timing_generator = Connector(name='timing_generator', interface='PulserInterface')

    # declare config options
    #_save_thumbnails = ConfigOption(name='save_thumbnails', default=True)
    #_default_scan_mode = ConfigOption(name='default_scan_mode',
    #                                  default='JUMP_LIST',
    #                                  constructor=lambda x: SamplingOutputMode[x.upper()])
    _active_channels = ConfigOption(name='active_channels',default=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        self._timing_setup()
        super().on_activate()

    @QtCore.Slot()
    def start_odmr_scan(self):
        # account for the possibility that another programm used the timing 
        # generator inbetween and changed the loaded settings
        self._timing_setup()
        
        self._timing_generator().start()
        super().start_odmr_scan()

    @QtCore.Slot()
    def continue_odmr_scan(self):
        self._timing_generator().start()
        super().continue_odmr_scan()

    @QtCore.Slot()
    def stop_odmr_scan(self):
        self._timing_generator().stop()
        super().stop_odmr_scan()

    def _timing_setup(self):
        self._timing_generator().start_programming()
        sequence_list = [{'active_channels':self._active_channels, 'length':10e-9}]
        self._timing_generator().write_pulse_form(sequence_list,loop=True)
        self._timing_generator().stop_programming()