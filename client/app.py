"""
Cliente Bomberman Online - Factory da Aplicação
"""

import pygame

from client.api import APIClient
from client.scenes import SCENES_MAP, Scenes
from client.services import AuthService, MatchmakingService
from core.abstract import App
from core.config import Settings


class ClientApp(App):
    """Game App Client"""

    screen: pygame.Surface
    clock: pygame.time.Clock
    current_scene: Scenes = Scenes.START
    running: bool = False
    auth_service: AuthService
    matchmaking_service: MatchmakingService

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.event_handler = None
        self.api_client = APIClient(self.settings.server_endpoint)
        self.auth_service = AuthService(self)
        self.matchmaking_service = MatchmakingService(self)
        self.ws_client = None

    @property
    def screen_center(self) -> tuple[int, int]:
        return (self.screen.get_width() // 2, self.screen.get_height() // 2)

    def run(self) -> None:
        pygame.init()

        pygame.display.set_caption(self.settings.client_title)
        self.screen = pygame.display.set_mode(
            [self.settings.client_width, self.settings.client_height]
        )

        self.clock = pygame.time.Clock()
        self.running = True

        while self.running:
            self.clock.tick(self.settings.client_fps)

            scene = SCENES_MAP[self.current_scene]
            # a scene is responsible to update the current state, change scenes, etc.
            scene(self).update()

            pygame.display.flip()

        pygame.quit()
