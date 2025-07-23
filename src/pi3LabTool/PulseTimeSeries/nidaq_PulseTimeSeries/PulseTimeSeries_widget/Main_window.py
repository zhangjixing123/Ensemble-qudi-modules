#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
realtime_scope.py
PyQt5 + Matplotlib 
  · 左侧 13 个参数（含新加 x_time_window、display mode）
  · 右侧波形可设定窗口宽度，支持 “原始/平均” 两种显示
  · 底部滚动条可回看历史
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QSplitter, QVBoxLayout,
    QMessageBox
)
from PyQt5.QtGui import QFont


from PulseTimeSeries_widget.Param_widget import ParamPanel
from PulseTimeSeries_widget.Waveform_widget import WaveformPanel

# ───────────────────────────────────────
# 主窗口
# ───────────────────────────────────────
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Magnetic Scope")
        self.resize(1080, 590)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        splitter = QSplitter(Qt.Horizontal, self)
        self.panel_left  = ParamPanel()
        self.panel_right = WaveformPanel()
        splitter.addWidget(self.panel_left)
        splitter.addWidget(self.panel_right)
        splitter.setStretchFactor(1, 1)
        layout = QVBoxLayout(self); layout.addWidget(splitter)

    def _connect_signals(self):
        self.panel_left.btn_submit.clicked.connect(self.on_submit)
        self.panel_right.btn_start.clicked.connect(self.on_start)
        self.panel_right.btn_pause.clicked.connect(self.panel_right.pause)
        self.panel_right.btn_stop .clicked.connect(self.on_stop)

    def on_submit(self):
        self.params = self.panel_left.values()
        if (self.params["ignore first"] + self.params["ignore last"] >= self.params["frame_size"]):
            msgbox = QMessageBox(self)
            msgbox.setWindowTitle("Params error")
            msgbox.setText("The number of ignored data is greater than or equal to the frame size !")
            msgbox.setIcon(QMessageBox.Warning)
            msgbox.setStandardButtons(QMessageBox.Ok)
            # 设置字体大小
            font = QFont()
            font.setPointSize(12)  # 可根据需要调整大小
            msgbox.setFont(font)
            msgbox.exec_()

        else:
            msgbox = QMessageBox(self)
            msgbox.setWindowTitle("Params Submitted")
            msgbox.setText("Parameters have been saved, you can click Start.")
            msgbox.setIcon(QMessageBox.Information)
            msgbox.setStandardButtons(QMessageBox.Ok)
            # 设置字体大小
            font = QFont()
            font.setPointSize(12)  # 根据需要调整字体大小
            msgbox.setFont(font)
            msgbox.exec_()

    def on_start(self):
        if not hasattr(self, "params"):

            msgbox = QMessageBox(self)
            msgbox.setWindowTitle("No Params")
            msgbox.setText("Please submit parameters first.")
            msgbox.setIcon(QMessageBox.Warning)
            msgbox.setStandardButtons(QMessageBox.Ok)
            # 设置字体大小
            font = QFont()
            font.setPointSize(12)  # 可根据需要调整大小
            msgbox.setFont(font)
            msgbox.exec_()
            return
        
        self.panel_left.set_editable(False)
        self.panel_right.start(self.params)

    def on_stop(self):
        self.panel_right.stop()
        self.panel_left.set_editable(True)