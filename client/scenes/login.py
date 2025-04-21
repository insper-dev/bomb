import pygame
import pygame.font

from client.components import BaseComponent, Button, Input, State, TextArea
from client.scenes.base import BaseScene, Scenes
from core.constants import BLACK


class LoginScene(BaseScene):
    """Scene for user authentication (login and signup)"""

    def __init__(self, app) -> None:
        super().__init__(app)

        # State
        self.active_field = "username"  # Current input field: username or password
        self.is_signup_mode = False  # Toggle between login and signup
        self.show_error = False
        self.error_message = ""
        self.interative_components: list[BaseComponent] = [
            Input(
                self.app.screen,
                position=(self.app.screen_center[0] * 0.5, self.app.screen_center[1] * 0.8),
                label=r"Username\h",
                text_type="text",
                is_topleft=True,
                callback=lambda: self._submit(),
            ),
            Input(
                self.app.screen,
                position=(self.app.screen_center[0] * 0.5, self.app.screen_center[1] * 1.2),
                label=r"Password\h",
                text_type="text",
                is_topleft=True,
                callback=lambda: self._submit(),
            ),
            State(
                self.app.screen,
                position=(self.app.screen_center[0] * 0.5, self.app.screen_center[1] * 1.45),
                label="Submit",
                text_type="standard",
                is_topleft=True,
                callback=lambda: self._submit(),
            ),
            Button(
                self.app.screen,
                position=(self.app.screen_center[0] * 0.1, self.app.screen_center[1] * 1.85),
                label="back",
                text_type="standard",
                variant="outline",
                size="sm",
                is_topleft=True,
                callback=lambda: self.change_scene(Scenes.MAIN_MENU),
            ),
            Button(
                self.app.screen,
                position=(self.app.screen_center[0] * 1.62, self.app.screen_center[1] * 1.85),
                label="Sing-in",
                text_type="standard",
                variant="outline",
                size="sm",
                is_topleft=True,
                callback=lambda: self.authentication_change(),
            ),
        ]
        self.non_interative: list[BaseComponent] = [
            TextArea(
                self.app.screen,
                position=(self.app.screen_center[0], self.app.screen_center[1] * 0.35),
                label="Login",
                text_type="title",
                hover=False,
            ),
            TextArea(
                self.app.screen,
                position=(self.app.screen_center[0] * 0.5, self.app.screen_center[1] * 0.65),
                label="Username",
                text_type="subtitle",
                hover=False,
                is_topleft=True,
            ),
            TextArea(
                self.app.screen,
                position=(self.app.screen_center[0] * 0.5, self.app.screen_center[1] * 1.05),
                label="Password",
                text_type="subtitle",
                hover=False,
                is_topleft=True,
            ),
            TextArea(
                self.app.screen,
                position=(self.app.screen_center[0], self.app.screen_center[1] * 1.7),
                label="",
                text_type="text",
                hover=False,
            ),
        ]
        self.components: list[BaseComponent] = self.interative_components + self.non_interative
        self.buttons_index = 0

        # Setup auth callbacks
        self.app.auth_service.register_login_success_callback(self._on_login_success)
        self.app.auth_service.register_login_error_callback(self._on_login_error)

    def handle_event(self, event) -> None:
        if event.type == pygame.QUIT:
            self.app.running = False

        elif event.type == pygame.KEYDOWN:
            inputs: list[Input] = [self.interative_components[0], self.interative_components[1]]
            buttons: list[Button] = [self.interative_components[3], self.interative_components[4]]
            keys: dict[pygame.event.EventType : int] = {
                pygame.K_LEFT: "left",
                pygame.K_RIGHT: "right",
                pygame.K_TAB: "tab",
            }
            if event.key in keys:
                for component in self.components:
                    if isinstance(component, Input) and keys[event.key] != "tab":
                        component.active = False
                        component.is_focused = False
                    else:
                        component.is_focused = False
                if inputs[0].active or inputs[1].active:
                    inputs[0].active = not inputs[0].active
                    inputs[1].active = not inputs[1].active
                elif keys[event.key] == "tab":
                    inputs[0].active = not inputs[0].active
                else:
                    index = 1 if keys[event.key] == "right" else 0
                    buttons[index].is_focused = True

    def render(self) -> None:
        # Background
        self.app.screen.fill(BLACK)

        # Loading indicator
        is_loading = (
            self.app.auth_service.is_login_loading or self.app.auth_service.is_signup_loading
        )
        if is_loading:
            self.interative_components[2].active = True

        if self.show_error:
            self.non_interative[-1].label = self.error_message
            self.interative_components[2].active = False
        else:
            self.non_interative[-1].label = ""

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

        if self.components[2].active:
            self.components[2].is_dissabled = True

        # Call parent update to handle events
        super().update()

    def _submit(self) -> None:
        # Clear previous errors
        self.interative_components[2].active = True

        self.show_error = False
        self.error_message = ""

        # Validate input
        if not self.components[0].value:
            self.show_error = True
            self.error_message = "Username cannot be empty"
            return

        if not self.components[1].value:
            self.show_error = True
            self.error_message = "Password cannot be empty"
            return

        if len(self.components[1].value) < 6:
            self.show_error = True
            self.error_message = "Password must be at least 6 characters"
            return

        self.error_message = ""

        # Submit based on mode
        if self.is_signup_mode:
            self.app.auth_service.signup(self.components[0].value, self.components[1].value)
        else:
            self.app.auth_service.login(self.components[0].value, self.components[1].value)

    def _on_login_success(self, token: str) -> None:
        """Called when login/signup is successful"""
        # Redirect to the main menu

        if self.app.auth_service.is_logged_in:
            self.app.current_scene = Scenes.MAIN_MENU
        self.interative_components[2].is_dissabled = False

    def _on_login_error(self, error_message: str) -> None:
        """Called when login/signup fails"""
        self.show_error = True
        self.error_message = error_message
        self.components[2].is_dissabled = False

    def change_scene(
        self,
        scene: BaseScene,
        alt_scene_conditioned: tuple[bool | None, BaseScene] = (None, BaseScene),
    ) -> None:
        condition, alt_scene = alt_scene_conditioned
        if alt_scene is None:
            self.app.current_scene = scene
        else:
            self.app.current_scene = alt_scene if condition else scene

    def authentication_change(self) -> None:
        self.is_signup_mode = not self.is_signup_mode
        self.interative_components[4].label = "Login" if self.is_signup_mode else "Sing-In"
        self.non_interative[0].label = "Sing-In" if self.is_signup_mode else "Login"
