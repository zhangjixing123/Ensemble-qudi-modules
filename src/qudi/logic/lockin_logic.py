import numpy as np
import time
import datetime as dt
import matplotlib.pyplot as plt
from PySide2 import QtCore
from typing import Union, Optional, Sequence


from qudi.core.module import LogicBase
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.util.mutex import Mutex
from qudi.logic.time_series_reader_logic import TimeSeriesReaderLogic


# TODO: How to handle multi channels and multi modules?
class LockinLogic(TimeSeriesReaderLogic, LogicBase):
    """
    This is the Logic class for the LockIn implementation.

    example config for copy-paste:

    lockin_logic:
        module.Class: 'lockin_logic.LockinLogic'
        connect:
            lockin: <lockin_name>
            
        options:
            
    """

    # declare connector 
    _lockin = Connector(name='lockin',interface='LockinInterface')

    # declare config options 
    # TODO: Are there options to be considered?


    # declare status variables
    # Signal Input Stuff
    _InputAC = StatusVar(name='InputAC', default=0)
    _InputDiff = StatusVar(name='InputDiff', default=0)
    _InputImp = StatusVar(name='InputImp', default=0)
    _InputRange = StatusVar(name='InputRange', default=2)
    # Demod Stuff
    _DemodBW = StatusVar(name='DemodBW', default=6.811)
    _DemodEnable = StatusVar(name='DemodEnable', default=0)
    _DemodHarmonic = StatusVar(name='DemodHarmonic', default=1)
    _DemodOrder = StatusVar(name='DemodOrder', default=4)
    _DemodOsc = StatusVar(name='DemodOsc', default=0)
    _DemodPhase = StatusVar(name='DemodPhase', default=0.0)
    _DemodRate = StatusVar(name='DemodRate', default=1799.0)
    _DemodSinc = StatusVar(name='DemodSinc', default=0)
    _DemodTrigger = StatusVar(name='DemodTrigger', default=0)
    # Signal Output Stuff
    _OutputAdd = StatusVar(name='OutputAdd',default=0)
    _OutputAmpEnable = StatusVar(name='OutputAmpEnable',default=0)
    _OutputAmpOffset = StatusVar(name='OutputAmpOffset',default=0.0)
    _OutputEnable = StatusVar(name='OutputEnable',default=0)
    _OutputRange = StatusVar(name='OutputRange',default=1)
    # Pll Stuff
    _PllEnable = StatusVar(name='PllEnable',default=0)
    _PllAdc = StatusVar(name='PllAdc',default=0)



    # Internal Signals
    # TODO: Find the necessary ones


    # Update signals, e.g for GUI module
    sigParamsUpdated = QtCore.Signal(dict)
    sigDataUpdated = QtCore.Signal()

    # TODO:
    _default_something_configs = (
    )


    #TODO: Set representers and constructors

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)

        self._threadlock = Mutex()
        self._samples_per_frame = None #TODO: What dis doin?

        # data arrays
        self._data_buffer = None
        self._times_buffer = None
        self._trace_data = None
        self._trace_times = None

        # for data recording
        self._recorded_raw_data = None
        self._recorded_raw_times = None
        self._recorded_sample_count = 0
        self._data_recording_active = False
        self._record_start_time = None


    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        lockin_constraints = self._lockin().constraints
        # TODO: recall status variables and check against constraints

        
        # Flag to stop the loop and process variables
        self._recorded_raw_data = None
        self._recorded_raw_times = None
        self._recorded_sample_count = 0
        self._data_recording_active = False
        self._record_start_time = None


        

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module.
        """
        try:
            if self.module_state() == 'locked':
                self._stop()
        finally:
            # Free (potentially) large raw data buffers
            self._data_buffer = None
            self._times_buffer = None




    
    #TODO: Check if all parameters are included; especially trigger_state correctly parsed
    @property
    def setting_parameters(self):
        params = {'InputAC': self._InputAC,
                  'InputDiff': self._InputDiff,
                  'InputImp': self._InputImp,
                  'InputRange': self._InputRange,
                  'DemodBW': self._DemodBW,
                  'DemodEnable': self._DemodEnable,
                  'DemodHarmonic': self._DemodHarmonic,
                  'DemodOrder': self._DemodHarmonic,
                  'DemodOsc': self._DemodOsc,
                  'DemodPhase': self._DemodPhase,
                  'DemodRate': self._DemodRate,
                  'DemodSinc': self._DemodSinc,
                  'DemodTrigger': self._DemodTrigger,
                  'OutputAdd': self._OutputAdd,
                  'OutputAmpEnable': self._OutputAmpEnable,
                  'OutputAmpOffset': self._OutputAmpOffset,
                  'OutputEnable': self._OutputEnable,
                  'OutputRange': self._OutputRange,
                  'PllEnable': self._PllEnable,
                  'PllAdc': self._PllAdc
                  }
        return params
    
    @property
    def lockin_constraints(self):
        return self._lockin().constraints




























    @property
    def InputAC(self):
        return self._InputAC
    
    @QtCore.Slot()
    def set_ACMode(self):
        with self._threadlock:
            self.sigParamsUpdated.emit({'InputAC': self.InputAC})




    

