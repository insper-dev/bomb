from enum import Enum

from client.scenes.base import BaseScene
from client.scenes.start import StartScene


class Scenes(str, Enum):
    START = "start"


SCENES_MAP: dict[Scenes, type[BaseScene]] = {Scenes.START: StartScene}
"""Mapping of scenes to their respective classes."""


__all__ = ["SCENES_MAP", "Scenes"]
