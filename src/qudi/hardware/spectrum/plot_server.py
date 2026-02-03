# plot_server.py
# Realtime data plotting server using PyQt5 and Matplotlib
# Supports multiple channels, scrolling, and data saving to CSV.
# Used to visualize data received via a multiprocessing queue from Data Acquisition processes.

import multiprocessing
from collections import deque
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QSlider, QWidget, QVBoxLayout, QPushButton, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import sys
import csv
import os

class RealtimePlotWindow(QMainWindow):
    def __init__(self, input_queue, num_channels=4, buffer_len=1000, window_len=300):
        super().__init__()
        self.setWindowTitle("Realtime Data Plotter")
        self.input_queue = input_queue
        self.num_channels = num_channels
        self.buffer_len = buffer_len
        self.window_len = window_len
        self.scroll_position = 1.0  # 1->automatic scroll to end

        self.channel_names = ['qwTotalMem', 'qwToTransfer', 'lAvailUser', 'IPCPos']
        self.data = [deque(maxlen=buffer_len) for _ in range(num_channels)]

        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        self.figure = Figure(figsize=(10, 10))  # wider figure
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.axes = self.figure.subplots(self.num_channels, 1, sharex=True)
        self.lines = []

        # save button
        self.save_button = QPushButton("save date as .CSV")
        self.save_button.clicked.connect(self.save_data)
        layout.addWidget(self.save_button)

        for i in range(self.num_channels):
            ax = self.axes[i]
            line, = ax.plot([], [], label=self.channel_names[i])
            ax.set_ylim(0, 10)
            ax.set_xlim(0, self.buffer_len)  # show full buffer initially
            ax.set_title(self.channel_names[i])
            ax.grid(True)
            self.lines.append(line)

        self.resize(1400, 800)  # bigger window as default

        # add slider for scrolling
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(100)
        self.slider.valueChanged.connect(self.on_slider_change)
        layout.addWidget(self.slider)

    def on_slider_change(self, val):
        self.scroll_position = val / 100.0

    def update_plot(self):
        while not self.input_queue.empty():
            data_point = self.input_queue.get()
            for i in range(self.num_channels):
                self.data[i].append(data_point[i])

        max_index = len(self.data[0])
        for i in range(self.num_channels):
            y = list(self.data[i])
            x = list(range(len(y)))

            if max_index < self.window_len:
                start = 0
                end = self.window_len
            else:
                if self.scroll_position >= 0.99:
                    start = max_index - self.window_len
                else:
                    start = int((max_index - self.window_len) * self.scroll_position)
                end = start + self.window_len

            x_segment = x[start:end]
            y_segment = y[start:end]

            self.lines[i].set_data(x_segment, y_segment)
            self.axes[i].set_xlim(start, end)

            # ✅ auto scale y-axis
            if y_segment:
                ymin = min(y_segment)
                ymax = max(y_segment)
                margin = (ymax - ymin) * 0.1 if ymax != ymin else 1
                self.axes[i].set_ylim(ymin - margin, ymax + margin)

        self.canvas.draw()

    def save_data(self):
        # auto open save dialog
        path, _ = QFileDialog.getSaveFileName(self, "Save Data", "data.csv", "CSV Files (*.csv)")
        if not path:
            return

        # organize data for CSV: each row is a sample point (multi-channel)
        length = min(len(ch) for ch in self.data)
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            # write header
            writer.writerow(self.channel_names)
            # write data rows
            for i in range(length):
                row = [self.data[ch][i] for ch in range(self.num_channels)]
                writer.writerow(row)

        print(f"[+] Save data under path: {os.path.abspath(path)}")




class RealtimePlotProcess(multiprocessing.Process):
    def __init__(self, input_queue, num_channels=4, buffer_len=1000, window_len=300):
        super().__init__()
        self.input_queue = input_queue
        self.num_channels = num_channels
        self.buffer_len = buffer_len
        self.window_len = window_len

    def run(self):
        app = QApplication(sys.argv)
        win = RealtimePlotWindow(
            input_queue=self.input_queue,
            num_channels=self.num_channels,
            buffer_len=self.buffer_len,
            window_len=self.window_len,
        )
        win.show()
        sys.exit(app.exec_())
