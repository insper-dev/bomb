from typing import Literal

import pygame

from client.services.game import GameService
from core.constants import BLOCKS, CARLITOS, MODULE_SIZE
from core.types import Coordinate, PlayerDirectionState


class Player:
    def __init__(
        self,
        screen: pygame.Surface,
        position: tuple[int, int],
        images: dict[PlayerDirectionState, list[pygame.Surface]],
        game_service: GameService,
        margin: tuple[int, int],
        map: list[list[str]],
    ) -> None:
        # Window Screen
        self.screen = screen

        # Margin to aling with map
        self.margin = margin

        # Position relative to image list
        self.relative_position = position

        # Real position to be dranw
        self.position: tuple[float, float] = (
            self.relative_position[0] * MODULE_SIZE + self.margin[0],
            self.relative_position[1] * MODULE_SIZE + self.margin[1],
        )

        # Game service containing the playesr state and more
        self.game_service = game_service

        # Map list[list[str]]
        self.map = map

        # A list of list of images
        self.sprites = images

        # Sprites change index
        self.sprites_index: int = 0

        # Player transition velocity
        self.velocity: int = 200

        # Player animation deslocation
        self.ds = 0

        # Player stand by image
        self.stand_by_image = self.sprites["stand_by"][0]

        # Player moviment state
        self.moviment_state: PlayerDirectionState = "stand_by"

        # Player general status
        self.status: dict[Literal["vidas", "power", "active_power_up"], int | None] = {
            "vidas": 10,
            "power": 1,
            "active_power_up": None,
        }

        # Player internal clock
        self._initialize_timer()

    def render(self) -> None:
        """
        Player general rederization
            _update_timer()
            _move()
            _handle_animation()
        """

        self._update_timer()
        self._move()
        self._handle_animation()

    def _initialize_timer(self) -> None:
        """
        Initializae the player personal clock with the properties:
            time_elapsed
            initial_time
            time_counter
        """

        self.time: dict[Literal["time_elapsed", "initial_time", "time_counter"], int] = {
            "time_elapsed": 0,
            "initial_time": pygame.time.get_ticks(),
            "time_counter": 0,
        }
        self.movement_time: int = 1000  # miliseconds

    def _update_timer(self) -> None:
        """
        Update the player internal clock with math operations:
            time_elapsed = current_time - initial_time
            initial_time = current_time
            time_counter = time_counter + time_elapsed
        """
        current_time = pygame.time.get_ticks()
        self.time["time_elapsed"] = current_time - self.time["initial_time"]
        self.time["initial_time"] = current_time
        self.time["time_counter"] += self.time["time_elapsed"]

    def _update_position(self) -> None:
        """
        Update the player real position
        """

        x = self.relative_position[0] * MODULE_SIZE + self.margin[0]
        y = self.relative_position[1] * MODULE_SIZE + self.margin[1]
        self.position = (x, y)

    def _move(self) -> None:
        """
        Move the player if the animations is active, else just update its position:
            if direction == 'stand_by':
                self._update_postion()
                return
            ... (Movement)
        """
        direction = self.moviment_state
        if direction == "stand_by":
            self._update_position()
            return
        # Gets the time elapsed in seconds dt[seconds]
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

    def _handle_animation(self) -> None:
        """
        Handles sprites animations
        """

        sprites = self.sprites[self.moviment_state]
        sprites_quantity = len(sprites)
        if self.time["time_counter"] > self.movement_time:
            self.movement_time = 0
            self.sprites_index = (self.sprites_index + 1) % sprites_quantity
            self.time["time_counter"] = 0

        if self.moviment_state == "stand_by":
            self.__draw(self.stand_by_image)
            return
        self.__draw(sprites[self.sprites_index])

    def change_moviment_state(self, direction: PlayerDirectionState) -> bool:
        """
        Changes the moviment state and returns True if completed and False if not
        Args:
            direction (PlayerDirectionState): ('up', 'down', 'right', 'left')
        """
        if self.moviment_state != "stand_by" or direction == "stand_by":
            return False

        pos = self.relative_position

        around: dict[PlayerDirectionState, Coordinate] = {
            "up": (pos[0], pos[1] - 1),
            "right": (pos[0] + 1, pos[1]),
            "down": (pos[0], pos[1] + 1),
            "left": (pos[0] - 1, pos[1]),
        }
        x, y = around[direction]
        if y >= len(self.map) or x >= len(self.map[0]) or y < 0 or x < 0:
            return False
        if self.map[y][x] in BLOCKS.keys():
            return False

        stand_by_images = self.sprites["stand_by"]
        stand_by: dict[PlayerDirectionState, pygame.Surface] = {
            "right": stand_by_images[0],
            "left": stand_by_images[1],
            "down": stand_by_images[2],
            "up": stand_by_images[3],
        }
        self.relative_position = around[direction]
        self.stand_by_image = stand_by[direction]
        self.moviment_state = direction
        return True

    def __draw(self, image: pygame.Surface) -> None:
        """
        Draw the player image in its positions
        Args:
            image (pygame.Surface): player image sprite
        """
        rect = image.get_rect(topleft=self.position)
        image.convert_alpha()
        self.screen.blit(image, rect)


class Carlitos(Player):
    def __init__(
        self,
        screen: pygame.Surface,
        position: tuple[int, int],
        game_service: GameService,
        margin: tuple[int, int],
        map: list[list[str]],
    ) -> None:
        super().__init__(screen, position, CARLITOS, game_service, margin, map)
