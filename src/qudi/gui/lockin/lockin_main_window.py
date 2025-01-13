__all__ = ('LockinMainWindow',)


import os

import pyqtgraph as pg
from PySide2 import QtCore, QtWidgets, QtGui

from qudi.util.widgets.scientific_spinbox import ScienDSpinBox
from qudi.util.paths import get_artwork_dir

from qudi.gui.lockin.lockin_settings_dockwidget import LockinSettingsDockWidget


class LockinMainWindow(QtWidgets.QMainWindow):
    """The main window for the Lockin implementation
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('qudi: LockIn')
        self.setDockNestingEnabled(True)

        # Create QActions
        icon_path = os.path.join(get_artwork_dir(),'icons')

        icon = QtGui.QIcon(os.path.join(icon_path,'start-counter'))
        icon.addFile(os.path.join(icon_path, 'stop-counter'),
                     state=QtGui.QIcon.On)
        self.action_toggle_measurement = QtWidgets.QAction('Toggle Measurement')
        self.action_toggle_measurement.setCheckable(True)
        self.action_toggle_measurement.setIcon(icon)
        self.action_toggle_measurement.setToolTip('Start/Stop Lockin measurement')

        icon = QtGui.QIcon(os.path.join(icon_path, 'restart-counter'))
        self.action_resume_measurement = QtWidgets.QAction('Resume Measurement')
        self.action_resume_measurement.setIcon(icon)
        self.action_resume_measurement.setToolTip('Resume Lockin measurement')

        icon = QtGui.QIcon(os.path.join(icon_path, 'record-counter'))
        icon.addFile(os.path.join(icon_path, 'stop-record-counter'), state=QtGui.QIcon.On)
        self.action_record_trace = QtWidgets.QAction(icon, 'Start recording', self)
        self.action_record_trace.setCheckable(True)
        self.action_record_trace.setToolTip(
            'Start/Stop trace recorder. This will continuously accumulate trace data and save it '
            'to file once it is stopped.'
        )

        icon = QtGui.QIcon(os.path.join(icon_path, 'camera-photo'))
        self.action_snapshot_trace = QtWidgets.QAction(icon, 'Take snapshot', self)
        self.action_snapshot_trace.setCheckable(False)
        self.action_snapshot_trace.setToolTip(
            'Take a snapshot of only the currently shown data trace and save it to file.'
        )

        icon = QtGui.QIcon(os.path.join(icon_path, 'application-exit'))
        self.action_close = QtWidgets.QAction('Close')
        self.action_close.setIcon(icon)

        self.action_show_controls = QtWidgets.QAction('Measurement Controls')
        self.action_show_controls.setCheckable(True)
        self.action_show_controls.setChecked(True)
        self.action_show_controls.setToolTip('Show/Hide controls')

        self.action_restore_default_view = QtWidgets.QAction('Restore default', self)
        self.action_restore_default_view.setCheckable(False)
        self.action_restore_default_view.setToolTip('Restore the default view.')


        self.action_show_lockin_settings = QtWidgets.QAction('Lockin settings', self)
        self.action_show_lockin_settings.setCheckable(True)
        self.action_show_lockin_settings.setToolTip('Show settings of the Lockin')

        icon = QtGui.QIcon(os.path.join(icon_path, 'application-exit'))
        self.close_action = QtWidgets.QAction(icon, 'Close', self)
        self.close_action.setCheckable(False)
        self.close_action.setToolTip('Close')
        
        # Create measurement toolbar

        self.toolbar = QtWidgets.QToolBar('Measurement Controls')
        self.toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.toolbar.addAction(self.action_toggle_measurement)
        self.toolbar.addAction(self.action_resume_measurement)
        self.toolbar.addAction(self.action_record_trace)
        self.toolbar.addAction(self.action_snapshot_trace)
        
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.toolbar)
        
        # Create menubar

        menubar = QtWidgets.QMenuBar()
        menu = menubar.addMenu('File')
        menu.addAction(self.action_toggle_measurement)
        menu.addAction(self.action_resume_measurement)
        menu.addAction(self.action_record_trace)
        menu.addAction(self.action_snapshot_trace)
        menu.addSeparator()
        menu.addAction(self.close_action)
        menu = menubar.addMenu('View')
        menu.addAction(self.action_show_controls)
        menu.addSeparator()
        menu.addAction(self.action_restore_default_view)

        self.setMenuBar(menubar)
        
        # Create plot widget

        self.trace_plot_widget = pg.PlotWidget()
        self.current_value_label = QtWidgets.QLabel('0')
        font = self.current_value_label.font()
        font.setBold(True)
        font.setPointSize(60)
        self.current_value_label.setFont(font)
        self.current_value_label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)


        # Create and populate layout

        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QGridLayout()
        
        main_layout.setColumnStretch(0, 1)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        self.settings_dockwidget = LockinSettingsDockWidget()
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.settings_dockwidget)

        main_layout.addWidget(self.current_value_label, 1, 0, 1, 2)
        main_layout.addWidget(self.trace_plot_widget, 2, 0, 1,2)

        # Connect show/hide signals
        self.action_show_controls.triggered[bool].connect(self.toolbar.setVisible)
        self.toolbar.visibilityChanged.connect(self.action_show_controls.setChecked)
        self.action_show_lockin_settings.triggered[bool].connect(self.settings_dockwidget.setVisible)
        self.settings_dockwidget.visibilityChanged.connect(self.action_show_lockin_settings.setChecked)
        self.close_action.triggered.connect(self.close)