from typing import Literal

import pygame

from core.constants import BLCOKS, DESTROYABLE_BLOCKS, EXPLOSION_PARTICLES, MODULE_SIZE


class Particles:
    def __init__(
        self,
        screen: pygame.Surface,
        position: tuple[int, int],
        margin: tuple[int, int],
        radius: int,
        map: list[list[str]],
    ) -> None:
        self.screen = screen
        self.map = map
        self.images: dict[Literal["geo", "tail", "tip"], list[pygame.Surface]] = EXPLOSION_PARTICLES
        self.relative_position = position
        self.magin = margin
        self.position: tuple[int, int] = (
            self.relative_position[0] * MODULE_SIZE + self.magin[0],
            self.relative_position[1] * MODULE_SIZE + self.magin[1],
        )
        self.radius = radius
        self.range_directions: dict[Literal["left", "right", "up", "donw"], int] = {
            "left": self.radius,
            "right": self.radius,
            "up": self.radius,
            "donw": self.radius,
        }
        self.is_done = False
        self._initialize_timer()
        self._destroy()
        self._draw()

    def _draw(self) -> None:
        main_surface = pygame.Surface(
            (
                MODULE_SIZE * 2 * self.radius + MODULE_SIZE,
                MODULE_SIZE * 2 * self.radius + MODULE_SIZE,
            ),
            flags=pygame.SRCALPHA,
        )
        main_surface = main_surface.convert_alpha()
        width, height = main_surface.get_size()

        middle = (width / 2, height / 2)

        key_mapping: dict[int, Literal["left", "right", "up", "donw"]] = {
            0: "up",
            1: "left",
            2: "donw",
            3: "right",
        }

        for i in range(self.radius + 1):
            if i == 0:
                image = self.images["geo"][0]
                image_rect = image.get_rect(center=middle)
                main_surface.blit(image, image_rect)
            elif i == self.radius:
                images = self.images["tip"]
                positions = [
                    (middle[0], middle[1] - MODULE_SIZE * i),
                    (middle[0] - MODULE_SIZE * i, middle[1]),
                    (middle[0], middle[1] + MODULE_SIZE * i),
                    (middle[0] + MODULE_SIZE * i, middle[1]),
                ]
                for id, (image, position) in enumerate(zip(images, positions, strict=False)):
                    key = key_mapping[id]
                    if i in range(self.range_directions[key] + 1):
                        image_rect = image.get_rect(center=(position))
                        main_surface.blit(image, image_rect)
            else:
                images = self.images["tail"]
                positions = [
                    (middle[0], middle[1] - MODULE_SIZE * i),
                    (middle[0] - MODULE_SIZE * i, middle[1]),
                    (middle[0], middle[1] + MODULE_SIZE * i),
                    (middle[0] + MODULE_SIZE * i, middle[1]),
                ]
                for id, (image, position) in enumerate(zip(images, positions, strict=False)):
                    key = key_mapping[id]
                    if i in range(self.range_directions[key] + 1):
                        image_rect = image.get_rect(center=(position))
                        main_surface.blit(image, image_rect)
        self.surface = main_surface

    def _destroy(self) -> None:
        directions: dict[Literal["left", "right", "up", "donw"], tuple[int, int]] = {
            "left": (-1, 0),
            "right": (1, 0),
            "up": (0, -1),
            "donw": (0, 1),
        }
        off: list[str] = []
        for i in range(self.radius):
            for direction, value in directions.items():
                x, y = (
                    self.relative_position[0] + value[0] * (i + 1),
                    self.relative_position[1] + value[1] * (i + 1),
                )
                if (
                    direction not in off
                    and (len(self.map[0]) > x >= 0 and len(self.map) > y >= 0)
                    and self.map[y][x] in BLCOKS.keys()
                ):
                    if self.map[y][x] in DESTROYABLE_BLOCKS:
                        self.map[y][x] = "f_shed1"
                        self.range_directions[direction] = i + 1
                    else:
                        self.range_directions[direction] = i
                    off.append(direction)

    def _initialize_timer(self) -> None:
        self.time: dict[Literal["time_elapsed", "initial_time", "time_counter"], int] = {
            "time_elapsed": 0,
            "initial_time": pygame.time.get_ticks(),
            "time_counter": 0,
        }
        self.animation_time: int = 500  # miliseconds

    def _update_timer(self) -> None:
        current_time = pygame.time.get_ticks()
        self.time["time_elapsed"] = current_time - self.time["initial_time"]
        self.time["initial_time"] = current_time
        self.time["time_counter"] += self.time["time_elapsed"]

    def _update_state(self) -> None:
        if self.time["time_counter"] > self.animation_time:
            self.is_done = True
            return
        rect = self.surface.get_rect(
            center=(self.position[0] + MODULE_SIZE / 2, self.position[1] + MODULE_SIZE / 2)
        )
        self.screen.blit(self.surface, rect)

    def render(self) -> None:
        self._update_timer()
        self._update_state()
