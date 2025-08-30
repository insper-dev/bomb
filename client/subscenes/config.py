"""
Config subscene for in-game configuration without leaving the scene.
"""

import json
from pathlib import Path
from typing import Any

import pygame

from client.config_manager import config_manager
from core.constants import (
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_RED,
    DARK_NAVY,
    LIGHT_GRAY,
    MEDIUM_GRAY,
    WHITE,
)

from .base import BaseSubScene, SubSceneType


class ConfigSubScene(BaseSubScene):
    """Configuration subscene that overlays the current scene."""

    def __init__(self, app, parent_scene) -> None:
        super().__init__(app, parent_scene)

        self.modal = True
        self.background_alpha = 160

        # Configuration file path
        self.config_file = Path("client_config.json")

        # Current configuration
        self.config = self._load_config()

        # UI state
        self.active_section = 0  # 0: Audio, 1: Keys
        self.active_option = 0
        self.waiting_for_key = False
        self.waiting_for_action = None

        # Audio settings
        self.audio_options = [
            {
                "name": "Master Volume",
                "key": "master_volume",
                "type": "slider",
                "min": 0,
                "max": 100,
            },
            {"name": "Music Volume", "key": "music_volume", "type": "slider", "min": 0, "max": 100},
            {"name": "SFX Volume", "key": "sfx_volume", "type": "slider", "min": 0, "max": 100},
        ]

        # Key bindings
        self.key_bindings = [
            {"name": "Move Up", "action": "move_up", "default": [pygame.K_UP, pygame.K_w]},
            {"name": "Move Down", "action": "move_down", "default": [pygame.K_DOWN, pygame.K_s]},
            {"name": "Move Left", "action": "move_left", "default": [pygame.K_LEFT, pygame.K_a]},
            {"name": "Move Right", "action": "move_right", "default": [pygame.K_RIGHT, pygame.K_d]},
            {"name": "Place Bomb", "action": "place_bomb", "default": [pygame.K_SPACE]},
            {"name": "Pause/Menu", "action": "pause", "default": [pygame.K_ESCAPE]},
        ]

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from file or create default."""
        default_config = {
            "master_volume": 70,
            "music_volume": 60,
            "sfx_volume": 80,
            "key_bindings": {
                "move_up": [pygame.K_UP, pygame.K_w],
                "move_down": [pygame.K_DOWN, pygame.K_s],
                "move_left": [pygame.K_LEFT, pygame.K_a],
                "move_right": [pygame.K_RIGHT, pygame.K_d],
                "place_bomb": [pygame.K_SPACE],
                "pause": [pygame.K_ESCAPE],
            },
        }

        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    for key, value in default_config.items():
                        if key not in loaded_config:
                            loaded_config[key] = value
                    return loaded_config
            except (json.JSONDecodeError, OSError):
                pass

        return default_config

    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
            print("[CONFIG] Settings saved successfully")
        except OSError as e:
            print(f"[CONFIG] Failed to save settings: {e}")

    def _apply_audio_settings(self) -> None:
        """Apply audio settings to pygame mixer."""
        master_vol = self.config["master_volume"] / 100.0
        music_vol = self.config["music_volume"] / 100.0

        # Apply master volume to music
        try:
            pygame.mixer.music.set_volume(master_vol * music_vol)
        except pygame.error:
            pass  # Ignore if no music is loaded

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle config menu events."""
        if self.waiting_for_key and event.type == pygame.KEYDOWN:
            self._handle_key_binding(event.key)
            return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._close_config()
                return True

            elif event.key == pygame.K_TAB:
                # Switch between Audio and Keys sections
                self.active_section = (self.active_section + 1) % 2
                self.active_option = 0
                return True

            elif event.key == pygame.K_UP:
                if self.active_section == 0:  # Audio
                    self.active_option = (self.active_option - 1) % len(self.audio_options)
                else:  # Keys
                    self.active_option = (self.active_option - 1) % len(self.key_bindings)
                return True

            elif event.key == pygame.K_DOWN:
                if self.active_section == 0:  # Audio
                    self.active_option = (self.active_option + 1) % len(self.audio_options)
                else:  # Keys
                    self.active_option = (self.active_option + 1) % len(self.key_bindings)
                return True

            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                if self.active_section == 0:  # Audio sliders
                    self._handle_audio_adjustment(event.key == pygame.K_RIGHT)
                return True

            elif event.key == pygame.K_RETURN:
                if self.active_section == 1:  # Key bindings
                    self._start_key_binding()
                return True

        return False

    def render(self, screen: pygame.Surface) -> None:
        """Render the config menu overlay."""
        if not self.active:
            return

        # Semi-transparent background
        self._render_background_overlay(screen)

        screen_w, screen_h = screen.get_size()

        # Main panel
        panel_width = 600
        panel_height = 500
        panel_x = (screen_w - panel_width) // 2
        panel_y = (screen_h - panel_height) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        self._render_panel(screen, panel_rect, DARK_NAVY, ACCENT_BLUE)

        # Title
        title_font = pygame.font.SysFont("Arial", 32, bold=True)
        title_text = title_font.render("CONFIGURAÇÕES", True, WHITE)
        title_rect = title_text.get_rect(center=(screen_w // 2, panel_y + 40))
        screen.blit(title_text, title_rect)

        # Tabs
        self._render_tabs(screen, panel_x, panel_y + 80, panel_width)

        # Content
        content_y = panel_y + 140
        if self.active_section == 0:
            self._render_audio_settings(screen, panel_x, content_y, panel_width)
        else:
            self._render_key_settings(screen, panel_x, content_y, panel_width)

        # Instructions
        self._render_instructions(screen, panel_x, panel_y + panel_height - 60, panel_width)

    def _render_tabs(self, screen: pygame.Surface, x: int, y: int, width: int) -> None:
        """Render section tabs."""
        tabs = ["ÁUDIO", "CONTROLES"]
        tab_width = width // 2 - 20

        for i, tab_name in enumerate(tabs):
            tab_x = x + 20 + (i * (tab_width + 20))
            tab_rect = pygame.Rect(tab_x, y, tab_width, 40)

            is_active = i == self.active_section
            self._render_button(screen, tab_rect, tab_name, is_active, font_size=18)

    def _render_audio_settings(self, screen: pygame.Surface, x: int, y: int, width: int) -> None:
        """Render audio configuration options."""
        for i, option in enumerate(self.audio_options):
            option_y = y + (i * 80)
            is_active = i == self.active_option

            # Option name
            font = pygame.font.SysFont("Arial", 22, bold=is_active)
            color = ACCENT_GREEN if is_active else WHITE
            name_surface = font.render(option["name"], True, color)
            screen.blit(name_surface, (x + 40, option_y))

            # Slider
            self._render_slider(x + 250, option_y + 10, 200, option, is_active)

    def _render_slider(self, x: int, y: int, width: int, option: dict, is_active: bool) -> None:
        """Render audio slider."""
        value = self.config[option["key"]]
        percentage = (value - option["min"]) / (option["max"] - option["min"])

        # Slider track
        track_rect = pygame.Rect(x, y, width, 8)
        pygame.draw.rect(self.app.screen, MEDIUM_GRAY, track_rect, border_radius=4)

        # Slider fill
        fill_width = int(width * percentage)
        if fill_width > 0:
            fill_rect = pygame.Rect(x, y, fill_width, 8)
            fill_color = ACCENT_GREEN if is_active else ACCENT_BLUE
            pygame.draw.rect(self.app.screen, fill_color, fill_rect, border_radius=4)

        # Slider handle
        handle_x = x + int(width * percentage) - 6
        handle_rect = pygame.Rect(handle_x, y - 4, 12, 16)
        handle_color = WHITE if is_active else LIGHT_GRAY
        pygame.draw.rect(self.app.screen, handle_color, handle_rect, border_radius=6)

        # Value text
        font = pygame.font.SysFont("Arial", 18)
        value_text = f"{value}%"
        value_surface = font.render(value_text, True, WHITE)
        self.app.screen.blit(value_surface, (x + width + 20, y - 5))

    def _render_key_settings(self, screen: pygame.Surface, x: int, y: int, width: int) -> None:
        """Render key binding configuration."""
        for i, binding in enumerate(self.key_bindings):
            option_y = y + (i * 55)
            is_active = i == self.active_option

            # Action name
            font = pygame.font.SysFont("Arial", 20, bold=is_active)
            color = ACCENT_GREEN if is_active else WHITE
            name_surface = font.render(binding["name"], True, color)
            screen.blit(name_surface, (x + 40, option_y))

            # Key display
            self._render_key_binding(x + 250, option_y, binding, is_active)

    def _render_key_binding(self, x: int, y: int, binding: dict, is_active: bool) -> None:
        """Render individual key binding."""
        action = binding["action"]
        keys = self.config["key_bindings"].get(action, binding["default"])

        if self.waiting_for_key and self.waiting_for_action == action:
            # Show waiting state
            text = "Pressione uma tecla..."
            color = ACCENT_RED
            bg_color = (50, 20, 20)
        else:
            # Show current keys
            key_names = [pygame.key.name(key).upper() for key in keys[:2]]  # Show max 2 keys
            text = " / ".join(key_names)
            color = ACCENT_GREEN if is_active else WHITE
            bg_color = (20, 40, 20) if is_active else DARK_NAVY

        # Key box
        font = pygame.font.SysFont("Arial", 16, bold=True)
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect()

        box_rect = pygame.Rect(x, y - 5, max(180, text_rect.width + 20), 30)
        border_color = ACCENT_GREEN if is_active else MEDIUM_GRAY

        pygame.draw.rect(self.app.screen, bg_color, box_rect, border_radius=5)
        pygame.draw.rect(self.app.screen, border_color, box_rect, 2, border_radius=5)

        # Center text in box
        text_pos = (
            box_rect.centerx - text_rect.width // 2,
            box_rect.centery - text_rect.height // 2,
        )
        self.app.screen.blit(text_surface, text_pos)

    def _render_instructions(self, screen: pygame.Surface, x: int, y: int, width: int) -> None:
        """Render control instructions."""
        instructions = [
            "TAB: Alternar seções  |  ↑↓: Navegar  |  ←→: Ajustar volume",
            "ENTER: Alterar tecla  |  ESC: Fechar e salvar",
        ]

        font = pygame.font.SysFont("Arial", 14)
        for i, instruction in enumerate(instructions):
            text_surface = font.render(instruction, True, LIGHT_GRAY)
            text_rect = text_surface.get_rect(center=(x + width // 2, y + 12 + i * 20))
            screen.blit(text_surface, text_rect)

    def _handle_audio_adjustment(self, increase: bool) -> None:
        """Handle audio slider adjustments."""
        option = self.audio_options[self.active_option]
        key = option["key"]
        current = self.config[key]

        step = 5
        if increase:
            new_value = min(option["max"], current + step)
        else:
            new_value = max(option["min"], current - step)

        self.config[key] = new_value
        self._apply_audio_settings()

    def _start_key_binding(self) -> None:
        """Start waiting for new key binding."""
        binding = self.key_bindings[self.active_option]
        self.waiting_for_key = True
        self.waiting_for_action = binding["action"]

    def _handle_key_binding(self, key: int) -> None:
        """Handle new key binding."""
        if key == pygame.K_ESCAPE:
            # Cancel key binding
            self.waiting_for_key = False
            self.waiting_for_action = None
            return

        if self.waiting_for_action:
            # Update the primary key (first in the list)
            if self.waiting_for_action in self.config["key_bindings"]:
                self.config["key_bindings"][self.waiting_for_action][0] = key

        self.waiting_for_key = False
        self.waiting_for_action = None

    def _close_config(self) -> None:
        """Close config and save settings."""
        self._save_config()
        self._apply_audio_settings()
        # Reload config in the global config manager
        config_manager.reload_config()

        # Hide this subscene
        if hasattr(self.parent_scene, "subscene_manager"):
            self.parent_scene.subscene_manager.hide_subscene(SubSceneType.CONFIG)
