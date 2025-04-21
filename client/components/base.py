from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Literal

import pygame

from core.constants import FONT_MAP, FONT_SIZE_MAP, SIZE_MAP, VARIANT_MAP
from core.types import (
    ComponentSize,
    ComponentType,
    ComponentVariant,
    Coordinate,
    FontSize,
    FontStyle,
    Thickness,
)


class BaseComponent(ABC):
    """
    Abstract base class for all components.
    """

    def __init__(
        self,
        window: pygame.Surface,
        position: Coordinate,
        label: str,
        variant: ComponentVariant = "standard",
        size: ComponentSize = "md",
        text_type: FontSize = "standard",
        hover: bool = True,
        is_topleft: bool = False,
        *,
        callback: Callable = lambda: print("Button clicked!"),
    ) -> None:
        """
        Initialize the component.

        Args:
            window (pygame.Surface): The window where the component will be drawn.
            position (Coordinate): The position of the component.
            variant (str): The variant of the component.
            size (str): The size of the component.
            callback (Callable): A callback function to be executed on click.
        """
        self.label = label
        self.window = window
        self.position = position
        self.variant: ComponentVariant = variant
        self.size: ComponentSize = size
        self.text_type: FontSize = text_type
        self.hover = hover
        self.callback = callback
        self.is_topleft = is_topleft
        self.is_focused = False
        self.is_disabled = False
        # ! Warning: ter cuidado com a poha do nome da classe!!!
        # ! Se por acaso mudar o nome da classe, precisa mudar o "ComponentType"
        self.type: ComponentType = self.__class__.__name__.lower()  # type: ignore
        self.surface = self._init_surface()
        self.rect = (
            self.surface.get_rect(topleft=position)
            if is_topleft
            else self.surface.get_rect(center=position)
        )

    @abstractmethod
    def _init_surface(self) -> pygame.Surface:
        """
        Initialize the surface of the component.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def _create_surface(self, size) -> pygame.Surface:
        """
        Create the surface of the component's part.
        """
        return pygame.surface.Surface(size, flags=pygame.SRCALPHA)

    def _get_color(self, surface_part: Literal["bg", "text", "border"]) -> pygame.Color:
        """
        Get the color of the component based on its part.
        """
        colors = VARIANT_MAP[self.is_disabled][self.is_focused]

        return colors[self.variant][surface_part]

    def _get_font(self, font_style: FontStyle | None = None) -> pygame.font.Font:
        """
        Get the font of the component.
        """
        font_size = FONT_SIZE_MAP[self.is_focused][self.text_type][self.size]
        font = FONT_MAP[font_style] if font_style else None

        return pygame.font.Font(font, font_size)

    def _get_size(self) -> tuple[Coordinate, Thickness]:
        """
        Get the size of the component.
        """
        sizes = SIZE_MAP[self.is_focused][self.type]

        return sizes[self.size]

    def _handle_hover(self, event) -> None:
        if event.type == pygame.MOUSEMOTION and self.hover:
            if self.rect.collidepoint(event.pos):
                self.is_focused = True
            else:
                self.is_focused = False

    def _handle_click(self, event) -> None:
        """
        Handle click events for the component.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self._callback()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and self.is_focused:
                self._callback()

    def _handle_event(self, event: pygame.event.Event) -> None:
        ...
        return

    def _render(self) -> None:
        ...
        return

    def _callback(self) -> None:
        self.callback()

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle events for the component.
        """
        if self.is_disabled:
            return
        self._handle_event(event)
        self._handle_hover(event)
        self._handle_click(event)

    def render(self) -> None:
        """
        Render the component.
        """
        self._render()
        self.surface = self._init_surface()
        self.rect = (
            self.surface.get_rect(topleft=(self.position))
            if self.is_topleft
            else self.surface.get_rect(center=(self.position))
        )
        self.window.blit(self.surface, self.rect)
