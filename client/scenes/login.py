# client/scenes/login.py
import pygame
import pygame.font

from client.scenes.base import BaseScene, Scenes


class LoginScene(BaseScene):
    """Scene for user authentication (login and signup)"""

    def __init__(self, app) -> None:
        super().__init__(app)

        # State
        self.username = ""
        self.password = ""
        self.active_field = "username"  # Current input field: username or password
        self.is_signup_mode = False  # Toggle between login and signup
        self.show_error = False
        self.error_message = ""

        # UI Elements
        self.font_large = pygame.font.SysFont(None, 60)
        self.font_medium = pygame.font.SysFont(None, 36)
        self.font_small = pygame.font.SysFont(None, 24)

        # Colors
        self.color_bg = (0, 0, 0)
        self.color_text = (255, 255, 255)
        self.color_input_bg = (40, 40, 40)
        self.color_input_active = (60, 60, 120)
        self.color_button = (50, 100, 50)
        self.color_button_hover = (70, 120, 70)
        self.color_error = (200, 50, 50)

        # Rectangles for elements (initialize in render)
        self.username_rect = None
        self.password_rect = None
        self.submit_rect = None
        self.toggle_rect = None
        self.back_rect = None

        # Setup auth callbacks
        self.app.auth_service.register_login_success_callback(self._on_login_success)
        self.app.auth_service.register_login_error_callback(self._on_login_error)

    def handle_event(self, event) -> None:
        if event.type == pygame.QUIT:
            self.app.running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Check if clicked on input fields
            if self.username_rect and self.username_rect.collidepoint(event.pos):
                self.active_field = "username"
            elif self.password_rect and self.password_rect.collidepoint(event.pos):
                self.active_field = "password"
            # Check if clicked submit button
            elif self.submit_rect and self.submit_rect.collidepoint(event.pos):
                self._submit()
            # Check if clicked toggle button
            elif self.toggle_rect and self.toggle_rect.collidepoint(event.pos):
                self.is_signup_mode = not self.is_signup_mode
                self.show_error = False  # Clear errors on toggle
            # Check if clicked back button
            elif self.back_rect and self.back_rect.collidepoint(event.pos):
                self.app.current_scene = Scenes.START

        elif event.type == pygame.KEYDOWN:
            # Handle key input for the active field
            if event.key == pygame.K_TAB:
                # Switch between fields
                self.active_field = "password" if self.active_field == "username" else "username"
            elif event.key == pygame.K_RETURN:
                # Submit on Enter
                self._submit()
            elif event.key == pygame.K_BACKSPACE:
                # Delete character on backspace
                if self.active_field == "username":
                    self.username = self.username[:-1]
                else:
                    self.password = self.password[:-1]
            else:
                # Add character
                if event.unicode.isprintable():
                    if self.active_field == "username":
                        self.username += event.unicode
                    else:
                        self.password += event.unicode

    def render(self) -> None:
        # Background
        self.app.screen.fill(self.color_bg)

        # Title
        title_text = "Sign Up" if self.is_signup_mode else "Login"
        title_surface = self.font_large.render(title_text, True, self.color_text)
        title_rect = title_surface.get_rect(center=(self.app.screen.get_width() // 2, 100))
        self.app.screen.blit(title_surface, title_rect)

        # Username field
        username_label = self.font_medium.render("Username:", True, self.color_text)
        username_label_rect = username_label.get_rect(topleft=(200, 200))
        self.app.screen.blit(username_label, username_label_rect)

        # Username input box
        self.username_rect = pygame.Rect(200, 240, 400, 40)
        username_color = (
            self.color_input_active if self.active_field == "username" else self.color_input_bg
        )
        pygame.draw.rect(self.app.screen, username_color, self.username_rect, border_radius=5)

        # Username text
        username_surface = self.font_medium.render(self.username, True, self.color_text)
        username_text_rect = username_surface.get_rect(
            midleft=(self.username_rect.left + 10, self.username_rect.centery)
        )
        self.app.screen.blit(username_surface, username_text_rect)

        # Password field
        password_label = self.font_medium.render("Password:", True, self.color_text)
        password_label_rect = password_label.get_rect(topleft=(200, 300))
        self.app.screen.blit(password_label, password_label_rect)

        # Password input box
        self.password_rect = pygame.Rect(200, 340, 400, 40)
        password_color = (
            self.color_input_active if self.active_field == "password" else self.color_input_bg
        )
        pygame.draw.rect(self.app.screen, password_color, self.password_rect, border_radius=5)

        # Password text (masked)
        masked_password = "*" * len(self.password)
        password_surface = self.font_medium.render(masked_password, True, self.color_text)
        password_text_rect = password_surface.get_rect(
            midleft=(self.password_rect.left + 10, self.password_rect.centery)
        )
        self.app.screen.blit(password_surface, password_text_rect)

        # Submit button
        self.submit_rect = pygame.Rect(300, 420, 200, 50)
        mouse_pos = pygame.mouse.get_pos()
        button_color = (
            self.color_button_hover
            if self.submit_rect.collidepoint(mouse_pos)
            else self.color_button
        )
        pygame.draw.rect(self.app.screen, button_color, self.submit_rect, border_radius=5)

        # Submit button text
        submit_text = "Sign Up" if self.is_signup_mode else "Login"
        submit_surface = self.font_medium.render(submit_text, True, self.color_text)
        submit_text_rect = submit_surface.get_rect(center=self.submit_rect.center)
        self.app.screen.blit(submit_surface, submit_text_rect)

        # Toggle button
        toggle_text = (
            "Already have an account? Login"
            if self.is_signup_mode
            else "Don't have an account? Sign Up"
        )
        toggle_surface = self.font_small.render(toggle_text, True, self.color_text)
        toggle_text_rect = toggle_surface.get_rect(center=(self.app.screen.get_width() // 2, 500))
        self.toggle_rect = toggle_text_rect.inflate(20, 10)
        self.app.screen.blit(toggle_surface, toggle_text_rect)

        # Back button
        back_text = "Back to Menu"
        back_surface = self.font_small.render(back_text, True, self.color_text)
        back_text_rect = back_surface.get_rect(center=(self.app.screen.get_width() // 2, 550))
        self.back_rect = back_text_rect.inflate(20, 10)
        self.app.screen.blit(back_surface, back_text_rect)

        # Error message (if any)
        if self.show_error and self.error_message:
            error_surface = self.font_small.render(self.error_message, True, self.color_error)
            error_rect = error_surface.get_rect(center=(self.app.screen.get_width() // 2, 470))
            self.app.screen.blit(error_surface, error_rect)

        # Loading indicator
        is_loading = (
            self.app.auth_service.is_login_loading or self.app.auth_service.is_signup_loading
        )
        if is_loading:
            # Draw a simple loading spinner
            current_time = pygame.time.get_ticks()
            angle = (current_time % 1000) / 1000 * 360
            center = (self.app.screen.get_width() // 2, 470)
            radius = 15

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

    def update(self) -> None:
        # Check for auth service errors
        if not self.is_signup_mode:
            error = self.app.auth_service.get_login_error()
            if error:
                self.show_error = True
                self.error_message = error
        else:
            error = self.app.auth_service.get_signup_error()
            if error:
                self.show_error = True
                self.error_message = error

        # Call parent update to handle events
        super().update()

    def _submit(self) -> None:
        # Clear previous errors
        self.show_error = False
        self.error_message = ""

        # Validate input
        if not self.username:
            self.show_error = True
            self.error_message = "Username cannot be empty"
            return

        if not self.password:
            self.show_error = True
            self.error_message = "Password cannot be empty"
            return

        if len(self.password) < 6:
            self.show_error = True
            self.error_message = "Password must be at least 6 characters"
            return

        # Submit based on mode
        if self.is_signup_mode:
            self.app.auth_service.signup(self.username, self.password)
        else:
            self.app.auth_service.login(self.username, self.password)

    def _on_login_success(self, token: str) -> None:
        """Called when login/signup is successful"""
        # Redirect to the main menu
        self.app.current_scene = Scenes.START

    def _on_login_error(self, error_message: str) -> None:
        """Called when login/signup fails"""
        self.show_error = True
        self.error_message = error_message
