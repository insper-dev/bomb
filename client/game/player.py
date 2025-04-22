from collections.abc import Callable

import pygame

from client.services.game import GameService
from core.constants import MODULE_SIZE, PLAYERS_MAP
from core.models.game import GameState, PlayerState
from core.types import PlayerDirectionState


class Player:
    # TODO: passar user id nessa poha, e substituir o curreent user state.
    def __init__(self, game_service: GameService, margin: tuple[int, int]) -> None:
        self.game_service = game_service
        self.app = game_service.app
        self.margin = margin
        self.__real_position = (0, 0)
        self.__sprite_index: int = 0
        self.__initial_time = pygame.time.get_ticks()
        self.__time_counter = 0
        self.__velocity = 200
        self.__distance = 0
        self.__is_moving = False
        self.game_service.register_moviment_callback(self._on_move_callback)

    def _on_move_callback(self, position: tuple[int, int]) -> None:
        self.__is_moving = True
        self.__real_position = position
        self.__initial_time = pygame.time.get_ticks()
        self.__distance = 0

    @property
    def time_elapsed(self) -> int:
        dt = self.__initial_time - pygame.time.get_ticks()
        self.__time_counter += dt
        self.__initial_time = pygame.time.get_ticks()
        return dt

    @property
    def sprite_index(self) -> int:
        if self.current_player_state is None:
            raise Exception("Current player state is None")

        if self.__time_counter >= 500:
            self.__time_counter = 0
            self.__sprite_index = (self.__sprite_index + 1) % len(
                PLAYERS_MAP[self.current_player_state.skin]
            )

        return self.__sprite_index

    @property
    def state(self) -> GameState | None:
        return self.game_service.state

    @property
    def current_player_state(self) -> PlayerState | None:
        if self.state is None:
            return None

        if self.app.auth_service.current_user is None:
            # ! WARNING: This should not happen.
            return None

        return self.state.players[self.app.auth_service.current_user.id]

    @property
    def real_position(self) -> tuple[int, int]:
        if self.current_player_state is None:
            return (0, 0)

        if not self.__is_moving:
            return (
                self.current_player_state.x * MODULE_SIZE + self.margin[0],
                self.current_player_state.y * MODULE_SIZE + self.margin[1],
            )

        walked_distance = self.__velocity * self.time_elapsed
        self.__distance += walked_distance
        self.__is_moving = self.__distance < MODULE_SIZE

        move_map: dict[PlayerDirectionState, Callable] = {
            "up": lambda x, y: (x, y - walked_distance),
            "down": lambda x, y: (x, y + walked_distance),
            "left": lambda x, y: (x - walked_distance, y),
            "right": lambda x, y: (x + walked_distance, y),
        }
        fn = move_map[self.current_player_state.direction_state]
        self.__real_position = fn(self.__real_position)

        return self.__real_position

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            key_map: dict[int, PlayerDirectionState] = {
                pygame.K_UP: "up",
                pygame.K_DOWN: "down",
                pygame.K_LEFT: "left",
                pygame.K_RIGHT: "right",
            }
            if event.key in key_map and not self.__is_moving:
                self.game_service.send_move(key_map[event.key])
            elif event.key == pygame.K_SPACE:
                self.game_service.send_bomb()

    def render(self) -> None:
        if self.current_player_state is None:
            return

        player_sprites = PLAYERS_MAP[self.current_player_state.skin]

        sprite = player_sprites[self.current_player_state.direction_state][self.sprite_index]

        self.app.screen.blit(sprite, self.real_position)
