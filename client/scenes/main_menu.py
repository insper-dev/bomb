import pygame

from client.components import BaseComponent, Button, State, TextArea
from client.scenes.base import BaseScene, Scenes


class MainMenu(BaseScene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.app = app
        self.app.auth_service.get_current_user()
        self.once = True
        self.active_button = 0
        self.non_interative: list[BaseComponent] = [
            TextArea(
                self.app.screen,
                position=(self.app.screen_center[0], self.app.screen_center[1] * 0.6),
                label="BombDuni",
                variant="standard",
                size="lg",
                text_type="title",
            ),
            TextArea(
                self.app.screen,
                position=(self.app.screen_center[0], self.app.screen_center[1] * 1.8),
                label="Click play to sing in your account or Sing-in",
                variant="standard",
                size="lg",
                text_type="text",
            ),
        ]
        self.interative_components: list[BaseComponent] = [
            Button(
                self.app.screen,
                position=(self.app.screen_center[0] * 0.7, self.app.screen_center[1]),
                label="Jogar",
                variant="standard",
                size="lg",
                callback=lambda: self.change_scene(
                    Scenes.LOGIN,
                    (self.app.auth_service.is_logged_in, Scenes.MATCHMAKING),
                    self.__getattribute__(),
                ),
            ),
            Button(
                self.app.screen,
                position=(self.app.screen_center[0] * 1.3, self.app.screen_center[1]),
                label="Config",
                variant="standard",
                size="lg",
                callback=lambda: self.change_scene(),
            ),
            Button(
                self.app.screen,
                position=(self.app.screen_center[0] * 0.7, self.app.screen_center[1] * 1.25),
                label="Sair",
                variant="outline",
                size="lg",
                callback=lambda: pygame.quit(),
            ),
            State(
                self.app.screen,
                position=(self.app.screen_center[0] * 1.3, self.app.screen_center[1] * 1.25),
                label="Logout",
                variant="outline",
                size="lg",
                callback=lambda: self.app.auth_service.logout(),
            ),
        ]
        self.components = self.interative_components + self.non_interative
        self.app.auth_service.register_logout_callback(self._on_logout)

    def handle_event(self, event: pygame.event.Event) -> None:
        # Changing the focus of the button
        self.changing_focus(event)

    def render(self) -> None:
        self.app.screen.fill((1, 5, 68))
        if self.app.auth_service.is_logged_in:
            if self.once:
                self.once = False
                self.interative_components[3].is_dissabled = False
                self.components[0].callback = lambda: self.change_scene(Scenes.MATCHMAKING)
            self.app.auth_service.get_current_user()
            self.non_interative[1].label = "Welcome: " + self.app.auth_service.current_user.username
        else:
            self.interative_components[3].is_dissabled = True
            self.non_interative[1].label = "Click play to sing in your account or Sing-in"
            self.components[0].callback = lambda: self.change_scene(Scenes.LOGIN)

        if self.interative_components[3].active:
            self.interative_components[3].is_dissabled = True

    def changing_focus(self, event: pygame.event.Event) -> None:
        """
        Change the focus of the button.
        """
        moviment = {pygame.K_UP: -2, pygame.K_DOWN: 2, pygame.K_LEFT: -1, pygame.K_RIGHT: 1}
        if event.type == pygame.KEYDOWN:
            if event.key in moviment:
                self.active_button = (self.active_button + moviment[event.key]) % len(
                    self.interative_components
                )
                for i, component in enumerate(self.interative_components):
                    component.is_focused = i == self.active_button

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

    def _on_logout(self) -> None:
        """
        Is executed when the player logout
        """
        self.interative_components[3].active = False
