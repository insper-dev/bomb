"""
Cliente Bomberman Online - Factory da Aplicação
"""

import pygame

from client.api import APIClient
from client.scenes import SCENES_MAP, Scenes
from client.services import AuthService
from core.abstract import App
from core.config import Settings


class ClientApp(App):
    """Game App Client"""

    screen: pygame.Surface
    clock: pygame.time.Clock
    current_scene: Scenes = Scenes.START
    running: bool = False
    auth_service: AuthService

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.event_handler = None
        # TODO: settings.host is a enviroment variable just to the client. The server should user
        # another one to "bind"
        self.api_client = APIClient(self.settings.host)
        self.auth_service = AuthService(self)
        self.ws_client = None

    @property
    def screen_center(self) -> tuple[int, int]:
        return (self.screen.get_width() // 2, self.screen.get_height() // 2)

    def run(self) -> None:
        pygame.init()

        pygame.display.set_caption(self.settings.title)
        self.screen = pygame.display.set_mode([self.settings.width, self.settings.height])

        self.clock = pygame.time.Clock()
        self.running = True

        while self.running:
            self.clock.tick(self.settings.fps)

            scene = SCENES_MAP[self.current_scene]
            # a scene is responsible to update the current state, change scenes, etc.
            scene(self).update()

            pygame.display.flip()

        pygame.quit()
