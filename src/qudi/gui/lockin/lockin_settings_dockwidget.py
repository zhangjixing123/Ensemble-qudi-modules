__all__ = ('LockinSettingsDockWidget')

import numpy as np
from PySide2 import QtCore, QtWidgets, QtGui

from qudi.util.widgets.advanced_dockwidget import AdvancedDockWidget
from qudi.util.widgets.scientific_spinbox import ScienDSpinBox


class LockinSettingsDockWidget(AdvancedDockWidget):
    """

    """
    sigRangeChanged = QtCore.Signal(float)
    sigACChanged = QtCore.Signal(int)
    sigTerminationChanged = QtCore.Signal(int)
    sigDiffChanged = QtCore.Signal(int)
    sigDemodHarmonicChanged = QtCore.Signal(int)
    sigDemodBWChanged = QtCore.Signal(float)
    sigDemodOrderChanged = QtCore.Signal(int)
    sigDemodPhaseChanged = QtCore.Signal(float)
    sigDemodRateChanged = QtCore.Signal(int)
    sigDemodSincChanged = QtCore.Signal(int)
    sigDemodEnableChanged = QtCore.Signal(int)
    sigDemodTriggerChanged = QtCore.Signal(int)
    sigOutONChanged = QtCore.Signal() 
    sigOutAddChanged = QtCore.Signal()
    sigOutOffsetChanged = QtCore.Signal(float)
    sigOutAmpChanged = QtCore.Signal(float)
    sigOutAmpEnabledChanged = QtCore.Signal(int)
    sigOutRangeChanged = QtCore.Signal(float)
    sigPllEnableChanged = QtCore.Signal(int)
    sigPllOscChanged = QtCore.Signal(int)

    # TODO: set all input arguments
    def __init__(self, *args, range_limits=None, oscsNum=None, demodsNum=None, 
                 trigger_states=None, output_ranges=None, adc_channels=None, 
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Lockin Settings')
        self.setFeatures(self.DockWidgetFloatable | self.DockWidgetMovable)

        # Lookup table for the selected states to determine return argument later
        self._trigger_states = trigger_states
        self._output_ranges = output_ranges
        self._adc_channels = adc_channels

        # Minimal Spinbox width for a standard long input
        self._min_spinbox_width = QtGui.QFontMetrics(ScienDSpinBox().font()).width(
            ' -000.000 GHz '
        )

        # create central widget and layout

        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)

        # create singal input group box

        group_box = QtWidgets.QGroupBox('Signal Input')
        layout = QtWidgets.QVBoxLayout()
        group_box.setLayout(layout)

        # TODO: Set correct values
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setStretch(2, 1)
        h_layout.setStretch(3, 1)

        label = QtWidgets.QLabel('Range:')
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        h_layout.addWidget(label)
        self.range_spinbox = ScienDSpinBox()
        self.range_spinbox.setMinimumWidth(self._min_spinbox_width)
        self.range_spinbox.setDecimals(6)
        self.range_spinbox.setSuffix('V')
        self.range_spinbox.valueChanged.connect(self._range_cb)
        self.range_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                         QtWidgets.QSizePolicy.Fixed)
        if range_limits is not None:
            self.range_spinbox.setRange(*range_limits)
        h_layout.addWidget(self.range_spinbox)
        layout.addLayout(h_layout)
        
        # TODO: Match to first h_layout
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setStretch(2, 1)
        h_layout.setStretch(3, 1)

        label_ac = QtWidgets.QLabel('AC:')
        label_ac.setAlignment(QtCore.Qt.AlignCenter)
        label_ac.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.ac_checkbox = QtWidgets.QCheckBox()

        label_termination = QtWidgets.QLabel('50 Ohm:')
        label_termination.setAlignment(QtCore.Qt.AlignCenter)
        label_termination.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.termination_checkbox = QtWidgets.QCheckBox()
        
        label_diff = QtWidgets.QLabel('Diff:')
        label_diff.setAlignment(QtCore.Qt.AlignCenter)
        label_diff.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.diff_checkbox = QtWidgets.QCheckBox()
        
        self.ac_checkbox.stateChanged.connect(self.sigACChanged)
        self.termination_checkbox.stateChanged.connect(self.sigTerminationChanged)
        self.diff_checkbox.stateChanged.connect(self.sigDiffChanged)
        h_layout.addWidget(label_ac)
        h_layout.addWidget(self.ac_checkbox)
        h_layout.addWidget(label_termination)
        h_layout.addWidget(self.termination_checkbox)
        h_layout.addWidget(label_diff)
        h_layout.addWidget(self.diff_checkbox)
        layout.addLayout(h_layout)

        main_layout.addWidget(group_box)

        
        # TODO: 
        # create oscillator group box
        # group_box = QtWidgets.QGroupBox('Oscillator')
        # layout = QtWidgets.QVBoxLayout()
        # group_box.setLayout(layout)

        # create demodulator group box

        group_box = QtWidgets.QGroupBox('Demodulator')
        layout = QtWidgets.QHBoxLayout()
        group_box.setLayout(layout)
        
        self._demod_layout = QtWidgets.QGridLayout()
        self._demod_layout.setContentsMargins(0, 0, 0, 0)

        label = QtWidgets.QLabel('Signal 1')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._demod_layout.addWidget(label, 1, 0)
        
        label = QtWidgets.QLabel('Osc')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._demod_layout.addWidget(label, 0, 1)
        self.oscNum_combobox = QtWidgets.QComboBox()
        self.oscNum_combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        if oscsNum is not None:
            for n in range(oscsNum):
                self.oscNum_combobox.addItem(f'{n}')
        self.oscNum_combobox.currentIndexChanged.connect(self._osc_selection_cb)
        self._demod_layout.addWidget(self.oscNum_combobox, 1, 1)
        
        label = QtWidgets.QLabel('Harmonic')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._demod_layout.addWidget(label, 0, 2)
        self.harmonic_spinbox = QtWidgets.QSpinBox()
        self.harmonic_spinbox.setMinimumWidth(self._min_spinbox_width)
        self.harmonic_spinbox.valueChanged.connect(self._harmonic_cb)
        self.harmonic_spinbox.setValue(4)
        self._demod_layout.addWidget(self.harmonic_spinbox, 1, 2)
        
        label = QtWidgets.QLabel('Demod Freq')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._demod_layout.addWidget(label, 0, 3)
        # self.demod_frequency = QtWidgets.QTextBrowser() #TODO figure out how that works
        # self._demod_layout.addLayout(self.demod_frequency, 1, 3)
        
        label = QtWidgets.QLabel('Phase')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._demod_layout.addWidget(label, 0, 4)
        self.phase_spinbox = QtWidgets.QSpinBox()
        self.phase_spinbox.setMinimumWidth(self._min_spinbox_width)
        self.phase_spinbox.valueChanged.connect(self._phase_cb)
        self._demod_layout.addWidget(self.phase_spinbox, 1, 4)
        
        label = QtWidgets.QLabel('Filter BW')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._demod_layout.addWidget(label, 0, 5)
        self.bandwidth_spinbox = ScienDSpinBox()
        self.bandwidth_spinbox.setMinimumWidth(self._min_spinbox_width)
        self.bandwidth_spinbox.setSuffix('Hz')
        self.bandwidth_spinbox.valueChanged.connect(self._bandwidth_cb)
        self._demod_layout.addWidget(self.bandwidth_spinbox, 1, 5)
        
        label = QtWidgets.QLabel('Filter Order')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._demod_layout.addWidget(label, 0, 6)
        self.order_spinbox = QtWidgets.QSpinBox()
        self.order_spinbox.setMinimumWidth(self._min_spinbox_width)
        self.order_spinbox.valueChanged.connect(self._order_cb)
        self._demod_layout.addWidget(self.order_spinbox, 1, 6)

        label = QtWidgets.QLabel('Sinc')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._demod_layout.addWidget(label, 0, 6)
        self.sinc_checkbox = QtWidgets.QCheckBox()
        self.sinc_checkbox.stateChanged.connect(self.sigDemodSincChanged)
        self._demod_layout.addWidget(self.sinc_checkbox)
        
        self.enable_checkbox = QtWidgets.QCheckBox()
        self.enable_checkbox.stateChanged.connect(self.sigDemodEnableChanged)
        self._demod_layout.addWidget(self.enable_checkbox, 1, 7)       
        label = QtWidgets.QLabel('Sample Rate')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._demod_layout.addWidget(label, 0, 8)
        self.rate_spinbox = ScienDSpinBox()
        self.rate_spinbox.setMinimumWidth(self._min_spinbox_width)
        self.rate_spinbox.valueChanged.connect(self._rate_cb)
        self._demod_layout.addWidget(self.rate_spinbox, 1, 8)
        layout.addLayout(self._demod_layout)
        layout.addStretch(1)
        
        label = QtWidgets.QLabel('Trigger')
        label.setAlignment(QtCore.Qt.AlignCenter)
        self._demod_layout.addWidget(label, 0, 9)
        self.trigger_combobox = QtWidgets.QComboBox()
        if trigger_states is not None:
            #self.trigger_combobox.addItems(f'{list(trigger_states.values())}')
            for name in list(trigger_states.values()):
                self.trigger_combobox.addItem(f'{name}')
        self.trigger_combobox.currentIndexChanged.connect(self._trigger_cb)
        self._demod_layout.addWidget(self.trigger_combobox)

        main_layout.addWidget(group_box)

        # create signal output group box
        group_box = QtWidgets.QGroupBox('Signal Output')
        layout = QtWidgets.QVBoxLayout()
        group_box.setLayout(layout)

        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setStretch(2, 1)
        h_layout.setStretch(3, 1)
        self.outputON_checkbox = QtWidgets.QCheckBox('ON')
        self.outputON_checkbox.stateChanged.connect(self.sigOutONChanged)
        self.outputAdd_checkbox = QtWidgets.QCheckBox('Add')
        self.outputAdd_checkbox.stateChanged.connect(self.sigOutAddChanged)
        h_layout.addWidget(self.outputON_checkbox)
        h_layout.addWidget(self.outputAdd_checkbox)
        layout.addLayout(h_layout)

        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setStretch(2, 1)
        h_layout.setStretch(3, 1)
        label = QtWidgets.QLabel('Range [V]')
        self.outputRange_combobox = QtWidgets.QComboBox()
        self.outputRange_combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        if output_ranges is not None:
            self.outputRange_combobox.addItems(output_ranges)
        self.outputRange_combobox.currentIndexChanged.connect(self._outputRange_cb)
        h_layout.addWidget(label)
        h_layout.addWidget(self.outputRange_combobox)
        layout.addLayout(h_layout)

        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setStretch(2, 1)
        h_layout.setStretch(3, 1)
        label = QtWidgets.QLabel('Offset')
        self.outputOffset_spinbox = ScienDSpinBox()
        self.outputOffset_spinbox.setSuffix('V')
        self.outputOffset_spinbox.valueChanged.connect(self._outputOffset_cb)
        h_layout.addWidget(label)
        h_layout.addWidget(self.outputOffset_spinbox)
        layout.addLayout(h_layout)

        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setStretch(2, 1)
        h_layout.setStretch(3, 1)
        label = QtWidgets.QLabel('Amplitude')
        self.outputAmp_spinbox = ScienDSpinBox()
        self.outputAmp_spinbox.setSuffix('Vpk')
        self.outputAmp_spinbox.valueChanged.connect(self._outputAmp_cb)
        h_layout.addWidget(label)
        h_layout.addWidget(self.outputAmp_spinbox)
        self.outputAmpEnable_checkbox = QtWidgets.QCheckBox('Amp Enable')
        self.outputAmpEnable_checkbox.stateChanged.connect(self.sigOutAmpEnabledChanged)
        h_layout.addWidget(self.outputAmpEnable_checkbox)
        layout.addLayout(h_layout)

        main_layout.addWidget(group_box)

        # PLLs

        group_box = QtWidgets.QGroupBox('PLLs')
        layout = QtWidgets.QVBoxLayout()
        group_box.setLayout(layout)

        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setStretch(2, 1)
        h_layout.setStretch(3, 1)
        
        self.pllEnable_checkbox = QtWidgets.QCheckBox('Pll Enable')
        self.pllEnable_checkbox.stateChanged.connect(self.sigPllEnableChanged)
        h_layout.addWidget(self.outputAmpEnable_checkbox)
        self.pllAdc_combobox = QtWidgets.QComboBox()
        self.pllAdc_combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        if adc_channels is not None:
            self.pllAdc_combobox.addItems(f'{list(adc_channels.values())}')
        self.pllAdc_combobox.currentIndexChanged.connect(self._pllAdc_cb)


        

        

    @property
    def selected_osc(self):
        return self.oscNum_combobox.currentText()
    
    @property
    def selected_trigger(self):
        trigger_name = self.trigger_combobox.currentText()
        return list(self._trigger_states.keys())[list(self._trigger_states.values()).index(trigger_name)]
    
    @property
    def selected_range(self):
        return self.outputRange_combobox.currentText()
    
    @property
    def selected_adc(self):
        adc_name = self.pllAdc_combobox.currentText()
        return self._adc_channels.keys()[self._adc_channels.values().index(adc_name)]

    @QtCore.Slot()
    def _range_cb(self):
        self.sigRangeChanged.emit(self.range_spinbox.value())
    
    @QtCore.Slot()
    def _harmonic_cb(self):
        self.sigDemodHarmonicChanged.emit(self.harmonic_spinbox.value())

    @QtCore.Slot()
    def _bandwidth_cb(self):
        self.sigDemodBWChanged.emit(self.bandwidth_spinbox.value())

    @QtCore.Slot()
    def _order_cb(self):
        self.sigDemodOrderChanged.emit(self.order_spinbox.value())

    @QtCore.Slot()
    def _rate_cb(self):
        self.sigDemodRateChanged.emit(self.rate_spinbox.value())

    @QtCore.Slot()
    def _trigger_cb(self):
        self.sigDemodTriggerChanged.emit(self.selected_trigger)

    @QtCore.Slot()
    def _outputOffset_cb(self):
        self.sigOutOffsetChanged.emit(self.outputOffset_spinbox.value())

    @QtCore.Slot()
    def _outputAmp_cb(self):
        self.sigOutAmpChanged.emit(self.outputAmp_spinbox.value())

    @QtCore.Slot()
    def _osc_selection_cb(self):
        self.sigPLLOscChanged.emit(self.selected_osc)

    @QtCore.Slot()
    def _phase_cb(self):
        self.sigDemodPhaseChanged.emit(self.phase_spinbox.value())

    @QtCore.Slot()
    def _outputRange_cb(self):
        self.sigOutRangeChanged.emit(self.selected_range)

    @QtCore.Slot()
    def _pllAdc_cb(self):
        self.sigPllOscChanged.emit(self.selected_adc)


    #TODO: FIll that up:
    def parameters_set_enabled(self, enable):
        self.range_spinbox.setEnabled(enable)
        self.ac_checkbox.setEnabled(enable)
        self.termination_checkbox.setEnabled(enable)
        self.diff_checkbox.setEnabled(enable)
        self.harmonic_spinbox.setEnabled(enable)
        self.bandwidth_spinbox.setEnabled(enable)
        self.order_spinbox.setEnabled(enable)
        self.rate_spinbox.setEnabled(enable)
        self.outputON_checkbox.setEnabled(enable)
        self.outputAdd_checkbox.setEnabled(enable)
        self.outputAmp_spinbox.setEnabled(enable)