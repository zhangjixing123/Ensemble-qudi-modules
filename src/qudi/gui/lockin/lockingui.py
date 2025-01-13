import numpy as np
from PySide2 import QtCore, QtWidgets

from qudi.core.connector import Connector
from qudi.core.module import GuiBase

from src.qudi.gui.lockin.lockin_main_window import LockinMainWindow
from src.qudi.gui.lockin.lockin_settings_dockwidget import LockinSettingsDockWidget

class LockinGui(GuiBase):
    """
    This is the GUI Class for the Lockin implementation.

    example config for copy-paste:

    lockin_gui:
        module.Class: 'lockin.lockgui.LockinGui'
        connect:
            lockin_logic: 'lockin_logic'
    """
    # declare connectors
    _lockin_logic = Connector(name='lockin_logic',interface='LockinLogic')

    # declare Config Options

    # TODO:
    # declare staus variables
    sigToggleMeas = QtCore.Signal(bool, bool)
    sigSaveData = QtCore.Signal(str)
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._lockin = None
        self._plot_widget = None
        self._settings_dockwidget = None


    def on_activate(self):
        # Create main window 
        logic = self._lockin_logic()
        data_constraints = logic.data_constraints # TODO: Needed?
        lockin_constraints = logic.lockin_constraints
        self._mw = LockinMainWindow()
        self._plot_widget = self._mw.centralWidget()

        self._settings_dockwidget = LockinSettingsDockWidget(
            parent = self._mw,
            range_limits = lockin_constraints._input_range,
            oscsNum = lockin_constraints._oscNum,
            demodsNum = lockin_constraints._demodsNum,
            trigger_states= lockin_constraints._trigger_states,
            adc_channels= lockin_constraints._pll_adcChannels,
            output_ranges= lockin_constraints._output_ranges,
        )
        #TODO: Refine ConfigOptions? i.e. add multichannels here?

        # Initialize widget contents
        self._update_parameters()
        self._update_measurement_state()
        #TODO: Check if everything is connected in the end
        # Connect signals
        self.__connect_main_window_actions()
        self.__connect_logic_signals()
        
    def on_deactivate(self):
        # Disconnect signals
        self.__disconnect_main_window_actions()
        self.__disconnect_logic_signals()

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def __connect_main_window_actions(self):
        logic = self._lockin_logic()
        self._mw.action_toggle_measurement.triggered[bool].connect(self.run_stop_measurement)
        self._mw.action_resume_measurement.triggered.connect(self.resume_measurement)
        self._mw.action_snapshot_trace.triggered.connect(logic.save_trace_snapshot,
                                                         QtCore.Qt.QueuedConnection)
        self._mw.action_restore_default_view.triggered.connect(self.restore_default_view)

    def __connect_lockin_settings_signals(self): #TODO: Whats wrong here?
        logic = self._lockin_logic()
        self._settings_dockwidget.sigACChanged.connect(logic.set_)

    def __disconnect_main_window_actions(self): 
        self._mw.action_toggle_measurement.triggered[bool].disconnect()
        self._mw.action_resume_measurement.triggered.disconnect()
        self._mw.action_snapshot_trace.triggered.disconnect()
        self._mw.action_restore_default_view.triggered.disconnect()

    def __disconnect_logic_signals(self):
        logic = self._lockin_logic()
        logic.sigParamsUpdated.disconnect()

      
    def _update_parameters(self,param_dict=None):
        """Update the lockin parameters in the GUI

        @param param_dict:
        @return:

        Any change event from the logic should call this update function.
        The update will block the GUI signals from emitting a change back to the
        logic."""
        if param_dict is None:
            logic = self._lockin_logic()
            param_dict = logic.setting_parameters
        
        ######### Input Settings ##############
        param = param_dict.get('InputAC')
        if param is not None:
            self._settings_dockwidget.ac_checkbox.setChecked(param)
        
        param = param_dict.get('InputDiff')
        if param is not None:
            self._settings_dockwidget.diff_checkbox.setChecked(param)
        
        param = param_dict.get('InputImp')
        if param is not None:
            self._settings_dockwidget.termination_checkbox.setChecked(param)
        
        param = param_dict.get('InputRange')
        if param is not None:
            self._settings_dockwidget.range_spinbox.setValue(param)

        ######### Demod Settings ##############
        param = param_dict.get('DemodBW')
        if param is not None:
            self._settings_dockwidget.bandwidth_spinbox.setValue(param)
        
        param = param_dict.get('DemodEnable')
        if param is not None:
            self._settings_dockwidget.enable_checkbox.setChecked(param) 

        param = param_dict.get('DemodHarmonic')
        if param is not None:
            self._settings_dockwidget.harmonic_spinbox.setValue(param) 
        
        param = param_dict.get('DemodOrder')
        if param is not None:
            self._settings_dockwidget.order_spinbox.setValue(param) 

        param = param_dict.get('DemodOsc')
        if param is not None:
            self._settings_dockwidget.oscNum_combobox.setCurrentIndex(param) 

        param = param_dict.get('DemodPhase')
        if param is not None:
            self._settings_dockwidget.phase_spinbox.setValue(param) 
        
        param = param_dict.get('DemodRate')
        if param is not None:
            self._settings_dockwidget.rate_spinbox.setValue(param)

        param = param_dict.get('DemodSinc')
        if param is not None:
            self._settings_dockwidget.sinc_checkbox.setChecked(param)

        param = param_dict.get('DemodTrigger')
        if param is not None:
            self._settings_dockwidget.trigger_combobox.setCurrentIndex(param)
        
        ######### Output Settings #############

        param = param_dict.get('OutputAdd')
        if param is not None:
            self._settings_dockwidget.outputAdd_checkbox.setChecked(param)

        param = param_dict.get('OutputAmpEnable')
        if param is not None:
            self._settings_dockwidget.outputON_checkbox.setChecked(param)

        param = param_dict.get('OutputAmpOffset')
        if param is not None:
            self._settings_dockwidget.outputAmp_spinbox.setValue(param)

        param = param_dict.get('OutputEnable')
        if param is not None:
            self._settings_dockwidget.outputAmpEnable_checkbox.setChecked(param)

        param = param_dict.get('OutputRange')
        if param is not None:
            self._settings_dockwidget.outputRange_combobox.setCurrentIndex(param)
        
        ######### PLL Settings ################

        param = param_dict.get('PllEnable')
        if param is not None:
            self._settings_dockwidget.pllEnable_checkbox.setChecked(param)
        
        param = param_dict.get('PllAdc')
        if param is not None:
            self._settings_dockwidget.pllAdc_combobox.setCurrentIndex(param)
        

        

    def _update_measurement_state(self,running=None):
        """ Update the display for a change in the lockin status.

        @param bool running:
        """
        if running is None:
            running = self._lockin_logic().module_state() != 'idle'
        # set control state
        self._mw.action_toggle_measurement.setEnabled(True)
        self._mw.action_resume_measurement.setEnabled(not running)
        self._mw.action_snapshot_trace.setEnabled(True)
        self._settings_dockwidget.parameters_set_enabled(not running)

    @QtCore.Slot(bool)
    def run_stop_measurement(self, is_checked):
        """ Manages what happends if the lockin measurement is started/stopped"""
        # Disables controls unitl logic feedback is activating them again
        self._mw.action_toggle_measurement.setEnabled(False)
        self._mw.action_resume_measurement.setEnabled(False)
        # Notify liguc
        self.sigToggleMeas.emit(is_checked, False) # start meas, resume flag

    @QtCore.Slot()
    def resume_measurement(self):
        # Disables controls until logic feedback is activating them again
        self._mw.action_toggle_measurement.setEnabled(False)
        self._mw.action_resume_measurement.setEnabled(False)
        # Notify liguc
        self.sigToggleMeas.emit(True, False) # start meas, resume flag

    @QtCore.Slot()
    def restore_default_view(self):
        self._settings_dockwidget.setFloating(False)
        self._mw.action_show_controls.setChecked(True)
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._settings_dockwidget)