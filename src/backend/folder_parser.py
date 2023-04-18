import asyncio
import os
from pathlib import Path

import eyed3
# pylint: disable=no-name-in-module
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from ..utils.logger import get_logger
from .track_data import LocalTrackData

_logger = get_logger(__file__)
# Отключаем логирование предупреждений из модуля (по большей части они не нужны)
eyed3.log.setLevel(40)

class FolderParser(QObject):
    signal_initialized = pyqtSignal(int)
    signal_finished = pyqtSignal(set)
    signal_track_processed = pyqtSignal(int)
    signal_cancel = pyqtSignal()

    def __init__(self):
        super().__init__()

        self._is_running = True
        @pyqtSlot()
        def cancel():
            self._is_running = False
        self.signal_cancel.connect(cancel)
        self._root_folder = Path()
        self._files = set()
        self._tracks = set()
        self._tracks_processed = 0

    @property
    def root_folder(self):
        return self._root_folder

    @root_folder.setter
    def root_folder(self, value: str | Path):
        self._root_folder = value if isinstance(value, Path) else Path(value)

    def initialize(self):
        self._is_running = True
        self._files = set()
        self._tracks = set()
        self._tracks_processed = 0

        issue = self.check_folder(self.root_folder)
        if issue:
            _logger.warning(issue)
        else:
            _logger.debug("Folder %s checked, everythin is fine", str(self.root_folder))

        self._files = set(
            Path(root).joinpath(name)
            for root, _, files in os.walk(self.root_folder)
            for name in files
        )

        files_amount = len(self._files)

        self.signal_initialized.emit(files_amount)

    def check_folder(self, folder: Path) -> str:
        if folder.suffix != "":
            issue = f"{str(folder.absolute())} is not a directory"
            return issue

        folder = folder.absolute()
        folder.mkdir(exist_ok=True)
        return ""

    def parse_filename(self, filename: str) -> tuple[str, str]:
        parted = filename.split(".")[0].split(" - ")
        if len(parted) == 2:
            return parted[0], parted[1]
        elif len(parted) == 1:
            return "", parted[0]
        return "", ""

    async def get_track_data(self, path: Path) -> LocalTrackData | None:
        if not os.path.exists(path):
            return
        audiofile = eyed3.load(path)
        if audiofile is None:
            return

        if audiofile.tag.artist is None or audiofile.tag.title is None: # type: ignore
            artist, title = self.parse_filename(path.name)
        if audiofile.tag.artist is not None: # type: ignore
            artist = audiofile.tag.artist # type: ignore
        if audiofile.tag.title is not None: # type: ignore
            title = audiofile.tag.title # type: ignore

        track_data = LocalTrackData(
            artist, # type: ignore
            title, # type: ignore
            str(path.absolute()),
            path.name
        )

        return track_data

    async def _set_track_data(self, path: Path):
        if not self._is_running:
            return
        track_data = await self.get_track_data(path)
        if track_data is not None:
            self._tracks.add(track_data)
        self._tracks_processed += 1
        self.signal_track_processed.emit(self._tracks_processed)

    async def _parse_tracks(self):
        await asyncio.gather(
            *[
                self._set_track_data(path) for path in self._files
            ]
        )

    def run(self):
        self.initialize()
        asyncio.run(self._parse_tracks())
        if self._is_running:
            self.signal_finished.emit(self._tracks)
            _logger.debug("Parsing is done: local_tracks - %d", len(self._tracks))
