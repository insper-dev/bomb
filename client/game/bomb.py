from typing import Literal

import pygame
import pygame.surface


class Bomb:
    def __init__(
        self,
        screen: pygame.Surface,
        images: list[pygame.Surface],
        position: tuple[int, int],
        explosion_radius: int,
    ) -> None:
        self.screen = screen
        self.sprites = images
        self.position = position
        self.sprite_index = 0
        self.explosion_radius = explosion_radius
        self.tick = 500  # mileconds
        self.explode = False
        self.ready = False
        self._initialize_timer()

    def _initialize_timer(self) -> None:
        self.time: dict[Literal["time_elapsed", "initial_time", "time_counter"], int] = {
            "time_elapsed": 0,
            "initial_time": pygame.time.get_ticks(),
            "time_counter": 0,
        }

    def __draw(self) -> None:
        image = self.sprites[self.sprite_index]
        rect = image.get_rect(top_left=self.position)
        self.screen.blit(image, rect)

    def _coking(self) -> None:
        if self.sprite_index >= len(self.sprites):
            self.ready = True
            return
        self.__draw()
        if self.time["time_counter"] >= self.tick:
            self.sprite_index += 1

    def render(self) -> None:
        self._coking()
