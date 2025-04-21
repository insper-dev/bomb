from typing import Literal

import pygame

from core.constants import CARLITOS


class Player:
    def __init__(
        self,
        screen: pygame.Surface,
        position: tuple[int, int],
        images: dict[Literal["up", "down", "left", "right", "stand_by"], list[pygame.Surface]],
        map: dict | None = None,
    ) -> None:
        self.screen = screen
        self.position = position
        self.map = map
        self.sprites = images
        self.sprites_index: int = 0
        self.velocity: int = 1
        self.moviment_state: Literal["stand_by", "left", "right", "down", "up"] = "stand_by"
        self._initialize_timer()

    def render(self) -> None:
        self._update_timer()
        self._handle_animation()

    def handle_events(self, event: pygame.event.Event) -> None:
        self._change_moviment_state(event)

    def _initialize_timer(self) -> None:
        self.time: dict[Literal["time_elapsed", "initial_time", "time_counter"], int] = {
            "time_elapsed": 0,
            "initial_time": pygame.time.get_ticks(),
            "time_counter": 0,
        }
        self.movement_time: int = 100  # miliseconds

    def _update_timer(self) -> None:
        current_time = pygame.time.get_ticks()
        self.time["time_elapsed"] = current_time - self.time["initial_time"]
        self.time["initial_time"] = current_time
        self.time["time_counter"] += self.time["time_elapsed"]

    def _move(self) -> None:
        direction = self.moviment_state
        pos = self.position
        vel = self.velocity
        if direction == "move_left":
            self.position = (pos[0] + vel, pos[1])
        if direction == "move_left":
            self.position = (pos[0] + vel, pos[1])
        if direction == "move_left":
            self.position = (pos[0] + vel, pos[1])
        if direction == "move_left":
            self.position = (pos[0] + vel, pos[1])

    def _handle_animation(self) -> None:
        sprites = self.sprites[self.moviment_state]
        sprites_quantity = len(sprites)
        if self.time["time_counter"] > self.movement_time:
            self.movement_time = 0
            self.__draw(sprites[self.sprites_index])
            self.sprites_index = (self.sprites_index + 1) % sprites_quantity

    def _change_moviment_state(self, event: pygame.event.Event) -> None:
        movements: dict[int, Literal["right", "left", "up", "down"]] = {
            pygame.K_LEFT: "left",
            pygame.K_RIGHT: "right",
            pygame.K_UP: "up",
            pygame.K_DOWN: "down",
        }
        if event.type in movements:
            self.moviment_state = movements[event.type]
        else:
            self.moviment_state = "stand_by"

    def __draw(self, image: pygame.Surface) -> None:
        rect = image.get_rect(topleft=self.position)
        self.screen.blit(image, rect)


class Carlitos(Player):
    def __init__(
        self,
        screen: pygame.Surface,
        position: tuple[int, int],
        map: dict | None = None,
    ) -> None:
        super().__init__(screen, position, CARLITOS, map)
