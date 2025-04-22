import pygame

from client.game.bomb import Bomb
from client.game.player import Player
from client.scenes.base import BaseScene, Scenes
from client.services.game import GameService
from core.constants import BLOCKS, BOMB_COKING, EXPLOSION_PARTICLES, MODULE_SIZE, PURPLE
from core.models.game import GameState, GameStatus


class GameScene(BaseScene):
    """Minimal scene to render Bomberman using GameService and GameState."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.service: GameService = app.game_service
        self.match_id: str = app.matchmaking_service.match_id or ""
        self.service.start(self.match_id)
        self.service.register_game_ended_callback(self._on_game_end)

        self.state: GameState | None = None

        # Initiate margin
        self.margim: tuple[int, int]

        # Initiate players hehe
        self.players: dict[str, Player]

        # Initiate bombs kaboom
        self.bombs: list[Bomb] = []

    def _on_game_end(self, status: GameStatus, winner: str | None) -> None:
        # TODO: mover pra cena de game over
        ...

    def _init_players(self, state: GameState) -> None:
        self.players = {}
        for id in state.players.keys():
            self.players[id] = Player(self.service, self.margim)

    def _calc_margin(self, state: GameState) -> None:
        y = self.app.screen_center[0] - len(state.map) * MODULE_SIZE // 2
        x = self.app.screen_center[1] - len(state.map[0]) * MODULE_SIZE // 2
        self.margim = (x, y)

    def handle_event(self, event: pygame.event.Event) -> None:
        # Exit to menu
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.service.stop()
            self.app.current_scene = Scenes.START
            return

        # TODO: instancia de player
        state = self.service.state
        user = self.app.auth_service.current_user
        if state is not None and user is not None:
            for id, player in self.players.items():
                if id == user.id:
                    player.handle_event(event)

        # TODO: passar o evento para o player
        # Movement keys

    def update(self) -> None:
        # Update latest state
        self.state = self.service.state
        if self.state is None:
            return

        # Calculate margin
        self._calc_margin(self.state)

        # Initiate Players object
        self._init_players(self.state)

        # Check end delay
        super().update()

    def render(self) -> None:
        screen = self.app.screen
        screen.fill(PURPLE)
        if not self.state:
            return
        # Compute margin once
        map_h = len(self.state.map)
        map_w = len(self.state.map[0]) if map_h else 0

        # Draw map tiles
        for y, row in enumerate(self.state.map):
            for x, cell in enumerate(row):
                rect = pygame.Rect(
                    self.margim[0] + x * MODULE_SIZE,
                    self.margim[1] + y * MODULE_SIZE,
                    MODULE_SIZE,
                    MODULE_SIZE,
                )
                block = BLOCKS[cell]
                screen.blit(block, rect)

        # Draw grid lines
        for y in range(map_h + 1):
            pygame.draw.line(
                screen,
                (255, 255, 255),
                (self.margim[0], self.margim[1] + y * MODULE_SIZE),
                (self.margim[0] + map_w * MODULE_SIZE, self.margim[1] + y * MODULE_SIZE),
            )
        for x in range(map_w + 1):
            pygame.draw.line(
                screen,
                (255, 255, 255),
                (self.margim[0] + x * MODULE_SIZE, self.margim[1]),
                (self.margim[0] + x * MODULE_SIZE, self.margim[1] + map_h * MODULE_SIZE),
            )

        # Draw players
        for player in self.players.values():
            player.render()

        # Draw bombs
        for pstate in self.state.players.values():
            for bomb in pstate.bombs:
                bomb_rect = pygame.Rect(
                    self.margim[0] + bomb.x * MODULE_SIZE,
                    self.margim[1] + bomb.y * MODULE_SIZE,
                    MODULE_SIZE,
                    MODULE_SIZE,
                )

                # Pick bomb sprite based on time (animation)
                if bomb.exploded_at:
                    # If bomb exploded, draw explosion particles
                    core_rect = bomb_rect.copy()
                    screen.blit(EXPLOSION_PARTICLES["geo"][0], core_rect)

                    # Draw explosion in four directions
                    for i, direction in enumerate([(0, -1), (1, 0), (0, 1), (-1, 0)]):
                        dx, dy = direction
                        exp_rect = pygame.Rect(
                            self.margim[0] + (bomb.x + dx) * MODULE_SIZE,
                            self.margim[1] + (bomb.y + dy) * MODULE_SIZE,
                            MODULE_SIZE,
                            MODULE_SIZE,
                        )
                        screen.blit(EXPLOSION_PARTICLES["tip"][i], exp_rect)
                else:
                    # Bomb cooking animation
                    frame_idx = (pygame.time.get_ticks() // 200) % len(BOMB_COKING)
                    bomb_sprite = BOMB_COKING[frame_idx]
                    screen.blit(bomb_sprite, bomb_rect)
