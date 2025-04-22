import pygame

from client.scenes.base import BaseScene, Scenes
from client.services.game import GameService
from core.constants import BLOCKS, BOMB_COKING, CARLITOS, EXPLOSION_PARTICLES, MODULE_SIZE, PURPLE
from core.models.game import GameState, GameStatus
from core.types import PlayerDirectionState


class GameScene(BaseScene):
    """Minimal scene to render Bomberman using GameService and GameState."""

    def __init__(self, app) -> None:
        super().__init__(app)
        # Services
        self.gs: GameService = app.game_service
        self.match_id: str = app.matchmaking_service.match_id or ""
        # Start realtime connection
        self.gs.start(self.match_id)
        self.gs.register_game_ended_callback(self._on_game_end)

        # Pygame setup
        self.font = pygame.font.SysFont(None, 36)
        self.end_text: pygame.Surface | None = None
        self.end_timer = 0
        self.end_delay = 3000  # ms before return to menu

        # Render state
        self.state: GameState | None = None
        self.margin = (0, 0)

    def _on_game_end(self, status: GameStatus, winner: str | None) -> None:
        # Prepare end game message and timer
        if status == GameStatus.DRAW:
            msg = "Draw!"
        elif winner and winner == self.app.auth_service.current_user.id:
            msg = "You Won!"
        else:
            msg = "You Lost!"
        self.end_text = self.font.render(msg, True, (255, 255, 255))
        self.end_timer = pygame.time.get_ticks()

    def _calc_margin(self, map_width: int, map_height: int) -> None:
        screen_w, screen_h = self.app.screen.get_size()
        total_w = map_width * MODULE_SIZE
        total_h = map_height * MODULE_SIZE
        self.margin = (
            (screen_w - total_w) // 2,
            (screen_h - total_h) // 2,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        # Exit to menu
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.gs.stop()
            self.app.current_scene = Scenes.START
            return
        # Movement keys
        if event.type == pygame.KEYDOWN:
            key_map: dict[int, PlayerDirectionState] = {
                pygame.K_UP: "up",
                pygame.K_DOWN: "down",
                pygame.K_LEFT: "left",
                pygame.K_RIGHT: "right",
            }
            if event.key in key_map:
                self.gs.send_move(key_map[event.key])
            elif event.key == pygame.K_SPACE:
                self.gs.send_bomb()

    def update(self) -> None:
        # Update latest state
        self.state = self.gs.state
        # Check end delay
        if self.end_text:
            now = pygame.time.get_ticks()
            if now - self.end_timer > self.end_delay:
                self.app.current_scene = Scenes.GAME_OVER
        super().update()

    def render(self) -> None:
        screen = self.app.screen
        screen.fill(PURPLE)
        if not self.state:
            return
        # Compute margin once
        map_h = len(self.state.map)
        map_w = len(self.state.map[0]) if map_h else 0
        self._calc_margin(map_w, map_h)
        mx, my = self.margin

        # Draw map tiles
        for y, row in enumerate(self.state.map):
            for x, cell in enumerate(row):
                rect = pygame.Rect(
                    mx + x * MODULE_SIZE,
                    my + y * MODULE_SIZE,
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
                (mx, my + y * MODULE_SIZE),
                (mx + map_w * MODULE_SIZE, my + y * MODULE_SIZE),
            )
        for x in range(map_w + 1):
            pygame.draw.line(
                screen,
                (255, 255, 255),
                (mx + x * MODULE_SIZE, my),
                (mx + x * MODULE_SIZE, my + map_h * MODULE_SIZE),
            )

        # Draw players
        for pstate in self.state.players.values():
            x = mx + pstate.x * MODULE_SIZE
            y = my + pstate.y * MODULE_SIZE
            player_rect = pygame.Rect(x, y, MODULE_SIZE, MODULE_SIZE)

            # Choose the correct player sprite based on direction
            player_images = CARLITOS
            direction = pstate.direction_state or "stand_by"
            # Use animation frame based on player position to simulate movement
            frame_idx = int(pstate.x + pstate.y) % len(player_images[direction])
            player_sprite = player_images[direction][frame_idx]

            # Draw the player
            screen.blit(player_sprite, player_rect)

        # Draw bombs
        for pstate in self.state.players.values():
            for bomb in pstate.bombs:
                bomb_rect = pygame.Rect(
                    mx + bomb.x * MODULE_SIZE, my + bomb.y * MODULE_SIZE, MODULE_SIZE, MODULE_SIZE
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
                            mx + (bomb.x + dx) * MODULE_SIZE,
                            my + (bomb.y + dy) * MODULE_SIZE,
                            MODULE_SIZE,
                            MODULE_SIZE,
                        )
                        screen.blit(EXPLOSION_PARTICLES["tip"][i], exp_rect)
                else:
                    # Bomb cooking animation
                    frame_idx = (pygame.time.get_ticks() // 200) % len(BOMB_COKING)
                    bomb_sprite = BOMB_COKING[frame_idx]
                    screen.blit(bomb_sprite, bomb_rect)

        # Draw end text if any
        if self.end_text:
            tx, ty = self.end_text.get_size()
            sx, sy = screen.get_size()
            screen.blit(self.end_text, ((sx - tx) // 2, (sy - ty) // 2))
