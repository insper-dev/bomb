from typing import Literal

import pygame

from core.constants import EXPLOSION_PARTICLES, MODULE_SIZE


class Particles:
    def __init__(
        self, screen: pygame.Surface, partcles, position: tuple[int, int], radius: int
    ) -> None:
        self.screen = screen
        self.paticles = partcles
        self.images: dict[Literal["geo", "tail", "tip"], list[pygame.Surface]] = EXPLOSION_PARTICLES
        self.position = position
        self.radius = radius
        self._initialize_timer()
        self._draw()

    def _draw(self) -> None:
        main_surface = pygame.Surface(
            (MODULE_SIZE * 2 + MODULE_SIZE, MODULE_SIZE * 2 + MODULE_SIZE), flags=pygame.SRCALPHA
        )
        main_surface = main_surface.convert_alpha()
        width, height = main_surface.get_size()

        middle = (width / 2, height / 2)

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
                for image, position in zip(images, positions, strict=False):
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
                for image, position in zip(images, positions, strict=False):
                    image_rect = image.get_rect(center=(position))
                    main_surface.blit(image, image_rect)
            print(i)
        self.surface = main_surface

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

    def render(self) -> str:
        self._update_timer()
        rect = self.surface.get_rect(
            center=(self.position[0] + MODULE_SIZE / 2, self.position[1] + MODULE_SIZE / 2)
        )
        self.screen.blit(self.surface, rect)
        to_remove = ""
        if self.time["time_counter"] > 500:
            for key, value in self.paticles.items():
                if value == self:
                    to_remove = key
        return to_remove
