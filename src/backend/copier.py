import os
import shutil
from pathlib import Path

import Levenshtein
# pylint: disable=no-name-in-module, no-member
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from .track_data import InternetTrackData, LocalTrackData


class Copier(QObject):
    signal_initialized = pyqtSignal()
    signal_finished = pyqtSignal(set)
    signal_track_processed = pyqtSignal(int)
    signal_cancel = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.loved_tracks: set[InternetTrackData] = set()
        self.local_tracks: set[LocalTrackData] = set()
        self.symlinks: bool = True

        self._is_running = True
        @pyqtSlot()
        def cancel():
            self._is_running = False
        self.signal_cancel.connect(cancel)
        self._final_folder = ""
        self._processed_amount = 0
        self._problems = set()

    @property
    def final_folder(self):
        return self._final_folder

    @final_folder.setter
    def final_folder(self, value: str | Path):
        self._final_folder = value if isinstance(value, Path) else Path(value)

    def initialize(self):
        self._is_running = True
        self._processed_amount = 0
        self._problems = set()

        os.makedirs(self.final_folder, exist_ok=True)
        self.signal_initialized.emit()

    def process(self):
        for loved_track in self.loved_tracks:
            for local_track in self.local_tracks:
                if not self._is_running:
                    return
                if (
                    Levenshtein.ratio(loved_track.artist.lower(), local_track.artist.lower()) >= 0.95 and # type: ignore
                    Levenshtein.ratio(loved_track.title.lower(), local_track.title.lower()) >= 0.95 # type: ignore
                ):
                    if os.path.exists(f"{self.final_folder}/{local_track.filename}"):
                        break
                    if self.symlinks:
                        os.symlink(local_track.path, f"{self.final_folder}/{local_track.filename}")
                    else:
                        shutil.copy2(local_track.path, self.final_folder)
                    break
            else:
                self._problems.add(loved_track)
            self._processed_amount += 1
            self.signal_track_processed.emit(self._processed_amount)

    def run(self):
        self.initialize()
        self.process()
        if self._is_running:
            self.signal_finished.emit(self._problems)
