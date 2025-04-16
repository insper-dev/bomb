# client/scenes/matchmaking.py
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
        self.opponent_id = None
        self.match_id = None
        self.error_message = None
        self.cancel_button_rect = None
        self.start_time = time.time()

        # Register matchmaking callbacks
        self.app.matchmaking_service.add_on_state_change_listener(self._on_state_change)
        self.app.matchmaking_service.add_on_match_found_listener(self._on_match_found)
        self.app.matchmaking_service.add_on_queue_update_listener(self._on_queue_update)
        self.app.matchmaking_service.add_on_error_listener(self._on_error)

        # Join matchmaking queue
        self.app.matchmaking_service.join_matchmaking_queue()

    def handle_event(self, event) -> None:
        if event.type == pygame.QUIT:
            # Make sure to leave the queue when closing
            self.app.matchmaking_service.leave_matchmaking_queue()
            self.app.running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Check if clicked on cancel button
            if self.cancel_button_rect and self.cancel_button_rect.collidepoint(event.pos):
                self.app.matchmaking_service.leave_matchmaking_queue()
                self.app.current_scene = Scenes.START

    def render(self) -> None:
        # Background
        self.app.screen.fill(self.color_bg)

        # Title
        title_text = "Finding Match" if not self.match_found else "Match Found!"
        title_surface = self.font_large.render(title_text, True, self.color_text)
        title_rect = title_surface.get_rect(center=(self.app.screen.get_width() // 2, 100))
        self.app.screen.blit(title_surface, title_rect)

        if self.match_found:
            # Match found info
            match_text = f"Match ID: {self.match_id}"
            match_surface = self.font_medium.render(match_text, True, self.color_text)
            match_rect = match_surface.get_rect(center=(self.app.screen.get_width() // 2, 200))
            self.app.screen.blit(match_surface, match_rect)

            opponent_text = f"Opponent: {self.opponent_id}"
            opponent_surface = self.font_medium.render(opponent_text, True, self.color_text)
            opponent_rect = opponent_surface.get_rect(
                center=(self.app.screen.get_width() // 2, 250)
            )
            self.app.screen.blit(opponent_surface, opponent_rect)

            connecting_text = "Connecting to game..."
            connecting_surface = self.font_medium.render(connecting_text, True, self.color_text)
            connecting_rect = connecting_surface.get_rect(
                center=(self.app.screen.get_width() // 2, 350)
            )
            self.app.screen.blit(connecting_surface, connecting_rect)

            # Loading spinner
            current_time = pygame.time.get_ticks()
            angle = (current_time % 1000) / 1000 * 360
            center = (self.app.screen.get_width() // 2, 420)
            radius = 20

            # Draw spinning circle segments
            for i in range(8):
                segment_angle = angle + i * 45
                start_pos = (
                    center[0]
                    + int(radius * 0.7 * pygame.math.Vector2(1, 0).rotate(segment_angle).x),
                    center[1]
                    + int(radius * 0.7 * pygame.math.Vector2(1, 0).rotate(segment_angle).y),
                )
                end_pos = (
                    center[0] + int(radius * pygame.math.Vector2(1, 0).rotate(segment_angle).x),
                    center[1] + int(radius * pygame.math.Vector2(1, 0).rotate(segment_angle).y),
                )

                # Fade colors based on position
                alpha = 255 - (i * 30)
                if alpha < 0:
                    alpha = 0

                pygame.draw.line(self.app.screen, (255, 255, 255, alpha), start_pos, end_pos, 3)

        else:
            # Queue info
            position_text = f"Queue Position: {self.queue_position}"
            position_surface = self.font_medium.render(position_text, True, self.color_text)
            position_rect = position_surface.get_rect(
                center=(self.app.screen.get_width() // 2, 200)
            )
            self.app.screen.blit(position_surface, position_rect)

            wait_time_text = f"Wait Time: {self._format_time(self.wait_time)}"
            wait_time_surface = self.font_medium.render(wait_time_text, True, self.color_text)
            wait_time_rect = wait_time_surface.get_rect(
                center=(self.app.screen.get_width() // 2, 250)
            )
            self.app.screen.blit(wait_time_surface, wait_time_rect)

            estimated_text = f"Estimated Wait: {self._format_time(self.estimated_wait)}"
            estimated_surface = self.font_medium.render(estimated_text, True, self.color_text)
            estimated_rect = estimated_surface.get_rect(
                center=(self.app.screen.get_width() // 2, 300)
            )
            self.app.screen.blit(estimated_surface, estimated_rect)

            # Searching animation
            dots = "." * (1 + int(time.time() - self.start_time) % 4)
            searching_text = f"Searching{dots}"
            searching_surface = self.font_medium.render(searching_text, True, self.color_text)
            searching_rect = searching_surface.get_rect(
                center=(self.app.screen.get_width() // 2, 350)
            )
            self.app.screen.blit(searching_surface, searching_rect)

            # Cancel button
            self.cancel_button_rect = pygame.Rect(
                self.app.screen.get_width() // 2 - 100, 400, 200, 50
            )
            mouse_pos = pygame.mouse.get_pos()
            cancel_button_color = (
                self.color_button_hover
                if self.cancel_button_rect.collidepoint(mouse_pos)
                else self.color_button
            )
            pygame.draw.rect(
                self.app.screen, cancel_button_color, self.cancel_button_rect, border_radius=5
            )

            cancel_text = "Cancel"
            cancel_surface = self.font_medium.render(cancel_text, True, self.color_text)
            cancel_text_rect = cancel_surface.get_rect(center=self.cancel_button_rect.center)
            self.app.screen.blit(cancel_surface, cancel_text_rect)

        # Error message (if any)
        if self.error_message:
            error_surface = self.font_small.render(self.error_message, True, (255, 50, 50))
            error_rect = error_surface.get_rect(center=(self.app.screen.get_width() // 2, 500))
            self.app.screen.blit(error_surface, error_rect)

    def update(self) -> None:
        # Check if match was found, move to game scene after a delay
        if self.match_found and time.time() - self.start_time > 3:
            # Set up the game connection
            self.app.game_service.connect_to_game(self.match_id)
            self.app.current_scene = Scenes.GAME

        # Call parent update
        super().update()

    def _on_state_change(self, state) -> None:
        """Called when matchmaking state changes"""
        if state == MatchmakingState.MATCH_FOUND:
            self.match_found = True
            self.start_time = time.time()  # Reset timer for the transition delay

        elif state == MatchmakingState.ERROR:
            # Go back to start scene on error
            self.app.current_scene = Scenes.START

    def _on_match_found(self, match_id, opponent_id) -> None:
        """Called when a match is found"""
        self.match_id = match_id
        self.opponent_id = opponent_id
        self.match_found = True

    def _on_queue_update(self, position, wait_time, estimated_wait) -> None:
        """Called when queue position is updated"""
        self.queue_position = position
        self.wait_time = wait_time
        self.estimated_wait = estimated_wait

    def _on_error(self, error_message) -> None:
        """Called when an error occurs"""
        self.error_message = error_message

    def _format_time(self, seconds) -> str:
        """Format seconds into mm:ss"""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
