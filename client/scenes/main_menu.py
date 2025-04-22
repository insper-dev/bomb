import pygame

from client.components import BaseComponent, Button, State, Text
from client.scenes.base import BaseScene, Scenes


class MainMenuScene(BaseScene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.app = app
        self.app.auth_service.get_current_user()
        self.active_button = 0

        self.non_interative: list[BaseComponent] = [
            Text(
                self.app.screen,
                position=(self.app.screen_center[0], int(self.app.screen_center[1] * 0.6)),
                label="Lara Bomb Online",
                variant="standard",
                size="lg",
                text_type="title",
            ),
            Text(
                self.app.screen,
                position=(self.app.screen_center[0], int(self.app.screen_center[1] * 1.8)),
                label="Click play to sign in your account or Sign-in",
                variant="standard",
                size="lg",
                text_type="text",
            ),
        ]

        self.interative_components: list[BaseComponent] = [
            Button(
                self.app.screen,
                position=(int(self.app.screen_center[0] * 0.7), self.app.screen_center[1]),
                label="Jogar",
                variant="standard",
                size="lg",
                callback=self._handle_play_button,
            ),
            Button(
                self.app.screen,
                position=(int(self.app.screen_center[0] * 1.3), self.app.screen_center[1]),
                label="Config",
                variant="standard",
                size="lg",
                callback=lambda: setattr(self.app, "current_scene", Scenes.LOGIN),
            ),
            Button(
                self.app.screen,
                position=(
                    int(self.app.screen_center[0] * 0.7),
                    int(self.app.screen_center[1] * 1.25),
                ),
                label="Sair",
                variant="outline",
                size="lg",
                callback=lambda: setattr(self.app, "running", False),
            ),
            State(
                self.app.screen,
                position=(
                    int(self.app.screen_center[0] * 1.3),
                    int(self.app.screen_center[1] * 1.25),
                ),
                label="Logout",
                variant="outline",
                size="lg",
                callback=lambda: self.app.auth_service.logout(),
            ),
        ]

        self.components = self.interative_components + self.non_interative
        self.app.auth_service.register_logout_callback(self._on_logout)

    def _handle_play_button(self) -> None:
        """Handle play button logic - redirect to login or matchmaking based on auth status"""
        if self.app.auth_service.is_logged_in:
            self.app.current_scene = Scenes.MATCHMAKING
        else:
            self.app.current_scene = Scenes.LOGIN

    def handle_event(self, event: pygame.event.Event) -> None:
        self.changing_focus(event)

    def render(self) -> None:
        self.app.screen.fill((1, 5, 68))

        if self.app.auth_service.is_logged_in and (user := self.app.auth_service.current_user):
            self.interative_components[3].is_disabled = False
            self.non_interative[1].label = f"Welcome: {user.username}"
        else:
            self.interative_components[3].is_disabled = True
            self.non_interative[1].label = "Click play to sign in your account or Sign-in"

        # FIXME: "active" is not an attribute of BaseComponent.
        if self.interative_components[3].active:
            self.interative_components[3].is_disabled = True

    def changing_focus(self, event: pygame.event.Event) -> None:
        """
        Change the focus of the button.
        """
        movement = {pygame.K_UP: -2, pygame.K_DOWN: 2, pygame.K_LEFT: -1, pygame.K_RIGHT: 1}

        if event.type == pygame.KEYDOWN and event.key in movement:
            # Update active button index
            offset = movement[event.key]
            self.active_button = (self.active_button + offset) % len(self.interative_components)

            # Update focus state for all components
            for i, component in enumerate(self.interative_components):
                component.is_focused = i == self.active_button

    def _on_logout(self) -> None:
        """
        Executed when the player logs out
        """
        # FIXME: "active" is not an attribute of BaseComponent.
        self.interative_components[3].active = False
