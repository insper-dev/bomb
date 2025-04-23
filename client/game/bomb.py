from typing import Literal

import pygame

from core.constants import BOMB_COKING, MODULE_SIZE


class Bomb:
    def __init__(
        self,
        screen: pygame.Surface,
        position: tuple[int, int],
        margin: tuple[int, int],
    ) -> None:
        self.screen = screen
        self.sprites = BOMB_COKING
        self.margin = margin
        self.relative_position = position
        self.position: tuple[int, int] = (
            self.relative_position[0] * MODULE_SIZE + self.margin[0],
            self.relative_position[1] * MODULE_SIZE + self.margin[1],
        )
        self.sprite_index = 0
        self.tick = 200  # mileconds
        self.explosion_time = self.tick * len(self.sprites)
        self.explode = False
        self._initialize_timer()

    def _initialize_timer(self) -> None:
        self.time: dict[Literal["time_elapsed", "initial_time", "time_counter"], int] = {
            "time_elapsed": 0,
            "initial_time": pygame.time.get_ticks(),
            "time_counter": 0,
        }

    def _update_timer(self) -> None:
        current_time = pygame.time.get_ticks()
        self.time["time_elapsed"] = current_time - self.time["initial_time"]
        self.time["initial_time"] = current_time
        self.time["time_counter"] += self.time["time_elapsed"]

    def __draw(self) -> None:
        image = self.sprites[self.sprite_index]
        rect = image.get_rect(topleft=self.position)
        self.screen.blit(image, rect)

    def _coking(self) -> None:
        if self.sprite_index >= len(self.sprites):
            self.ready = True
            del self
            return
        self.__draw()
        if self.time["time_counter"] >= self.tick:
            self.sprite_index += 1
            self.time["time_counter"] = 0

    def _explode_check(self) -> None:
        if not self.explode:
            return

    def render(self) -> None:
        self._update_timer()
        self._coking()
        self._explode_check()
