# client/scenes/game.py
import pygame

from client.scenes.base import BaseScene, Scenes


class GameScene(BaseScene):
    """Game scene"""

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
        self.game_started = False
        self.game_ended = False
        self.winner_id = None
        self.exit_button_rect = None

        # Player info
        self.local_player = None
        self.opponent = None

        # Register game callbacks
        self.app.game_service.register_message_callback("game_start", self._on_game_start)
        self.app.game_service.register_message_callback("game_end", self._on_game_end)

    def handle_event(self, event) -> None:
        if event.type == pygame.QUIT:
            # Disconnect from game when closing
            self.app.game_service.disconnect_from_game()
            self.app.running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Check if clicked on exit button
            if self.exit_button_rect and self.exit_button_rect.collidepoint(event.pos):
                self.app.game_service.disconnect_from_game()
                self.app.current_scene = Scenes.START

        # Game controls would go here in a real implementation
        # For now, we're just showing the connection was successful

    def render(self) -> None:
        # Background
        self.app.screen.fill(self.color_bg)

        # Get player info
        self.local_player = self.app.game_service.get_local_player()
        other_players = self.app.game_service.get_other_players()
        self.opponent = next(iter(other_players.values()), None) if other_players else None

        # Title
        if self.game_ended:
            title_text = "Game Over!"
        elif self.game_started:
            title_text = "Game Running"
        else:
            title_text = "Connecting to Game"

        title_surface = self.font_large.render(title_text, True, self.color_text)
        title_rect = title_surface.get_rect(center=(self.app.screen.get_width() // 2, 100))
        self.app.screen.blit(title_surface, title_rect)

        # Game ID
        game_id_text = f"Game ID: {self.app.game_service.game_id}"
        game_id_surface = self.font_medium.render(game_id_text, True, self.color_text)
        game_id_rect = game_id_surface.get_rect(center=(self.app.screen.get_width() // 2, 150))
        self.app.screen.blit(game_id_surface, game_id_rect)

        # Players info
        if self.local_player:
            # Local player info
            player_text = f"You: {self.app.auth_service.current_user.username if self.app.auth_service.current_user else 'Player'}"  # noqa: E501
            player_surface = self.font_medium.render(player_text, True, self.color_text)
            player_rect = player_surface.get_rect(topleft=(100, 200))
            self.app.screen.blit(player_surface, player_rect)

            # Player status
            status_text = f"Status: {'Alive' if self.local_player.alive else 'Dead'}"
            status_surface = self.font_medium.render(status_text, True, self.color_text)
            status_rect = status_surface.get_rect(topleft=(100, 240))
            self.app.screen.blit(status_surface, status_rect)

            # Player position
            position_text = f"Position: ({int(self.local_player.position.x)}, {int(self.local_player.position.y)})"  # noqa: E501
            position_surface = self.font_small.render(position_text, True, self.color_text)
            position_rect = position_surface.get_rect(topleft=(100, 280))
            self.app.screen.blit(position_surface, position_rect)

        if self.opponent:
            # Opponent info
            opponent_text = f"Opponent: {self.opponent.id}"
            opponent_surface = self.font_medium.render(opponent_text, True, self.color_text)
            opponent_rect = opponent_surface.get_rect(topleft=(400, 200))
            self.app.screen.blit(opponent_surface, opponent_rect)

            # Opponent status
            opponent_status_text = f"Status: {'Alive' if self.opponent.alive else 'Dead'}"
            opponent_status_surface = self.font_medium.render(
                opponent_status_text, True, self.color_text
            )
            opponent_status_rect = opponent_status_surface.get_rect(topleft=(400, 240))
            self.app.screen.blit(opponent_status_surface, opponent_status_rect)

            # Opponent position
            opponent_pos_text = (
                f"Position: ({int(self.opponent.position.x)}, {int(self.opponent.position.y)})"
            )
            opponent_pos_surface = self.font_small.render(opponent_pos_text, True, self.color_text)
            opponent_pos_rect = opponent_pos_surface.get_rect(topleft=(400, 280))
            self.app.screen.blit(opponent_pos_surface, opponent_pos_rect)

        # Game status
        if self.game_ended and (user := self.app.auth_service.current_user):
            # Show winner
            winner_text = "You won!" if self.winner_id == user.id else "You lost!"
            winner_surface = self.font_large.render(winner_text, True, self.color_text)
            winner_rect = winner_surface.get_rect(center=(self.app.screen.get_width() // 2, 350))
            self.app.screen.blit(winner_surface, winner_rect)

        elif not self.game_started:
            # Show connecting animation
            dots = "." * (1 + (pygame.time.get_ticks() // 500) % 4)
            connecting_text = f"Connecting{dots}"
            connecting_surface = self.font_medium.render(connecting_text, True, self.color_text)
            connecting_rect = connecting_surface.get_rect(
                center=(self.app.screen.get_width() // 2, 350)
            )
            self.app.screen.blit(connecting_surface, connecting_rect)
        else:
            # Show game controls instructions
            controls_text = "Game connected successfully!"
            controls_surface = self.font_medium.render(controls_text, True, self.color_text)
            controls_rect = controls_surface.get_rect(
                center=(self.app.screen.get_width() // 2, 350)
            )
            self.app.screen.blit(controls_surface, controls_rect)

            instructions_text = "In a full implementation, the game board would be shown here."
            instructions_surface = self.font_small.render(instructions_text, True, self.color_text)
            instructions_rect = instructions_surface.get_rect(
                center=(self.app.screen.get_width() // 2, 380)
            )
            self.app.screen.blit(instructions_surface, instructions_rect)

        # Exit button
        self.exit_button_rect = pygame.Rect(self.app.screen.get_width() // 2 - 100, 500, 200, 50)
        mouse_pos = pygame.mouse.get_pos()
        exit_button_color = (
            self.color_button_hover
            if self.exit_button_rect.collidepoint(mouse_pos)
            else self.color_button
        )
        pygame.draw.rect(self.app.screen, exit_button_color, self.exit_button_rect, border_radius=5)

        exit_text = "Exit Game"
        exit_surface = self.font_medium.render(exit_text, True, self.color_text)
        exit_text_rect = exit_surface.get_rect(center=self.exit_button_rect.center)
        self.app.screen.blit(exit_surface, exit_text_rect)

    def _on_game_start(self, data) -> None:
        """Called when the game starts"""
        self.game_started = True

    def _on_game_end(self, data) -> None:
        """Called when the game ends"""
        self.game_ended = True
        self.winner_id = data.get("winner_id")
