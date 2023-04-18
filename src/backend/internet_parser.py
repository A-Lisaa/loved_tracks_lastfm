import asyncio
from collections.abc import Collection
from typing import Any

import requests
# pylint: disable=no-name-in-module
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from ..utils.logger import get_logger
from .track_data import InternetTrackData

API_KEY = ""

_logger = get_logger(__file__)

async def get_response(link: str) -> requests.models.Response:
    response = requests.get(link)
    _logger.debug("Got response from %s with status code = %d", link, response.status_code)
    return response

async def get_responses(links: Collection[str]) -> list[requests.models.Response]:
    return await asyncio.gather(*[get_response(link) for link in links])

async def get_json_response(link: str) -> Any:
    return (await get_response(link)).json()

async def get_json_responses(links: Collection[str]) -> list[Any]:
    return await asyncio.gather(*[get_json_response(link) for link in links])

class InternetParser(QObject):
    signal_initialized = pyqtSignal(int)
    signal_finished = pyqtSignal(set)
    signal_track_processed = pyqtSignal(int)
    signal_cancel = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.username = ""
        self._is_running = True
        @pyqtSlot()
        def cancel():
            self._is_running = False
        self.signal_cancel.connect(cancel)
        self._base_url = f"https://ws.audioscrobbler.com/2.0/?method=user.getlovedtracks&user={self.username}&api_key={API_KEY}&format=json"
        self._tracks = set()
        self._pages_amount = 0
        self._tracks_processed = 0

    def initialize(self):
        self._is_running = True
        self._base_url = f"https://ws.audioscrobbler.com/2.0/?method=user.getlovedtracks&user={self.username}&api_key={API_KEY}&format=json"
        self._tracks = set()
        self._pages_amount = 0
        self._tracks_processed = 0

        json_response = requests.get(self._base_url).json()

        issue = self.check_connection(json_response)
        if issue:
            _logger.warning(issue)
            return
        _logger.debug("Connection is successful")

        tracks_amount = int(json_response["lovedtracks"]["@attr"]["total"])
        self._pages_amount = int(json_response["lovedtracks"]["@attr"]["totalPages"])

        self.signal_initialized.emit(tracks_amount)

    def check_connection(self, json_response: dict[str, Any]) -> str:
        if issue := json_response.get("message", ""):
            return issue
        return ""

    async def _parse_page(self, link: str):
        if not self._is_running:
            return
        json_response = await get_json_response(link)
        for track in json_response["lovedtracks"]["track"]:
            track_data = InternetTrackData(
                track["artist"]["name"],
                track["name"],
                track["artist"]["url"],
                track["url"],
            )
            self._tracks.add(track_data)
            self._tracks_processed += 1
            self.signal_track_processed.emit(self._tracks_processed)

    async def _parse_tracks(self, username: str):
        await asyncio.gather(
            *[
                self._parse_page(
                    (
                        "https://ws.audioscrobbler.com/2.0/?method=user.getlovedtracks"
                        f"&user={username}&page={page}&api_key={API_KEY}&format=json"
                    )
                )
                for page in range(1, self._pages_amount+1)
            ]
        )

    def run(self):
        self.initialize()
        asyncio.run(self._parse_tracks(self.username))
        if self._is_running:
            self.signal_finished.emit(self._tracks)
            _logger.debug("Parsing is done: loved_tracks - %d", len(self._tracks))
