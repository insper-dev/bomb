import pygame

from core.constants import BLOCKS
from core.types import Coordinate


class BaseBlock:
    def __init__(self, screen: pygame.Surface, image_name: str, position: Coordinate) -> None:
        self.screen = screen
        self.image: pygame.Surface = BLOCKS[image_name]
        self.position = position
        self.rect = self.image.get_rect(topleft=self.position)

    def render(self) -> None:
        self.screen.blit(self.image, self.rect)
