import sys

# pylint: disable=no-name-in-module
from PyQt6.QtWidgets import QApplication

from src.frontend.pyqt import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()

# TODO: Кнопка отмены
