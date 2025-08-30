"""
Base class for subscenes - overlay UI elements that appear within scenes.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from client.app import ClientApp
    from client.scenes.base import BaseScene


class SubSceneType(str, Enum):
    """Available subscene types."""

    PAUSE = "pause"
    CONFIG = "config"
    INVENTORY = "inventory"
    SHOP = "shop"
    STATS = "stats"


class BaseSubScene(ABC):
    """Base class for all subscenes (overlay UI elements)."""

    def __init__(self, app: "ClientApp", parent_scene: "BaseScene") -> None:
        """
        Initialize a new subscene.

        Args:
            app: Client application instance
            parent_scene: The scene that this subscene overlays
        """
        self.app = app
        self.parent_scene = parent_scene
        self.active = False
        self.modal = True  # If True, blocks input to parent scene
        self.background_alpha = 120  # Overlay transparency (0-255)

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle events for this subscene.

        Args:
            event: pygame event to handle

        Returns:
            bool: True if event was consumed, False to pass to parent
        """
        raise NotImplementedError

    @abstractmethod
    def render(self, screen: pygame.Surface) -> None:
        """
        Render the subscene overlay.

        Args:
            screen: Surface to render on
        """
        raise NotImplementedError

    def show(self) -> None:
        """Show this subscene."""
        self.active = True

    def hide(self) -> None:
        """Hide this subscene."""
        self.active = False

    def toggle(self) -> None:
        """Toggle subscene visibility."""
        self.active = not self.active

    def _render_background_overlay(self, screen: pygame.Surface) -> None:
        """Render semi-transparent background overlay."""
        if self.modal and self.background_alpha > 0:
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, self.background_alpha))
            screen.blit(overlay, (0, 0))

    def _render_panel(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        bg_color: pygame.Color,
        border_color: pygame.Color,
        border_width: int = 3,
        border_radius: int = 10,
    ) -> None:
        """
        Render a styled panel for the subscene.

        Args:
            screen: Surface to render on
            rect: Panel rectangle
            bg_color: Background color
            border_color: Border color
            border_width: Border thickness
            border_radius: Border radius for rounded corners
        """
        # Draw background with gradient effect
        self._draw_gradient_rect(
            screen, rect, bg_color, pygame.Color(bg_color.r + 20, bg_color.g + 20, bg_color.b + 20)
        )

        # Draw border
        pygame.draw.rect(screen, border_color, rect, border_width, border_radius=border_radius)

    def _draw_gradient_rect(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        color1: pygame.Color,
        color2: pygame.Color,
    ) -> None:
        """Draw a rectangle with vertical gradient."""
        for y in range(rect.height):
            ratio = y / rect.height
            r = int(color1.r + (color2.r - color1.r) * ratio)
            g = int(color1.g + (color2.g - color1.g) * ratio)
            b = int(color1.b + (color2.b - color1.b) * ratio)
            pygame.draw.line(
                screen, (r, g, b), (rect.x, rect.y + y), (rect.x + rect.width, rect.y + y)
            )

    def _render_button(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        text: str,
        is_active: bool = False,
        is_disabled: bool = False,
        font_size: int = 20,
    ) -> None:
        """
        Render a styled button.

        Args:
            screen: Surface to render on
            rect: Button rectangle
            text: Button text
            is_active: Whether button is currently selected/focused
            is_disabled: Whether button is disabled
            font_size: Font size for button text
        """
        from core.constants import (
            ACCENT_BLUE,
            ACCENT_GREEN,
            DARK_NAVY,
            LIGHT_GRAY,
            MEDIUM_GRAY,
            WHITE,
        )

        # Determine colors based on state
        if is_disabled:
            bg_color = MEDIUM_GRAY
            text_color = LIGHT_GRAY
            border_color = LIGHT_GRAY
        elif is_active:
            bg_color = ACCENT_GREEN
            text_color = WHITE
            border_color = ACCENT_BLUE
        else:
            bg_color = DARK_NAVY
            text_color = WHITE
            border_color = ACCENT_BLUE

        # Draw button background
        pygame.draw.rect(screen, bg_color, rect, border_radius=5)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=5)

        # Draw button text
        font = pygame.font.SysFont("Arial", font_size, bold=True)
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=rect.center)
        screen.blit(text_surface, text_rect)


class SubSceneManager:
    """Manages subscenes for a parent scene."""

    def __init__(self, parent_scene: "BaseScene") -> None:
        """
        Initialize the subscene manager.

        Args:
            parent_scene: The scene that owns this manager
        """
        self.parent_scene = parent_scene
        self.subscenes: dict[SubSceneType, BaseSubScene] = {}
        self.active_subscenes: list[BaseSubScene] = []

    def register_subscene(self, subscene_type: SubSceneType, subscene: BaseSubScene) -> None:
        """
        Register a subscene.

        Args:
            subscene_type: Type of subscene
            subscene: Subscene instance
        """
        self.subscenes[subscene_type] = subscene

    def show_subscene(self, subscene_type: SubSceneType) -> None:
        """
        Show a specific subscene.

        Args:
            subscene_type: Type of subscene to show
        """
        if subscene_type in self.subscenes:
            subscene = self.subscenes[subscene_type]
            if subscene not in self.active_subscenes:
                self.active_subscenes.append(subscene)
            subscene.show()

    def hide_subscene(self, subscene_type: SubSceneType) -> None:
        """
        Hide a specific subscene.

        Args:
            subscene_type: Type of subscene to hide
        """
        if subscene_type in self.subscenes:
            subscene = self.subscenes[subscene_type]
            subscene.hide()
            if subscene in self.active_subscenes:
                self.active_subscenes.remove(subscene)

    def toggle_subscene(self, subscene_type: SubSceneType) -> None:
        """
        Toggle a specific subscene.

        Args:
            subscene_type: Type of subscene to toggle
        """
        if subscene_type in self.subscenes:
            subscene = self.subscenes[subscene_type]
            if subscene.active:
                self.hide_subscene(subscene_type)
            else:
                self.show_subscene(subscene_type)

    def hide_all(self) -> None:
        """Hide all active subscenes."""
        for subscene in self.active_subscenes.copy():
            subscene.hide()
        self.active_subscenes.clear()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle events for active subscenes.

        Args:
            event: pygame event to handle

        Returns:
            bool: True if any subscene consumed the event
        """
        # Process events in reverse order (top-most subscene first)
        for subscene in reversed(self.active_subscenes):
            if subscene.active and subscene.handle_event(event):
                return True
        return False

    def render(self, screen: pygame.Surface) -> None:
        """
        Render all active subscenes.

        Args:
            screen: Surface to render on
        """
        for subscene in self.active_subscenes:
            if subscene.active:
                subscene.render(screen)

    @property
    def has_modal_subscene(self) -> bool:
        """Check if any active subscene is modal."""
        return any(subscene.active and subscene.modal for subscene in self.active_subscenes)
