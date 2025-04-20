import pygame

from client.components import BaseComponent, TextArea
from client.scenes.base import BaseScene, Scenes
from core.constants import PURPLE


class InitialScene(BaseScene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.app.auth_service.get_current_user()
        self._setup_components()

    def _setup_components(self) -> None:
        """Initialize and setup all scene components."""
        self.interactive_components: list[BaseComponent] = []

        title_y = int(self.app.screen_center[1] * 0.8)
        subtitle_y = self.app.screen_center[1]
        instruction_y = int(self.app.screen_center[1] * 1.2)

        self.non_interactive: list[BaseComponent] = [
            TextArea(
                self.app.screen,
                position=(self.app.screen_center[0], title_y),
                label="LaraBomb Online",
                text_type="title",
            ),
            TextArea(
                self.app.screen,
                position=(self.app.screen_center[0], subtitle_y),
                label="Welcome to where bombs can be legally placed",
                text_type="subtitle",
                variant="primary",
                hover=False,
            ),
            TextArea(
                self.app.screen,
                position=(self.app.screen_center[0], instruction_y),
                label="Click anywhere or press Enter to continue",
                text_type="text",
                variant="primary",
                hover=False,
            ),
        ]

        self.components = self.interactive_components + self.non_interactive

    def render(self) -> None:
        """Render the scene background."""
        self.app.screen.fill(PURPLE)

    def handle_event(self, event) -> None:
        """Handle user input events."""
        if event.type == pygame.MOUSEBUTTONDOWN or (
            event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN
        ):
            self.app.current_scene = Scenes.MAIN_MENU
