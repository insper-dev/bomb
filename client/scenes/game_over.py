import pygame

from client.scenes.base import BaseScene, Scenes
from client.services.game_over import GameOverService


class GameOverScene(BaseScene):
    """Scene displayed after a game ends showing match statistics."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.match_id = app.game_service.state.game_id if app.game_service.state else ""
        self.game_over_service = GameOverService(app)

        # UI elements
        self.font_large = pygame.font.SysFont(None, 48)
        self.font_medium = pygame.font.SysFont(None, 36)
        self.font_small = pygame.font.SysFont(None, 24)

        # Start loading stats if we have a match ID
        if self.match_id:
            self.game_over_service.fetch_stats(self.match_id)

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                # Play again (return to matchmaking)
                self.app.current_scene = Scenes.MATCHMAKING
            elif event.key == pygame.K_ESCAPE:
                # Back to menu
                self.app.current_scene = Scenes.START

    def render(self) -> None:
        screen = self.app.screen
        screen.fill((0, 0, 0))

        # Title
        title = self.font_large.render("Game Over", True, (255, 255, 255))
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 50))

        # Loading or display stats
        if self.game_over_service.is_stats_loading:
            loading = self.font_medium.render("Loading statistics...", True, (180, 180, 180))
            screen.blit(loading, (screen.get_width() // 2 - loading.get_width() // 2, 150))
        elif self.game_over_service.match_stats:
            stats = self.game_over_service.match_stats
            y_pos = 120

            # Winner announcement
            if stats.winner_id:
                winner_name = next(
                    (p.username for p in stats.players if p.user_id == stats.winner_id), "Unknown"
                )
                winner_text = self.font_medium.render(f"Winner: {winner_name}", True, (255, 215, 0))
                screen.blit(
                    winner_text, (screen.get_width() // 2 - winner_text.get_width() // 2, y_pos)
                )
                y_pos += 60

            # Game duration if available
            if stats.duration_seconds is not None:
                mins, secs = divmod(stats.duration_seconds, 60)
                duration = self.font_small.render(
                    f"Game Duration: {mins}:{secs:02d}", True, (200, 200, 200)
                )
                screen.blit(duration, (screen.get_width() // 2 - duration.get_width() // 2, y_pos))
                y_pos += 40

            # Player stats
            for p in stats.players:
                color = (255, 215, 0) if p.is_winner else (200, 200, 200)
                player_text = self.font_small.render(
                    f"Player: {p.username} - Bombs: {p.bombs_placed} - Kills: {p.players_killed}",
                    True,
                    color,
                )
                screen.blit(
                    player_text, (screen.get_width() // 2 - player_text.get_width() // 2, y_pos)
                )
                y_pos += 40
        elif error := self.game_over_service.get_stats_error():
            error_text = self.font_medium.render(f"Error: {error}", True, (255, 50, 50))
            screen.blit(error_text, (screen.get_width() // 2 - error_text.get_width() // 2, 150))

        # Instructions
        instr1 = self.font_small.render("Press ENTER to play again", True, (180, 180, 180))
        instr2 = self.font_small.render("Press ESC to return to menu", True, (180, 180, 180))
        screen.blit(
            instr1, (screen.get_width() // 2 - instr1.get_width() // 2, screen.get_height() - 80)
        )
        screen.blit(
            instr2, (screen.get_width() // 2 - instr2.get_width() // 2, screen.get_height() - 50)
        )

        pygame.display.flip()
