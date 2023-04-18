import sys

# pylint: disable=no-name-in-module, broad-except
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow

from ..backend.copier import Copier
from ..backend.folder_parser import FolderParser
from ..backend.internet_parser import InternetParser
from ..utils.files_IO import read_json_file, write_json_file
from ..utils.logger import get_logger
from .main_window import Ui_MainWindow

_logger = get_logger(__file__)

class MainWindow(Ui_MainWindow, QMainWindow):
    signal_cancel = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.folder_dialog = QFileDialog(caption="Выберите папку", directory="/")
        self.folder_dialog.setFileMode(QFileDialog.FileMode.Directory)
        self.folder_dialog.setOption(QFileDialog.Option.ShowDirsOnly)

        self.processButton.clicked.connect(self.parse)

        self.cancelButton.clicked.connect(self.signal_cancel.emit)
        @pyqtSlot()
        def cancel():
            self.internet_parser.signal_cancel.emit()
            self.internet_parser_thread.quit()
            self.folder_parser.signal_cancel.emit()
            self.folder_parser_thread.quit()
            self.copier.signal_cancel.emit()
            self.copier_thread.quit()
            self.reset()
        self.signal_cancel.connect(cancel)

        self.startFolderButton.clicked.connect(lambda: self.startFolderLineEdit.setText(self.folder_dialog.getExistingDirectory()))
        self.endFolderButton.clicked.connect(lambda: self.endFolderLineEdit.setText(self.folder_dialog.getExistingDirectory()))

        self.internet_parser_thread = QThread()
        self.internet_parser = InternetParser()

        def setup_internet_parser():
            self.internet_parser.moveToThread(self.internet_parser_thread)
            self.internet_parser_thread.started.connect(self.internet_parser.run)

            @pyqtSlot(int)
            def initialized(tracks_amount):
                self.lastfmProgressBar.setValue(0)
                self.lastfmProgressBar.setMaximum(tracks_amount)
            self.internet_parser.signal_initialized.connect(initialized)

            @pyqtSlot(set)
            def finished(tracks):
                self.loved_tracks = tracks
                self.internet_parser_thread.quit()

                if self.local_tracks:
                    self.copy()
            self.internet_parser.signal_finished.connect(finished)

            @pyqtSlot(int)
            def processed(tracks_processed):
                self.lastfmProgressBar.setValue(tracks_processed)
            self.internet_parser.signal_track_processed.connect(processed)

        setup_internet_parser()

        self.folder_parser_thread = QThread()
        self.folder_parser = FolderParser()

        def setup_folder_parser():
            self.folder_parser.moveToThread(self.folder_parser_thread)
            self.folder_parser_thread.started.connect(self.folder_parser.run)

            @pyqtSlot(int)
            def initialized(tracks_amount):
                self.startFolderProgressBar.setValue(0)
                self.startFolderProgressBar.setMaximum(tracks_amount)
            self.folder_parser.signal_initialized.connect(initialized)

            @pyqtSlot(set)
            def finished(tracks):
                self.local_tracks = tracks
                self.folder_parser_thread.quit()
                self.outputField.insertPlainText(f"Всего найдено музыкальных файлов в папке: {len(self.local_tracks)}\n")

                if self.loved_tracks:
                    self.copy()
            self.folder_parser.signal_finished.connect(finished)

            @pyqtSlot(int)
            def processed(tracks_amount):
                self.startFolderProgressBar.setValue(tracks_amount)
            self.folder_parser.signal_track_processed.connect(processed)

        setup_folder_parser()

        self.copier_thread = QThread()
        self.copier = Copier()

        def setup_copier():
            self.copier.moveToThread(self.copier_thread)
            self.copier_thread.started.connect(self.copier.run)

            @pyqtSlot(set)
            def finished(problems):
                self.problems = sorted(problems, key=lambda x: (x.artist, x.title))
                self.copier_thread.quit()

                if problems:
                    self.outputField.insertPlainText(f"Возникли проблемы со следующими треками ({len(self.problems)}шт.):\n")
                    self.outputField.insertPlainText("\n".join(f"{problem.artist} - {problem.title}" for problem in self.problems))

                self.processButton.setEnabled(True)
            self.copier.signal_finished.connect(finished)

            @pyqtSlot(int)
            def processed(tracks_amount):
                self.endFolderProgressBar.setValue(tracks_amount)
            self.copier.signal_track_processed.connect(processed)

        setup_copier()

        self.username = ""
        self.start_folder = ""
        self.loved_tracks = set()
        self.local_tracks = set()
        self.problems = set()

        last_settings = read_json_file("./last_settings.json")
        self.usernameLineEdit.setText(last_settings["username"])
        self.startFolderLineEdit.setText(last_settings["start_folder"])
        self.endFolderLineEdit.setText(last_settings["end_folder"])
        self.copyOptionComboBox.setCurrentIndex(last_settings["copy_mode"])

    def reset(self):
        self.username = ""
        self.start_folder = ""

        self.outputField.setText("")
        self.processButton.setEnabled(True)

        self.lastfmProgressBar.setValue(0)
        self.lastfmProgressBar.setMaximum(100)

        self.startFolderProgressBar.setValue(0)
        self.startFolderProgressBar.setMaximum(100)

        self.endFolderProgressBar.setValue(0)
        self.endFolderProgressBar.setMaximum(100)

    def internet_parse(self):
        self.username = self.usernameLineEdit.text()

        self.internet_parser.username = self.username

        self.internet_parser_thread.start()

    def start_folder_parse(self):
        self.start_folder = self.startFolderLineEdit.text()

        self.folder_parser.root_folder = self.start_folder

        self.folder_parser_thread.start()

    def copy(self):
        folder = self.endFolderLineEdit.text()

        self.copier.loved_tracks = self.loved_tracks
        self.copier.local_tracks = self.local_tracks
        self.copier.final_folder = folder
        if self.copyOptionComboBox.currentIndex() == 1:
            self.copier.symlinks = False

        self.endFolderProgressBar.setValue(0)
        self.endFolderProgressBar.setMaximum(len(self.loved_tracks))

        self.copier_thread.start()

    def parse(self):
        self.processButton.setEnabled(False)
        self.outputField.setText("")
        write_json_file(
            {
                "username": self.usernameLineEdit.text(),
                "start_folder": self.startFolderLineEdit.text(),
                "end_folder": self.endFolderLineEdit.text(),
                "copy_mode": self.copyOptionComboBox.currentIndex()
            },
            "./last_settings.json"
        )
        if self.username != self.usernameLineEdit.text():
            self.internet_parse()
        if self.start_folder != self.startFolderLineEdit.text():
            self.start_folder_parse()


def create_main_window():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()


def main():
    try:
        create_main_window()
    except Exception as error:
        _logger.critical("Exception %s", error)
