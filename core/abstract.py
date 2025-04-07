from abc import ABC, abstractmethod

from core.config import Settings


class App(ABC):
    settings: Settings

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError
