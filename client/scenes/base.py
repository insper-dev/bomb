from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from client.app import ClientApp


class BaseScene(ABC):
    """Classe base para todas as cenas do jogo."""

    def __init__(self, app: "ClientApp") -> None:
        """
        Initialize a new instance of the BaseScene class.

        Args:
            app: Client App
        """

        self.app = app
        self.next_scene: BaseScene | None = None
        self.components = []

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle events.

        Args:
            event: Event to be processed
        """
        raise NotImplementedError

    @abstractmethod
    def render(self) -> None:
        """
        Render the scene (draw on the screen).

        Args:
            app: Client App
        """
        raise NotImplementedError

    def _handle_event(self, event) -> None:
        """
        Handle events for the scene.
        """
        if event.type == pygame.QUIT:
            self.app.running = False

        self.handle_event(event)

        for components in self.components:
            components.handle_event(event)

    def _render(self) -> None:
        """
        Render the scene.
        """
        # TODO: constante de cor. THIS IS A FUCKING BLACK!
        self.app.screen.fill((0, 0, 0))

        # Render the scene
        self.render()

        # Render components
        for component in self.components:
            component.render()

        pygame.display.flip()

    def update(self) -> None:
        """Update the scene logic."""

        for event in pygame.event.get():
            self._handle_event(event)

        self._render()

    # TODO: type these functions
    def add_component(self, component: ...) -> None:
        """
        Add a component to the scene.

        Args:
            component: Component to be added
        """
        self.components.append(component)

    def remove_component(self, component: ...) -> None:
        """
        Remove a component from the scene.

        Args:
            component: Component to be removed
        """
        if component in self.components:
            self.components.remove(component)

    def _next_scene(self, scene) -> None:
        self.app.current_scene = scene


class Scenes(str, Enum):
    START = "start"
    MATCHMAKING = "matchmaking"
    GAME = "game"
    LOGIN = "login"
    MAIN_MENU = "main_menu"
    INITIAL_SCENE = "initi_scene"
