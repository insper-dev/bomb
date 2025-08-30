"""
Pause subscene for pausing gameplay and accessing options.
"""

import pygame

from core.constants import (
    ACCENT_BLUE,
    DARK_NAVY,
    LIGHT_GRAY,
    WHITE,
)

from .base import BaseSubScene, SubSceneType


class PauseSubScene(BaseSubScene):
    """Pause menu subscene that overlays the game."""

    def __init__(self, app, parent_scene) -> None:
        super().__init__(app, parent_scene)

        self.modal = True
        self.background_alpha = 180

        # Menu options
        self.options = [
            {"text": "Continuar", "action": self._resume_game},
            {"text": "Configurações", "action": self._open_config},
            {"text": "Sair do Jogo", "action": self._exit_game},
        ]

        self.active_option = 0

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle pause menu events."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._resume_game()
                return True

            elif event.key == pygame.K_UP:
                self.active_option = (self.active_option - 1) % len(self.options)
                return True

            elif event.key == pygame.K_DOWN:
                self.active_option = (self.active_option + 1) % len(self.options)
                return True

            elif event.key == pygame.K_RETURN:
                self.options[self.active_option]["action"]()
                return True

        return False

    def render(self, screen: pygame.Surface) -> None:
        """Render the pause menu overlay."""
        if not self.active:
            return

        # Semi-transparent background
        self._render_background_overlay(screen)

        screen_w, screen_h = screen.get_size()

        # Menu panel
        menu_width = 400
        menu_height = 300
        menu_x = (screen_w - menu_width) // 2
        menu_y = (screen_h - menu_height) // 2
        menu_rect = pygame.Rect(menu_x, menu_y, menu_width, menu_height)

        self._render_panel(screen, menu_rect, DARK_NAVY, ACCENT_BLUE)

        # Title
        title_font = pygame.font.SysFont("Arial", 36, bold=True)
        title_text = title_font.render("JOGO PAUSADO", True, WHITE)
        title_rect = title_text.get_rect(center=(screen_w // 2, menu_y + 60))
        screen.blit(title_text, title_rect)

        # Menu options
        start_y = menu_y + 120
        option_spacing = 60

        for i, option in enumerate(self.options):
            is_active = i == self.active_option
            y = start_y + i * option_spacing

            # Option background
            option_rect = pygame.Rect(menu_x + 50, y - 15, menu_width - 100, 45)

            self._render_button(screen, option_rect, option["text"], is_active, font_size=24)

        # Instructions
        instructions_font = pygame.font.SysFont("Arial", 16)
        instructions = [
            "↑↓: Navegar",
            "ENTER: Selecionar",
            "ESC: Voltar ao jogo",
        ]

        for i, instruction in enumerate(instructions):
            inst_text = instructions_font.render(instruction, True, LIGHT_GRAY)
            center_y = menu_y + menu_height + 60 + i * 20
            inst_rect = inst_text.get_rect(center=(screen_w // 2, center_y))
            screen.blit(inst_text, inst_rect)

    def show(self) -> None:
        """Show pause menu and pause game audio."""
        super().show()
        try:
            pygame.mixer.music.pause()
        except pygame.error:
            pass  # Ignore if no music is playing

    def hide(self) -> None:
        """Hide pause menu and resume game audio."""
        super().hide()
        try:
            pygame.mixer.music.unpause()
        except pygame.error:
            pass  # Ignore if no music is playing

    def _resume_game(self) -> None:
        """Resume the game."""
        self.hide()
        # If parent scene has subscene manager, hide this subscene
        if hasattr(self.parent_scene, "subscene_manager"):
            self.parent_scene.subscene_manager.hide_subscene(SubSceneType.PAUSE)

    def _open_config(self) -> None:
        """Open config subscene."""
        # Hide pause menu and show config
        if hasattr(self.parent_scene, "subscene_manager"):
            self.parent_scene.subscene_manager.hide_subscene(SubSceneType.PAUSE)
            self.parent_scene.subscene_manager.show_subscene(SubSceneType.CONFIG)

    def _exit_game(self) -> None:
        """Exit to main menu."""
        # Stop game service if available
        if hasattr(self.app, "game_service") and self.app.game_service.running:
            self.app.game_service.exit_game()

        # Return to main menu
        from client.scenes.base import Scenes

        self.app.current_scene = Scenes.START
