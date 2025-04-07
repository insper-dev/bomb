"""
Cliente Bomberman Online - Factory da Aplicação
"""

import pygame

from client.scenes import SCENES_MAP, Scenes
from core.abstract import App
from core.config import Settings


class ClientApp(App):
    """Game App Client"""

    screen: pygame.Surface
    clock: pygame.time.Clock
    current_scene: Scenes = Scenes.START
    running: bool = False

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.event_handler = None
        self.api_client = None
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
