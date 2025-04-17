from typing import Literal

import pygame

from client.scenes.base import BaseScene, Scenes
from client.services.game import GameService


class GameScene(BaseScene):
    """Scene to render and control the Bomberman game via WebSocket."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.game_service: GameService = app.game_service
        self.game_id: str = app.matchmaking_service.match_id or ""
        self.margin: int = 20
        self.game_service.start(self.game_id)

    def handle_event(self, event) -> None:
        if event.type == pygame.QUIT:
            self.app.running = False
        elif event.type == pygame.KEYDOWN:
            # Movement keys
            key_map: dict[int, Literal["up", "down", "left", "right"]] = {
                pygame.K_UP: "up",
                pygame.K_DOWN: "down",
                pygame.K_LEFT: "left",
                pygame.K_RIGHT: "right",
            }
            if event.key in key_map:
                self.game_service.send_move(key_map[event.key])
            # Exit to menu
            elif event.key == pygame.K_ESCAPE:
                self.game_service.stop()
                self.app.current_scene = Scenes.START

    def render(self) -> None:
        screen = self.app.screen
        screen.fill((0, 0, 0))

        if not self.game_service.game_state:
            # Waiting message
            font = pygame.font.SysFont(None, 48)
            text = font.render("Waiting for game state...", True, (200, 200, 200))
            rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
            screen.blit(text, rect)
            return

        rows = len(self.game_service.game_state.map)
        cols = len(self.game_service.game_state.map[0]) if rows > 0 else 0
        if cols == 0:
            return

        # Compute cell size
        avail_w = screen.get_width() - 2 * self.margin
        avail_h = screen.get_height() - 2 * self.margin
        cell_w = avail_w / cols
        cell_h = avail_h / rows
        size = int(min(cell_w, cell_h))

        # Draw grid
        for y in range(rows):
            for x in range(cols):
                rect = pygame.Rect(
                    self.margin + x * size,
                    self.margin + y * size,
                    size,
                    size,
                )
                pygame.draw.rect(screen, (50, 50, 50), rect, width=1)

        # Draw players
        colors = [(0, 120, 200), (200, 50, 50), (50, 200, 50), (200, 200, 50)]
        for idx, (_, pstate) in enumerate(self.game_service.game_state.players.items()):
            color = colors[idx % len(colors)]
            cx = self.margin + pstate.x * size + size / 2
            cy = self.margin + pstate.y * size + size / 2
            radius = size * 0.4
            pygame.draw.circle(screen, color, (int(cx), int(cy)), int(radius))

        # Instruction to exit
        font_small = pygame.font.SysFont(None, 24)
        instr = font_small.render("Press ESC to return to menu", True, (180, 180, 180))
        screen.blit(instr, (self.margin, screen.get_height() - self.margin - 20))
