import pygame

from core.constants import BLCOKS
from core.types import Coordinate


class BaseBlock:
    def __init__(self, screen: pygame.Surface, image_name: str, position: Coordinate) -> None:
        self.screen = screen
        self.image: pygame.Surface = BLCOKS[image_name]
        self.position = position
        self.rect = self.image.get_rect(topleft=self.position)

    def render(self) -> None:
        self.screen.blit(self.image, self.rect)
