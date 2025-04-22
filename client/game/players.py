from turtle import position
from typing import Literal

import pygame

from client.services.game import GameService
from core.constants import CARLITOS, MODULE_SIZE
from core.types import PlayerDirectionState


class Player:
    def __init__(
        self,
        screen: pygame.Surface,
        position: tuple[int, int],
        images: dict[PlayerDirectionState, list[pygame.Surface]],
        game_service: GameService,
        map: dict | None = None,
    ) -> None:
        self.screen = screen
        self.position = position
        self.last_position = position
        self.game_service = game_service
        self.map = map
        self.sprites = images
        self.sprites_index: int = 0
        self.velocity: int = 200
        self.ds = 0
        self.moviment_state: PlayerDirectionState = "stand_by"
        self.status: dict[Literal["vidas", "power", "active_power_up"], int | None] = {
            "vidas": 10,
            "power": 1,
            "active_power_up": None,
        }
        self._initialize_timer()

    def render(self) -> None:
        self._update_timer()
        self._handle_animation()
        self._move()

    def handle_events(self, event: pygame.event.Event) -> None:
        self._change_moviment_state(event)

    def _initialize_timer(self) -> None:
        self.time: dict[Literal["time_elapsed", "initial_time", "time_counter"], int] = {
            "time_elapsed": 0,
            "initial_time": pygame.time.get_ticks(),
            "time_counter": 0,
        }
        self.movement_time: int = 1000  # miliseconds

    def _update_timer(self) -> None:
        current_time = pygame.time.get_ticks()
        self.time["time_elapsed"] = current_time - self.time["initial_time"]
        self.time["initial_time"] = current_time
        self.time["time_counter"] += self.time["time_elapsed"]

    def _move(self) -> None:
        direction = self.moviment_state
        if direction == "stand_by":
            return
        dt = self.time["time_elapsed"] / 1000
        pos = self.position
        vel = self.velocity
        if self.ds < MODULE_SIZE:
            if direction == "right":
                self.position = (pos[0] + vel * dt, pos[1])
            if direction == "left":
                self.position = (pos[0] - vel * dt, pos[1])
            if direction == "up":
                self.position = (pos[0], pos[1] - vel * dt)
            if direction == "down":
                self.position = (pos[0], pos[1] + vel * dt)
            self.ds += vel * dt
        else:
            self.ds = 0
            self.moviment_state = "stand_by"
            self.game_service.send_move(self.moviment_state)

    def _handle_animation(self) -> None:
        sprites = self.sprites[self.moviment_state]
        sprites_quantity = len(sprites)
        if self.time["time_counter"] > self.movement_time:
            self.movement_time = 0
            self.sprites_index = (self.sprites_index + 1) % sprites_quantity
            self.__draw(sprites[self.sprites_index])
            self.time["time_counter"] = 0

    def _change_moviment_state(self, event: pygame.event.Event) -> None:
        if self.moviment_state != "stand_by":
            return
        movements: dict[int, Literal["right", "left", "up", "down"]] = {
            pygame.K_LEFT: "left",
            pygame.K_RIGHT: "right",
            pygame.K_UP: "up",
            pygame.K_DOWN: "down",
        }
        if event.type == pygame.KEYDOWN and event.key in movements:
            key = movements[event.key]
            self.moviment_state = key
            self.last_position = position
            self.game_service.send_move(key)

    def __draw(self, image: pygame.Surface) -> None:
        rect = image.get_rect(topleft=self.position)
        image.convert_alpha()
        self.screen.blit(image, rect)


class Carlitos(Player):
    def __init__(
        self,
        screen: pygame.Surface,
        position: tuple[int, int],
        game_service: GameService,
        map: dict | None = None,
    ) -> None:
        super().__init__(screen, position, CARLITOS, game_service, map)
