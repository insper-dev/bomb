from typing import Literal

import pygame

from client.scenes.base import BaseScene, Scenes
from client.services.game import GameService
from core.models.game import GameStatus


class GameScene(BaseScene):
    """Scene to render and control the Bomberman game via WebSocket."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.game_service: GameService = app.game_service
        self.game_id: str = app.matchmaking_service.match_id or ""
        self.margin: int = 20
        self.game_service.start(self.game_id)

        # Register callback for game end
        self.game_service.register_game_ended_callback(self._on_game_ended)

        # UI elements
        self.font_large = pygame.font.SysFont(None, 48)
        self.font_medium = pygame.font.SysFont(None, 36)
        self.font_small = pygame.font.SysFont(None, 24)

        # Auto-return to menu timer
        self.return_to_menu_timer = None
        self.return_countdown = 5  # seconds

    def _on_game_ended(self, status: GameStatus, winner_id: str | None) -> None:
        """Called when the game ends"""
        # Não chame game_service.stop() aqui - isso tentará parar a thread de dentro dela mesma
        # Apenas definimos uma flag para fazer a transição na thread principal
        self.should_transition_to_game_over = True

    def handle_event(self, event) -> None:
        if event.type == pygame.QUIT:
            self.app.running = False
        elif event.type == pygame.KEYDOWN:
            # Movement keys
            if not self.game_service.is_game_ended:
                key_map: dict[int, Literal["up", "down", "left", "right"]] = {
                    pygame.K_UP: "up",
                    pygame.K_DOWN: "down",
                    pygame.K_LEFT: "left",
                    pygame.K_RIGHT: "right",
                }
                if event.key in key_map:
                    self.game_service.send_move(key_map[event.key])
            if event.key == pygame.K_SPACE and not self.game_service.is_game_ended:
                self.game_service.send_bomb()
            # Exit to menu
            elif event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
                self.game_service.stop()
                self.app.current_scene = Scenes.START

    def update(self) -> None:
        # Primeiro verificamos se o jogo sinalizou que acabou e devemos transitar para o game over
        if hasattr(self, "should_transition_to_game_over") and self.should_transition_to_game_over:
            # Primeiro paramos o game service (na thread principal)
            if self.game_service.running:
                print("Stopping game service from main thread")
                self.game_service.stop()
            # Então mudamos para a cena de game over
            self.app.current_scene = Scenes.GAME_OVER
            return

        # Processamento normal
        super().update()

    def render(self) -> None:
        screen = self.app.screen
        screen.fill((0, 0, 0))
        state = self.game_service.state
        if not state:
            return

        rows, cols = len(state.map), len(state.map[0])
        if cols == 0:
            return

        # Compute cell size
        avail_w = screen.get_width() - 2 * self.margin
        avail_h = screen.get_height() - 2 * self.margin - 100
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
        for idx, (player_id, pstate) in enumerate(state.players.items()):
            if (
                self.game_service.is_game_ended
                and state.status == GameStatus.WINNER
                and state.winner_id == player_id
            ):
                color = (255, 215, 0)
            else:
                color = colors[idx % len(colors)]

            cx = self.margin + pstate.x * size + size / 2
            cy = self.margin + pstate.y * size + size / 2
            radius = size * 0.4
            pygame.draw.circle(screen, color, (int(cx), int(cy)), int(radius))

        # Draw bombs
        for bomb in state.bombs:
            bx = self.margin + bomb.x * size + size / 2
            by = self.margin + bomb.y * size + size / 2
            pygame.draw.circle(screen, (200, 200, 200), (int(bx), int(by)), int(size * 0.3))

        # Draw explosions as a "+" cross
        for exp in state.explosions:
            cx = self.margin + exp.x * size + size // 2
            cy = self.margin + exp.y * size + size // 2
            arm = exp.radius * size
            color = (255, 100, 0)
            # central square
            center_rect = pygame.Rect(cx - size // 4, cy - size // 4, size // 2, size // 2)
            pygame.draw.rect(screen, color, center_rect)
            # horizontal arm
            horiz_rect = pygame.Rect(cx - arm, cy - size // 8, arm * 2, size // 4)
            pygame.draw.rect(screen, color, horiz_rect)
            # vertical arm
            vert_rect = pygame.Rect(cx - size // 8, cy - arm, size // 4, arm * 2)
            pygame.draw.rect(screen, color, vert_rect)

        if self.game_service.is_game_ended:
            result_text = self.game_service.game_result
            text = self.font_large.render(result_text, True, (255, 255, 255))
            rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() - 80))
            screen.blit(text, rect)

            if self.return_to_menu_timer:
                remaining = max(0, (self.return_to_menu_timer - pygame.time.get_ticks()) // 1000)
                countdown = self.font_medium.render(
                    f"Returning to menu in {remaining} seconds...", True, (200, 200, 200)
                )
                screen.blit(
                    countdown,
                    (
                        screen.get_width() // 2 - countdown.get_width() // 2,
                        screen.get_height() - 40,
                    ),
                )
        else:
            # Regular game instructions
            instr = self.font_small.render("Use arrow keys to move", True, (180, 180, 180))
            screen.blit(instr, (self.margin, screen.get_height() - 80))

            instr2 = self.font_small.render("Press ESC to return to menu", True, (180, 180, 180))
            screen.blit(instr2, (self.margin, screen.get_height() - 50))
