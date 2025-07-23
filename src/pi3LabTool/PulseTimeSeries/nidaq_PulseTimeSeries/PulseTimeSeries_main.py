import sys
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication
import qdarktheme

from PulseTimeSeries_widget.Main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Arial", 13))
    qdarktheme.setup_theme("light")
    w = MainWindow(); w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()