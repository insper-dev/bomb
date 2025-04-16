import pygame

from client.scenes.base import BaseScene, Scenes


class StartScene(BaseScene):
    """Main menu scene"""

    def __init__(self, app) -> None:
        super().__init__(app)

        # UI Elements
        self.font_title = pygame.font.SysFont(None, 80)
        self.font_large = pygame.font.SysFont(None, 50)
        self.font_medium = pygame.font.SysFont(None, 36)
        self.font_small = pygame.font.SysFont(None, 24)

        # Colors
        self.color_bg = (0, 0, 0)
        self.color_text = (255, 255, 255)
        self.color_button = (50, 100, 50)
        self.color_button_hover = (70, 120, 70)
        self.color_auth_button = (100, 50, 50)
        self.color_auth_button_hover = (120, 70, 70)

        # Button rectangles
        self.play_button_rect = None
        self.login_button_rect = None
        self.logout_button_rect = None

        # Register auth callbacks
        self.app.auth_service.register_logout_callback(self._on_logout)
        # to chamando isso daqui abaixo só pra ser definido o "current_user", mas a princípio,
        # ele deve ser chamado pra dar um feedback visual logo de cara na tela inicial.
        self.app.auth_service.is_current_user_loading  # noqa

    def handle_event(self, event) -> None:
        if event.type == pygame.QUIT:
            self.app.running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Check if clicked on play button
            if self.play_button_rect and self.play_button_rect.collidepoint(event.pos):
                if self.app.auth_service.is_logged_in:
                    # Only allow play if logged in
                    self.app.current_scene = Scenes.MATCHMAKING
                else:
                    # Redirect to login if not logged in
                    self.app.current_scene = Scenes.LOGIN

            # Check if clicked on login/logout button
            if self.app.auth_service.is_logged_in:
                if self.logout_button_rect and self.logout_button_rect.collidepoint(event.pos):
                    self.app.auth_service.logout()
            else:
                if self.login_button_rect and self.login_button_rect.collidepoint(event.pos):
                    self.app.current_scene = Scenes.LOGIN

    def render(self) -> None:
        # Background
        self.app.screen.fill(self.color_bg)

        # Title
        title_surface = self.font_title.render(
            self.app.settings.client_title, True, self.color_text
        )
        title_rect = title_surface.get_rect(center=(self.app.screen.get_width() // 2, 100))
        self.app.screen.blit(title_surface, title_rect)

        # Subtitle
        subtitle_surface = self.font_medium.render(
            "A Bomberman-like online game", True, self.color_text
        )
        subtitle_rect = subtitle_surface.get_rect(center=(self.app.screen.get_width() // 2, 160))
        self.app.screen.blit(subtitle_surface, subtitle_rect)

        # User information
        if self.app.auth_service.is_logged_in and (user := self.app.auth_service.current_user):
            user_text = f"Logged in as: {user.username}"
            user_surface = self.font_medium.render(user_text, True, self.color_text)
            user_rect = user_surface.get_rect(center=(self.app.screen.get_width() // 2, 220))
            self.app.screen.blit(user_surface, user_rect)

        # Play button
        self.play_button_rect = pygame.Rect(self.app.screen.get_width() // 2 - 100, 300, 200, 60)
        mouse_pos = pygame.mouse.get_pos()
        play_button_color = (
            self.color_button_hover
            if self.play_button_rect.collidepoint(mouse_pos)
            else self.color_button
        )
        pygame.draw.rect(self.app.screen, play_button_color, self.play_button_rect, border_radius=5)

        play_text = "Play"
        play_surface = self.font_large.render(play_text, True, self.color_text)
        play_text_rect = play_surface.get_rect(center=self.play_button_rect.center)
        self.app.screen.blit(play_surface, play_text_rect)

        # Login/Logout button
        if self.app.auth_service.is_logged_in:
            # Logout button
            self.logout_button_rect = pygame.Rect(
                self.app.screen.get_width() // 2 - 100, 400, 200, 50
            )
            logout_button_color = (
                self.color_auth_button_hover
                if self.logout_button_rect.collidepoint(mouse_pos)
                else self.color_auth_button
            )
            pygame.draw.rect(
                self.app.screen, logout_button_color, self.logout_button_rect, border_radius=5
            )

            logout_text = "Logout"
            logout_surface = self.font_medium.render(logout_text, True, self.color_text)
            logout_text_rect = logout_surface.get_rect(center=self.logout_button_rect.center)
            self.app.screen.blit(logout_surface, logout_text_rect)
        else:
            # Login button
            self.login_button_rect = pygame.Rect(
                self.app.screen.get_width() // 2 - 100, 400, 200, 50
            )
            login_button_color = (
                self.color_auth_button_hover
                if self.login_button_rect.collidepoint(mouse_pos)
                else self.color_auth_button
            )
            pygame.draw.rect(
                self.app.screen, login_button_color, self.login_button_rect, border_radius=5
            )

            login_text = "Login"
            login_surface = self.font_medium.render(login_text, True, self.color_text)
            login_text_rect = login_surface.get_rect(center=self.login_button_rect.center)
            self.app.screen.blit(login_surface, login_text_rect)

        # Version info
        version_text = "v0.1.0"
        version_surface = self.font_small.render(version_text, True, self.color_text)
        version_rect = version_surface.get_rect(
            bottomright=(self.app.screen.get_width() - 20, self.app.screen.get_height() - 20)
        )
        self.app.screen.blit(version_surface, version_rect)

    def _on_logout(self) -> None:
        """Called when logout is successful"""
        # Stay on the same scene, but it will re-render with login button
        pass
