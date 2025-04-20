import pygame

from client.components import BaseComponent, TextArea
from client.scenes.base import BaseScene, Scenes
from core.constants import PURPLE


class InitialScene(BaseScene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.app.auth_service.get_current_user()
        self.active_button = 0
        self.interative_components: list[BaseComponent] = []
        self.non_interative: list[BaseComponent] = [
            TextArea(
                self.app.screen,
                position=(self.app.screen_center[0], self.app.screen_center[1] * 0.8),
                label="GeoBomber Online",
                text_type="title",
            ),
            TextArea(
                self.app.screen,
                position=(self.app.screen_center[0], self.app.screen_center[1]),
                label="Welcome to where bombs can be legally placed",
                text_type="subtitle",
                variant="primary",
                hover=False,
            ),
            TextArea(
                self.app.screen,
                position=(self.app.screen_center[0], self.app.screen_center[1] * 1.2),
                label="Click anywere or press Enter to continue",
                text_type="text",
                variant="primary",
                hover=False,
            ),
        ]
        self.components: list[BaseComponent] = self.interative_components + self.non_interative

    def render(self) -> None:
        self.app.screen.fill(PURPLE)

    def handle_event(self, event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.change_scene(Scenes.MAIN_MENU)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.change_scene(Scenes.MAIN_MENU)

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
