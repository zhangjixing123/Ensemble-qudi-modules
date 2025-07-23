#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Waveform_widget.py
PyQt5 + Matplotlib 实时示波器示例
  · 左侧 13 个参数（含新加 x_time_window、display mode）
  · 右侧波形可设定窗口宽度，支持 “原始/平均” 两种显示
  · 底部滚动条可回看历史
"""
import time, random, statistics, csv, os
from collections import deque
import numpy as np

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, 
    QPushButton, QLabel, QHBoxLayout, 
    QScrollBar, QMessageBox
)
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


from ni_x_pulse_time_series import PulseTimeSeries

# ───────────────────────────────────────
# 右侧波形面板
# ───────────────────────────────────────

class WaveformPanel(QWidget):
    Y_LIM = (-6, 6)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._init_state()

    def _init_state(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_plot)

        self.refresh_ms   = 50
        self.window_sec   = 5
        self.display_mode = "display last data"
        self.display_mode2 = "display original data link"
        self.data         = deque()          # (elapsed, value)
        self.start_time   = None
        self.running      = False
        self.paused       = False
        self.follow_tail  = True
        self.enable_debug = False

        # 文件写入
        self.file_path    = None
        self.csv_file     = None
        self.csv_writer   = None

    # ---------- 控制 ----------
    def start(self, params):
        if self.running:
            return
        
        # params of nidaq device
        self.nidaq = PulseTimeSeries()
        self.device_name = params["device_name"]
        self.clk_terminal = params["clk_terminal"]
        self.sample_rate = params["sample_rate"]
        self.frame_size  = params["frame_size"]
        self.frame_num   = params["frame_num"]
        self.analog_channels = params["analog_channels"]
        self.adc_voltage_range = (-abs(int(params["adc_voltage_range"])), abs(int(params["adc_voltage_range"])))
        self.rw_timeout  = params["rw_timeout"]
        self.external_sample_clock_source = params["external_sample_clock_source"]
        # params of GUI
        self.refresh_ms   = params["refresh_rate"]
        self.window_sec   = params["x_time_window"]

        self.ignore_first = params["ignore first"]
        self.ignore_last = params["ignore last"]

        self.display_mode = params["display_mode"]
        self.display_mode2 = params["display_mode2"]
        self.enable_debug = params["enable_debug"]
        # params of update of elapsed time
        self.pause_flag = 0    # not ever paused
        self.pause_point = 0
        self.elapsed = 0

        # start nidaq device
        self.nidaq._device_name = self.device_name
        self.nidaq.clk_terminal = self.clk_terminal
        self.nidaq._sample_rate = self.sample_rate
        self.nidaq._frame_size = self.frame_size
        self.nidaq._frame_num = self.frame_num
        self.nidaq.analog_channels = self.analog_channels
        self.nidaq._adc_voltage_range = self.adc_voltage_range
        self.nidaq._rw_timeout = self.rw_timeout
        self.nidaq.external_sample_clock_source = self.external_sample_clock_source
        self.nidaq._enable_debug = self.enable_debug

        self.nidaq.on_activate()
        self.nidaq.configure(bin_width_s = 1/self.sample_rate, 
                             record_length_s = self.frame_size/self.sample_rate,
                             number_of_gates = self.frame_num)

        # 保存/检查/覆盖文件
        # --- ①-A 拼路径 ---
        save_dir  = os.path.abspath(params["save_dir"])
        os.makedirs(save_dir, exist_ok=True)
        self.file_path = os.path.join(save_dir, params["file_name"])

        # --- ①-B 若文件已存在 → 提示 ---
        if os.path.exists(self.file_path):
            msgbox = QMessageBox(self)
            msgbox.setWindowTitle("File exists")
            msgbox.setText(
                f"『{self.file_path}』 already exists.\n"
                "Do you want to overwrite it?"
            )
            msgbox.setIcon(QMessageBox.Question)
            msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.No)

            # 设置字体大小
            font = QFont()
            font.setPointSize(12)  # 修改这里设置你想要的字体大小
            msgbox.setFont(font)

            ans = msgbox.exec_()
            if ans == QMessageBox.No:
                return  # 用户取消，直接退出 start()

        # --- ①-C 以 **写入模式** 打开文件 ---
        self.csv_file  = open(self.file_path, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["elapsed_time_s", "value"])

        # start nidaq
        self.nidaq.start_measure()

        # start timer
        self.start_time = time.perf_counter()
        self.timer.start(self.refresh_ms)

        # update UI state
        self.running = True
        self.paused  = False
        self.lbl_status.setText("Running")
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop .setEnabled(True)

    def pause(self):
        if not self.running:
            return
        if not self.paused:
            # stop nidaq device
            self.nidaq.pause_measure()
            self.timer.stop()
            self.paused = True
            self.lbl_status.setText("Paused")
            self.btn_pause.setText("Resume")
            self.pause_flag = 1
        else:
            # resume nidaq device
            self.nidaq.start_measure()
            self.timer.start(self.refresh_ms)
            self.paused = False
            self.lbl_status.setText("Running")
            self.btn_pause.setText("Pause")

    def stop(self):
        if not self.running:
            return
        # stop nidaq device
        self.nidaq.stop_measure()
        self.nidaq.on_deactivate()
        self.timer.stop()
        self.data.clear()
        self.line.set_data([], [])
        self.ax.set_xlim(0, self.window_sec)
        self.canvas.draw_idle()

        # 关闭文件
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = self.csv_writer = None

        self.running = self.paused = False
        self.follow_tail = True
        self.scrollbar.setMaximum(0); self.scrollbar.setValue(0)

        self.lbl_status.setText("Stopped")
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("Pause")
        self.btn_stop .setEnabled(False)

    # ---------- 滚动条 ----------
    def _on_scroll(self, value):
        self.follow_tail = (value == self.scrollbar.maximum())
        self._redraw_from_scroll(value)

    def _redraw_from_scroll(self, value):
        if not self.data:
            return
        first_t = self.data[0][0]
        t0 = first_t + value / 1000
        self._draw_window(t0, t0 + self.window_sec)

    # ---------- data update ----------
    def _update_plot(self):
        if self.pause_flag:                              # paused once
            self.start_time = time.perf_counter()
            # update pause point as last step:
            self.pause_point = self.elapsed + self.refresh_ms/1e3  
            self.pause_flag = 0           
            
        now = time.perf_counter()
        self.elapsed = now - self.start_time + self.pause_point

        # 模拟数据 —— #
        # data = np.random.randint(-6, 16, size=(10, 6)) # TODO: 替换为真实采样

        # get data from nidaq ---
        data, info = self.nidaq.get_data_trace(accumulate = True)
        if int(self.ignore_first):
            data = data[:, int(self.ignore_first):]
        if int(self.ignore_last):
            data = data[:, :-int(self.ignore_last)]
        all_data = data[:-1]
        average_data = data[-1]  # last row is the average data, rest of them are original data

        if self.display_mode2 == "Display original data link":

            if self.display_mode == "Display average data":
                display_data = average_data # display average data
            else:
                display_data = all_data[-1] # only last row

        else:

            if self.display_mode == "Display average data":
                display_data = np.array([np.sum(average_data)]) # display average data
            else:
                display_data = np.array([np.sum(all_data[-1])]) # only last row


 
        # 因为返回的是一组数据，赋予其对应的时间戳
        len_display_data = len(display_data)

        if len_display_data == 1:                 # 只收到一个点
            times = [self.elapsed]                # 直接用当前时间戳
        else:                                     # 多个点（批量）
            # 让第一点与最后一点正好跨度 refresh_ms 毫秒
            dt = self.refresh_ms * 1e-3 / (len_display_data - 1)
            times = [self.elapsed - (len_display_data - 1 - i) * dt
                    for i in range(len_display_data)]
        

        # —— 写入 CSV —— #
        if self.csv_writer:
            self.csv_writer.writerow([f"{self.elapsed:.6f}", all_data.tolist()])
            self.csv_file.flush()

        # —— 内存队列 & 调试 —— #
        self.data.extend(zip(times, display_data))
        while self.data and self.elapsed - self.data[0][0] > 1000: # 保持最近 1000 秒的数据
            self.data.popleft()
        # if self.enable_debug:
        #     print(f"{elapsed=:.2f}s, {display_data=:.2f}")

        # —— 滚动条范围 —— #
        first_t = self.data[0][0]
        last_t  = self.data[-1][0]
        total_ms = max(0, int((last_t - first_t - self.window_sec) * 1000))
        self.scrollbar.setMaximum(total_ms)

        if self.follow_tail:
            self._draw_window(last_t - self.window_sec, last_t)
            self.scrollbar.setValue(self.scrollbar.maximum())

    # ---------- 绘制 ----------
    def _draw_window(self, t0, t1):
        if not self.data:
            return
        pts = [(x, y) for (x, y) in self.data if t0 <= x <= t1]
        if not pts:
            return
        xs, ys = zip(*pts)

        # ---- 曲线 or 平均线 ----
        if self.display_mode == "display average data":
            avg = statistics.mean(ys)
            self.line.set_data([t0, t1], [avg, avg])
            ymin = avg; ymax = avg           # 下面一起放到 autoscale
        else:
            self.line.set_data(xs, ys)
            ymin, ymax = min(ys), max(ys)

        # ---- 自动 Y 轴 ----
        if ymin == ymax:                     # 全部相同，给个小余量
            ymin -= 0.5
            ymax += 0.5
        margin = 0.05 * (ymax - ymin)        # 5 % headroom
        self.ax.set_ylim(ymin - margin, ymax + margin)

        # ---- X 轴 & 绘制 ----
        self.ax.set_xlim(t0, t1)
        self.ax.set_xlabel("Elapsed Time (s)")
        self.canvas.draw_idle()

    # ---------- UI ----------
    def _build_ui(self):
        vbox = QVBoxLayout(self); vbox.setContentsMargins(0, 0, 0, 0)
        fig = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(fig)
        self.ax = fig.add_subplot(111)
        self.ax.set_title("Real-Time Waveform")
        self.ax.grid(True)
        self.ax.set_ylim(*self.Y_LIM)
        self.ax.set_xlim(0, 5)
        self.ax.set_xlabel("Elapsed Time (s)")
        # self.line, = self.ax.plot([], [], lw=0.8)
        self.line, = self.ax.plot([], [], 'o-', lw=1.2, markersize=4)
        vbox.addWidget(self.canvas, 1)

        self.scrollbar = QScrollBar(Qt.Horizontal); self.scrollbar.setRange(0, 0)
        self.scrollbar.valueChanged.connect(self._on_scroll)
        vbox.addWidget(self.scrollbar)

        hbox = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_pause = QPushButton("Pause"); self.btn_pause.setEnabled(False)
        self.btn_stop  = QPushButton("Stop");  self.btn_stop .setEnabled(False)
        self.lbl_status = QLabel("Stopped"); self.lbl_status.setAlignment(Qt.AlignCenter)

        hbox.addWidget(self.btn_start); hbox.addWidget(self.btn_pause)
        hbox.addWidget(self.btn_stop);  hbox.addWidget(self.lbl_status, 1)
        vbox.addLayout(hbox)
    
