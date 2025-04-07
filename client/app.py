"""
Cliente Bomberman Online - Factory da Aplicação
"""

from core.abstract import App
from core.config import Settings


class ClientApp(App):
    """Game App Client"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.running = False
        self.clock = None
        self.screen = None
        self.current_scene = None
        self.event_handler = None
        self.api_client = None
        self.ws_client = None

    def run(self) -> None:
        print("Hello, World!")
