#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Param_widget.py
PyQt5 + Matplotlib 实时示波器示例
  · 左侧 13 个参数（含新加 x_time_window、display mode）
  · 右侧波形可设定窗口宽度，支持 “原始/平均” 两种显示
  · 底部滚动条可回看历史
"""
from PyQt5.QtWidgets import (
    QWidget, QFormLayout,
    QLineEdit, QPushButton, QSpinBox,
    QDoubleSpinBox, QCheckBox, QComboBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# ───────────────────────────────────────
# 左侧参数面板（13 个字段）
# ───────────────────────────────────────
class ParamPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def values(self):
        return {
            "device_name":  self.ed_device.text(),
            "clk_terminal": self.ed_clk.text(),
            "sample_rate":  self.spin_rate.value(),
            "frame_size":   self.spin_size.value(),
            "frame_num":    self.spin_num.value(),
            "analog_channels": self.ed_ch.text(),
            "adc_voltage_range": self.ed_range.text(),
            "rw_timeout":   self.spin_timeout.value(),
            "external_sample_clock_source": self.ed_extclk.text(),
            "refresh_rate": self.spin_refresh.value(),
            "enable_debug": self.chk_debug.isChecked(),
            "x_time_window": self.spin_window.value(),
            "display_mode":  self.cmb_mode.currentText(),
            "display_mode2":  self.cmb_mode2.currentText(),
            "file_name": self.ed_fname.text(),
            "save_dir":  self.ed_dir.text(),
            "ignore first": self.ignore_first.value(),
            "ignore last": self.ignore_last.value()
        }

    def set_editable(self, editable: bool):
        for w in (
            self.ed_device, self.ed_clk, self.spin_rate, self.spin_size,
            self.spin_num, self.ed_ch, self.ed_range, self.spin_timeout,
            self.ed_extclk, self.spin_refresh, self.chk_debug,
            self.spin_window, self.cmb_mode, self.cmb_mode2,
            self.ed_fname, self.ed_dir, self.ignore_first, self.ignore_last
        ):
            w.setEnabled(editable)
        self.btn_submit.setEnabled(editable)

    def _build_ui(self):
        layout = QFormLayout(self)

        self.ed_device = QLineEdit("Dev3")
        self.ed_clk    = QLineEdit("ctr0")
        self.ed_ch     = QLineEdit("ai5")
        self.ed_range  = QLineEdit("10")
        self.ed_extclk = QLineEdit("PFI9")

        self.spin_rate = QSpinBox(); self.spin_rate.setRange(1, 300_000); self.spin_rate.setValue(100_000)
        self.spin_size = QSpinBox(); self.spin_size.setRange(2, 100_000); self.spin_size.setValue(10)
        self.spin_num  = QSpinBox(); self.spin_num.setRange(1, 10_000); self.spin_num.setValue(3)

        self.spin_timeout = QDoubleSpinBox(); self.spin_timeout.setRange(0.01, 10); self.spin_timeout.setValue(20)
        self.spin_refresh = QSpinBox(); self.spin_refresh.setRange(10, 5000); self.spin_refresh.setValue(500)

        self.spin_window = QDoubleSpinBox(); self.spin_window.setRange(0.5, 1000); self.spin_window.setDecimals(1); self.spin_window.setValue(10.0)

        self.cmb_mode = QComboBox(); self.cmb_mode.addItems(["Display last data", "Display average data"])
        self.cmb_mode2 = QComboBox(); self.cmb_mode2.addItems(["Display original data link", "Display integrated Point"])

        self.ignore_first = QSpinBox(); self.ignore_first.setRange(0, 100_000); self.ignore_first.setValue(0)
        self.ignore_last  = QSpinBox(); self.ignore_last.setRange(0, 100_000); self.ignore_last.setValue(0)

        self.chk_debug = QCheckBox("Enable")

        self.ed_fname = QLineEdit("data.csv")
        self.ed_dir   = QLineEdit("./data/")

        # ---- 排版 ----
        layout.addRow("device_name",  self.ed_device)
        layout.addRow("clk_terminal", self.ed_clk)
        layout.addRow("sample_rate",  self.spin_rate)
        layout.addRow("frame_size",   self.spin_size)
        layout.addRow("frame_num",    self.spin_num)
        layout.addRow("analog_channels", self.ed_ch)
        layout.addRow("adc_voltage_range", self.ed_range)
        layout.addRow("rw_timeout (s)",    self.spin_timeout)
        layout.addRow("external_sample_clock_source", self.ed_extclk)
        layout.addRow("refresh_rate (ms)", self.spin_refresh)

        layout.addRow("x_time_window (s)", self.spin_window)

        layout.addRow("ignore first data", self.ignore_first)
        layout.addRow("ignore last data", self.ignore_last)
        
        layout.addRow("display mode",      self.cmb_mode)
        layout.addRow("display mode 2",      self.cmb_mode2)
        layout.addRow("file_name",         self.ed_fname)  
        layout.addRow("save_dir",          self.ed_dir)    
        layout.addRow("enable_debug",      self.chk_debug)

        self.btn_submit = QPushButton("Submit")
        layout.addRow(self.btn_submit)