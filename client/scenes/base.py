from abc import ABC, abstractmethod
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

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Process Pygame events.

        Args:
            event: Event to be processed
        """
        # delegate event handling to components
        for component in self.components:
            if hasattr(component, "handle_event"):
                component.handle_event(event)

    # TODO: this approach is temporary until is define the logic sytax for the "scene components"
    @abstractmethod
    def update(self) -> None:
        """Update the scene logic."""
        # The idea os this function is to delagate the update process to the scene components
        # That means that it dont need to be overrided by child classes

        # TODO: use the self.app defined to change the global state / current_scene.
        for component in self.components:
            if hasattr(component, "update"):
                component.update()

        # Verifica se deve mudar para próxima cena
        if self.next_scene:
            # TODO: implement the change scen process
            # self.app.change_scene(self.next_scene)
            self.next_scene = None

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
