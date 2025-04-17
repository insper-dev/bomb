import time

import pygame

from client.scenes.base import BaseScene, Scenes
from core.models.matchmaking import MatchmakingState


class MatchmakingScene(BaseScene):
    """Matchmaking scene for finding opponents"""

    def __init__(self, app) -> None:
        super().__init__(app)

        # UI Elements
        self.font_large = pygame.font.SysFont(None, 60)
        self.font_medium = pygame.font.SysFont(None, 36)
        self.font_small = pygame.font.SysFont(None, 24)

        # Colors
        self.color_bg = (0, 0, 0)
        self.color_text = (255, 255, 255)
        self.color_button = (100, 50, 50)
        self.color_button_hover = (120, 70, 70)

        # State
        self.queue_position = 0
        self.wait_time = 0
        self.estimated_wait = 0
        self.match_found = False
        self.opponent_id: str | None = None
        self.match_id: str | None = None
        self.error_message: str | None = None
        self.cancel_button_rect: pygame.Rect | None = None
        self.start_time = time.time()

        # Register matchmaking callbacks
        ms = self.app.matchmaking_service
        ms.add_on_state_change_listener(self._on_state_change)
        ms.add_on_match_found_listener(self._on_match_found)
        ms.add_on_queue_update_listener(self._on_queue_update)
        ms.add_on_error_listener(self._on_error)

        # Join matchmaking queue
        ms.join_matchmaking_queue()

    def handle_event(self, event) -> None:
        if event.type == pygame.QUIT:
            self.app.matchmaking_service.leave_matchmaking_queue()
            self.app.running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.cancel_button_rect and self.cancel_button_rect.collidepoint(event.pos):
                self.app.matchmaking_service.leave_matchmaking_queue()
                self.app.current_scene = Scenes.START

    def render(self) -> None:
        screen = self.app.screen
        screen.fill(self.color_bg)

        title = "Match Found!" if self.match_found else "Finding Match"
        surface = self.font_large.render(title, True, self.color_text)
        rect = surface.get_rect(center=(screen.get_width() // 2, 100))
        screen.blit(surface, rect)

        if self.match_found:
            # Display match info
            info = [
                f"Match ID: {self.match_id}",
                f"Opponent: {self.opponent_id}",
                "Connecting to game...",
            ]
            for idx, txt in enumerate(info):
                surf = self.font_medium.render(txt, True, self.color_text)
                r = surf.get_rect(center=(screen.get_width() // 2, 200 + idx * 50))
                screen.blit(surf, r)
            # spinner
            t = pygame.time.get_ticks() % 1000 / 1000 * 360
            center = (screen.get_width() // 2, 420)
            r = 20
            for i in range(8):
                angle = t + i * 45
                vec = pygame.math.Vector2(1, 0).rotate(angle)
                start = (center[0] + vec.x * r * 0.7, center[1] + vec.y * r * 0.7)
                end = (center[0] + vec.x * r, center[1] + vec.y * r)
                alpha = max(0, 255 - i * 30)
                color = (255, 255, 255, alpha)
                pygame.draw.line(screen, color, start, end, 3)
        else:
            # Queue info
            texts = [
                f"Queue Position: {self.queue_position}",
                f"Wait Time: {self._format_time(self.wait_time)}",
                f"Estimated Wait: {self._format_time(self.estimated_wait)}",
            ]
            for idx, txt in enumerate(texts):
                surf = self.font_medium.render(txt, True, self.color_text)
                r = surf.get_rect(center=(screen.get_width() // 2, 200 + idx * 50))
                screen.blit(surf, r)
            # searching dots animation
            dots = "." * (1 + int(time.time() - self.start_time) % 4)
            surf = self.font_medium.render(f"Searching{dots}", True, self.color_text)
            r = surf.get_rect(center=(screen.get_width() // 2, 350))
            screen.blit(surf, r)
            # Cancel button
            self.cancel_button_rect = pygame.Rect(screen.get_width() // 2 - 100, 400, 200, 50)
            mp = pygame.mouse.get_pos()
            col = (
                self.color_button_hover
                if self.cancel_button_rect.collidepoint(mp)
                else self.color_button
            )
            pygame.draw.rect(screen, col, self.cancel_button_rect, border_radius=5)
            surf = self.font_medium.render("Cancel", True, self.color_text)
            r = surf.get_rect(center=self.cancel_button_rect.center)
            screen.blit(surf, r)

        # Error
        if self.error_message:
            surf = self.font_small.render(self.error_message, True, (255, 50, 50))
            r = surf.get_rect(center=(screen.get_width() // 2, 500))
            screen.blit(surf, r)

    def update(self) -> None:
        # After match found, wait 3s then start game
        if self.match_found and time.time() - self.start_time > 3:
            self.app.matchmaking_service.match_id = self.match_id
            self.app.matchmaking_service.leave_matchmaking_queue()
            self.app.current_scene = Scenes.GAME

        super().update()

    def _on_state_change(self, state: MatchmakingState) -> None:
        if state == MatchmakingState.MATCH_FOUND:
            self.match_found = True
            self.start_time = time.time()
        elif state == MatchmakingState.ERROR:
            self.app.current_scene = Scenes.START

    def _on_match_found(self, match_id: str, opponent_id: str) -> None:
        self.match_id = match_id
        self.opponent_id = opponent_id
        self.match_found = True

    def _on_queue_update(self, position: int, wait_time: float, estimated_wait: float) -> None:
        self.queue_position = position
        self.wait_time = wait_time
        self.estimated_wait = estimated_wait

    def _on_error(self, error_message: str) -> None:
        self.error_message = error_message

    def _format_time(self, seconds: float) -> str:
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins:02d}:{secs:02d}"
