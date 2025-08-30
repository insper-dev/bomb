import time

import pygame
from prisma.partials import Opponent

from client.scenes.base import BaseScene, Scenes
from client.services.matchmaking import MatchmakingService
from core.constants import ACCENT_BLUE, ACCENT_GREEN, ACCENT_YELLOW, DARK_NAVY, SLATE_GRAY, WHITE


class MatchmakingScene(BaseScene):
    """Simple matchmaking scene showing connected players and countdown."""

    def __init__(self, app) -> None:
        super().__init__(app)

        # Clear previous game state
        app.game_service.clear_game_state()

        self.matchmaking: MatchmakingService = app.matchmaking_service
        self.matchmaking.start()

        cx, cy = self.app.screen_center

        # Simple UI elements
        self.title_pos = (cx, cy - 100)
        self.player_count_pos = (cx, cy - 40)
        self.countdown_pos = (cx, cy + 20)
        self.status_pos = (cx, cy + 80)
        self.cancel_rect = pygame.Rect(cx - 100, cy + 150, 200, 50)
        self.start_time = time.time()

    def handle_event(self, event) -> None:
        mouse_pos = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.cancel_rect.collidepoint(mouse_pos):
                self._cancel_matchmaking()
                return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._cancel_matchmaking()

    @property
    def match_id(self) -> str | None:
        return getattr(self.matchmaking, "match_id", None)

    @property
    def oponent(self) -> Opponent | None:
        return getattr(self.matchmaking, "opponent", None)

    @property
    def player_count(self) -> int:
        return getattr(self.matchmaking, "player_count", 0)

    @property
    def countdown(self) -> int | None:
        return getattr(self.matchmaking, "countdown", None)

    def update(self) -> None:
        if self.match_id:
            self.matchmaking.stop()
            self.app.game_service.start(self.match_id)
            self.app.current_scene = Scenes.GAME
        super().update()

    def render(self) -> None:
        # Simple dark background
        self.app.screen.fill(DARK_NAVY)

        # Title
        self._render_title()

        # Player count
        self._render_player_count()

        # Countdown if 2+ players
        if self.player_count >= 2 and self.countdown is not None:
            self._render_countdown()

        # Status
        self._render_status()

        # Cancel button
        self._render_cancel_button()

        # Time elapsed
        self._render_time_elapsed()

    def _render_title(self) -> None:
        """Render simple title."""
        font = pygame.font.SysFont("Arial", 36, bold=True)
        text_surface = font.render("Matchmaking", True, WHITE)
        text_rect = text_surface.get_rect(center=self.title_pos)
        self.app.screen.blit(text_surface, text_rect)

    def _render_player_count(self) -> None:
        """Render connected player count."""
        text = f"Jogadores conectados: {self.player_count}/4"
        font = pygame.font.SysFont("Arial", 24)
        text_surface = font.render(text, True, ACCENT_BLUE)
        text_rect = text_surface.get_rect(center=self.player_count_pos)
        self.app.screen.blit(text_surface, text_rect)

    def _render_countdown(self) -> None:
        """Render countdown when 2+ players are connected."""
        if self.countdown is not None and self.countdown > 0:
            text = f"Iniciando em: {self.countdown}"
            font = pygame.font.SysFont("Arial", 32, bold=True)
            text_surface = font.render(text, True, ACCENT_YELLOW)
        else:
            text = "Iniciando partida..."
            font = pygame.font.SysFont("Arial", 28)
            text_surface = font.render(text, True, ACCENT_GREEN)

        text_rect = text_surface.get_rect(center=self.countdown_pos)
        self.app.screen.blit(text_surface, text_rect)

    def _render_status(self) -> None:
        """Render status message."""
        if self.match_id:
            text = "Partida encontrada! Conectando..."
        elif self.player_count >= 2:
            text = "Jogadores suficientes encontrados!"
        elif self.player_count == 1:
            text = "Aguardando mais jogadores..."
        else:
            text = "Procurando jogadores..."

        font = pygame.font.SysFont("Arial", 18)
        text_surface = font.render(text, True, SLATE_GRAY)
        text_rect = text_surface.get_rect(center=self.status_pos)
        self.app.screen.blit(text_surface, text_rect)

    def _render_cancel_button(self) -> None:
        """Render simple cancel button."""
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.cancel_rect.collidepoint(mouse_pos)

        # Button background
        bg_color = (40, 50, 65) if is_hover else (30, 40, 55)
        pygame.draw.rect(self.app.screen, bg_color, self.cancel_rect, border_radius=6)
        pygame.draw.rect(self.app.screen, ACCENT_BLUE, self.cancel_rect, 2, border_radius=6)

        # Button text
        font = pygame.font.SysFont("Arial", 20, bold=True)
        text_surface = font.render("Cancelar", True, WHITE)
        text_rect = text_surface.get_rect(center=self.cancel_rect.center)
        self.app.screen.blit(text_surface, text_rect)

    def _cancel_matchmaking(self) -> None:
        """Cancel matchmaking and return to main menu."""
        self.matchmaking.stop()
        self.app.current_scene = Scenes.MAIN_MENU

    def _render_time_elapsed(self) -> None:
        """Render elapsed time."""
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        time_text = f"Tempo: {mins:02d}:{secs:02d}"

        font = pygame.font.SysFont("Arial", 16)
        text_surface = font.render(time_text, True, WHITE)
        self.app.screen.blit(text_surface, (20, 20))
