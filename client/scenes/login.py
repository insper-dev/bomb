import pygame

from client.components import Button, Input, State, Text
from client.scenes.base import BaseScene, Scenes
from core.constants import BLACK

# !! TODO: REFATORAR A BASE COMPONENT PARA FAZER VALIDAÇÃO DOS ATRIBUTOS


class LoginScene(BaseScene):
    """Scene for user authentication (login and signup)"""

    def __init__(self, app) -> None:
        super().__init__(app)

        # State
        self.active_field = "username"  # Current input field: username or password
        self.is_signup_mode = False  # Toggle between login and signup
        self.error_message = ""
        self.inputs = [
            Input(
                self.app.screen,
                position=(
                    int(self.app.screen_center[0] * 0.5),
                    int(self.app.screen_center[1] * 0.8),
                ),
                label=r"Username\h",
                text_type="text",
                is_topleft=True,
                callback=lambda: self._submit(),
            ),
            Input(
                self.app.screen,
                position=(
                    int(self.app.screen_center[0] * 0.5),
                    int(self.app.screen_center[1] * 1.2),
                ),
                label=r"Password\h",
                text_type="text",
                is_topleft=True,
                callback=lambda: self._submit(),
            ),
        ]

        self.buttons = [
            Button(
                self.app.screen,
                position=(
                    int(self.app.screen_center[0] * 0.1),
                    int(self.app.screen_center[1] * 1.85),
                ),
                label="back",
                text_type="standard",
                variant="outline",
                size="sm",
                is_topleft=True,
                callback=lambda: setattr(self.app, "current_scene", Scenes.MAIN_MENU),
            ),
            Button(
                self.app.screen,
                position=(
                    int(self.app.screen_center[0] * 1.62),
                    int(self.app.screen_center[1] * 1.85),
                ),
                label="Cadastrar Conta",
                text_type="standard",
                variant="outline",
                size="sm",
                is_topleft=True,
                callback=lambda: self.authentication_change(),
            ),
        ]

        self.loading_state = State(
            self.app.screen,
            position=(
                int(self.app.screen_center[0] * 0.5),
                int(self.app.screen_center[1] * 1.45),
            ),
            label="Enviar",
            text_type="standard",
            is_topleft=True,
            callback=lambda: self._submit(),
        )

        self.texts = [
            Text(
                self.app.screen,
                position=(self.app.screen_center[0], int(self.app.screen_center[1] * 0.35)),
                label="Login",
                text_type="title",
                hover=False,
            ),
            Text(
                self.app.screen,
                position=(
                    int(self.app.screen_center[0] * 0.5),
                    int(self.app.screen_center[1] * 0.65),
                ),
                label="Usuário",
                text_type="subtitle",
                hover=False,
                is_topleft=True,
            ),
            Text(
                self.app.screen,
                position=(
                    int(self.app.screen_center[0] * 0.5),
                    int(self.app.screen_center[1] * 1.05),
                ),
                label="Senha",
                text_type="subtitle",
                hover=False,
                is_topleft=True,
            ),
            Text(
                self.app.screen,
                position=(self.app.screen_center[0], int(self.app.screen_center[1] * 1.7)),
                label="",
                text_type="text",
                hover=False,
            ),
        ]

        self.components = [*self.inputs, *self.buttons, *self.texts, self.loading_state]

        # Setup auth callbacks
        self.app.auth_service.register_login_success_callback(self._on_login_success)
        self.app.auth_service.register_login_error_callback(self._on_login_error)

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            keys = {
                pygame.K_LEFT: "left",
                pygame.K_RIGHT: "right",
                pygame.K_TAB: "tab",
            }
            if event.key in keys:
                for component in self.components:
                    if isinstance(component, Input) and keys[event.key] != "tab":
                        component.active = False
                    component.is_focused = False
                if self.inputs[0].active or self.inputs[1].active:
                    self.inputs[0].active = not self.inputs[0].active
                    self.inputs[1].active = not self.inputs[1].active
                elif keys[event.key] == "tab":
                    self.inputs[0].active = not self.inputs[0].active
                else:
                    index = 1 if keys[event.key] == "right" else 0
                    self.buttons[index].is_focused = True

    def render(self) -> None:
        # Background
        self.app.screen.fill(BLACK)

        self.loading_state.active = (
            self.app.auth_service.is_login_loading or self.app.auth_service.is_signup_loading
        )

        if self.error_message:
            self.texts[-1].label = self.error_message
            self.loading_state.active = False
        else:
            self.texts[-1].label = ""

    def update(self) -> None:
        # Check for auth service errors
        if not self.is_signup_mode:
            error = self.app.auth_service.get_login_error()
            if error:
                self.error_message = error
        else:
            error = self.app.auth_service.get_signup_error()
            if error:
                self.error_message = error

        if self.loading_state.active:
            self.loading_state.is_disabled = True

        # Call parent update to handle events
        super().update()

    def _submit(self) -> None:
        self.loading_state.active = True

        # Validate input
        if not self.inputs[0].value:
            self.error_message = "Username cannot be empty"
            return

        if not self.inputs[1].value:
            self.error_message = "Password cannot be empty"
            return

        if len(self.inputs[1].value) < 6:
            self.error_message = "Password must be at least 6 characters"
            return

        self.error_message = ""

        # Submit based on mode
        if self.is_signup_mode:
            self.app.auth_service.signup(self.inputs[0].value, self.inputs[1].value)
        else:
            self.app.auth_service.login(self.inputs[0].value, self.inputs[1].value)

    def _on_login_success(self, token: str) -> None:
        """Called when login/signup is successful"""
        self.app.current_scene = Scenes.MAIN_MENU

    def _on_login_error(self, error_message: str) -> None:
        """Called when login/signup fails"""

        self.error_message = error_message
        self.loading_state.is_disabled = False

    def authentication_change(self) -> None:
        self.is_signup_mode = not self.is_signup_mode
        self.buttons[1].label = "Login" if self.is_signup_mode else "Sign-up"
        self.texts[0].label = "Cadastro" if self.is_signup_mode else "Login"
