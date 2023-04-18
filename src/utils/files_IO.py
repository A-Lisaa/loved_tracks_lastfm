import json
import os
from typing import Any

from .logger import get_logger

_logger = get_logger(__file__)

def read_json_file(path: str) -> Any:
    if not os.path.exists(path):
        _logger.critical("Could not find file %s", path)
        raise OSError(f"Could not find file {path}")
    with open(path, encoding="utf-8") as json_file:
        return json.load(json_file)

def write_json_file(obj: Any, path: str):
    folder, _ = os.path.split(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, mode="w", encoding="utf-8") as json_file:
        json.dump(obj, json_file, indent=4)
