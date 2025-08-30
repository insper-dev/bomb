import json
import time
from pathlib import Path
from typing import Any

import pygame

from client.config_manager import config_manager
from client.scenes.base import BaseScene, Scenes
from core.constants import (
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_RED,
    DARK_NAVY,
    LIGHT_GRAY,
    MEDIUM_GRAY,
    SCENES_IMAGE_MAP,
    WHITE,
)


class ConfigScene(BaseScene):
    """Scene for audio and key configuration settings."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.app = app

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

        # Initialize pygame mixer for audio preview
        pygame.mixer.init()

        # Visual effects
        self.particle_timer = 0
        self.particles = []
        self.start_time = time.time()

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
        pygame.mixer.music.set_volume(master_vol * music_vol)

        print(f"[CONFIG] Applied audio: Master={master_vol:.2f}, Music={music_vol:.2f}")

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.waiting_for_key and event.type == pygame.KEYDOWN:
            self._handle_key_binding(event.key)
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._save_config()
                self._apply_audio_settings()
                # Reload config in the global config manager
                config_manager.reload_config()
                self.app.current_scene = Scenes.MAIN_MENU
                return

            elif event.key == pygame.K_TAB:
                # Switch between Audio and Keys sections
                self.active_section = (self.active_section + 1) % 2
                self.active_option = 0

            elif event.key == pygame.K_UP:
                if self.active_section == 0:  # Audio
                    self.active_option = (self.active_option - 1) % len(self.audio_options)
                else:  # Keys
                    self.active_option = (self.active_option - 1) % len(self.key_bindings)

            elif event.key == pygame.K_DOWN:
                if self.active_section == 0:  # Audio
                    self.active_option = (self.active_option + 1) % len(self.audio_options)
                else:  # Keys
                    self.active_option = (self.active_option + 1) % len(self.key_bindings)

            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                if self.active_section == 0:  # Audio sliders
                    self._handle_audio_adjustment(event.key == pygame.K_RIGHT)

            elif event.key == pygame.K_RETURN:
                if self.active_section == 1:  # Key bindings
                    self._start_key_binding()

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
        print(f"[CONFIG] Press new key for {binding['name']}...")

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
                action_name = self.waiting_for_action
                key_name = pygame.key.name(key)
                print(f"[CONFIG] Key binding updated: {action_name} -> {key_name}")

        self.waiting_for_key = False
        self.waiting_for_action = None

    def render(self) -> None:
        # Background
        self._render_background()

        # Update effects
        self._update_effects()

        # Title
        self._render_title()

        # Navigation tabs
        self._render_tabs()

        # Content based on active section
        if self.active_section == 0:
            self._render_audio_settings()
        else:
            self._render_key_settings()

        # Instructions
        self._render_instructions()

    def _render_background(self) -> None:
        """Render modern background."""
        background = SCENES_IMAGE_MAP["background"]
        self.app.screen.blit(background, (0, 0))

        # Dark overlay for better readability
        overlay = pygame.Surface(self.app.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.app.screen.blit(overlay, (0, 0))

    def _update_effects(self) -> None:
        """Update visual effects."""
        current_time = pygame.time.get_ticks()

        # Add occasional particles
        if current_time - self.particle_timer > 3000:  # Every 3 seconds
            import random

            x = random.randint(0, self.app.screen.get_width())
            y = random.randint(0, self.app.screen.get_height())
            self._add_particle(x, y, ACCENT_BLUE)
            self.particle_timer = current_time

        # Update existing particles
        self.particles = [p for p in self.particles if p["life"] > 0]
        for particle in self.particles:
            particle["x"] += particle["dx"]
            particle["y"] += particle["dy"]
            particle["life"] -= 1

    def _add_particle(self, x: float, y: float, color) -> None:
        """Add decorative particle."""
        import random

        self.particles.append(
            {
                "x": x,
                "y": y,
                "dx": random.uniform(-1, 1),
                "dy": random.uniform(-1, 1),
                "color": color,
                "life": 120,
                "max_life": 120,
            }
        )

    def _render_title(self) -> None:
        """Render scene title."""
        font = pygame.font.SysFont("Arial", 48, bold=True)
        title_surface = font.render("CONFIGURAÇÕES", True, WHITE)
        title_rect = title_surface.get_rect(center=(self.app.screen_center[0], 80))
        self.app.screen.blit(title_surface, title_rect)

    def _render_tabs(self) -> None:
        """Render navigation tabs."""
        cx, cy = self.app.screen_center
        tab_y = 150

        tabs = ["ÁUDIO", "CONTROLES"]
        tab_width = 150

        for i, tab_name in enumerate(tabs):
            x = cx - 160 + (i * 170)
            rect = pygame.Rect(x, tab_y, tab_width, 40)

            # Tab colors
            if i == self.active_section:
                bg_color = ACCENT_BLUE
                text_color = WHITE
                border_color = ACCENT_GREEN
            else:
                bg_color = DARK_NAVY
                text_color = LIGHT_GRAY
                border_color = MEDIUM_GRAY

            # Draw tab
            pygame.draw.rect(self.app.screen, bg_color, rect, border_radius=5)
            pygame.draw.rect(self.app.screen, border_color, rect, 2, border_radius=5)

            # Tab text
            font = pygame.font.SysFont("Arial", 20, bold=True)
            text_surface = font.render(tab_name, True, text_color)
            text_rect = text_surface.get_rect(center=rect.center)
            self.app.screen.blit(text_surface, text_rect)

    def _render_audio_settings(self) -> None:
        """Render audio configuration options."""
        cx, cy = self.app.screen_center
        start_y = 250

        for i, option in enumerate(self.audio_options):
            y = start_y + (i * 80)
            is_active = i == self.active_option

            # Option name
            font = pygame.font.SysFont("Arial", 24, bold=is_active)
            color = ACCENT_GREEN if is_active else WHITE
            name_surface = font.render(option["name"], True, color)
            self.app.screen.blit(name_surface, (cx - 200, y))

            # Slider
            self._render_slider(cx + 50, y + 10, 200, option, is_active)

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
        font = pygame.font.SysFont("Arial", 20)
        value_text = f"{value}%"
        value_surface = font.render(value_text, True, WHITE)
        self.app.screen.blit(value_surface, (x + width + 20, y - 5))

    def _render_key_settings(self) -> None:
        """Render key binding configuration."""
        cx, cy = self.app.screen_center
        start_y = 250

        for i, binding in enumerate(self.key_bindings):
            y = start_y + (i * 60)
            is_active = i == self.active_option

            # Action name
            font = pygame.font.SysFont("Arial", 22, bold=is_active)
            color = ACCENT_GREEN if is_active else WHITE
            name_surface = font.render(binding["name"], True, color)
            self.app.screen.blit(name_surface, (cx - 200, y))

            # Key display
            self._render_key_binding(cx + 50, y, binding, is_active)

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
        font = pygame.font.SysFont("Arial", 18, bold=True)
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect()

        box_rect = pygame.Rect(x, y - 5, max(150, text_rect.width + 20), 30)
        border_color = ACCENT_GREEN if is_active else MEDIUM_GRAY

        pygame.draw.rect(self.app.screen, bg_color, box_rect, border_radius=5)
        pygame.draw.rect(self.app.screen, border_color, box_rect, 2, border_radius=5)

        # Center text in box
        text_pos = (
            box_rect.centerx - text_rect.width // 2,
            box_rect.centery - text_rect.height // 2,
        )
        self.app.screen.blit(text_surface, text_pos)

    def _render_instructions(self) -> None:
        """Render control instructions."""
        instructions = [
            "TAB: Alternar seções",
            "↑↓: Navegar opções",
            "←→: Ajustar volume (Áudio)",
            "ENTER: Alterar tecla (Controles)",
            "ESC: Voltar e salvar",
        ]

        start_y = self.app.screen.get_height() - 120
        font = pygame.font.SysFont("Arial", 16)

        for i, instruction in enumerate(instructions):
            y = start_y + (i * 20)
            text_surface = font.render(instruction, True, LIGHT_GRAY)
            text_rect = text_surface.get_rect(center=(self.app.screen_center[0], y))
            self.app.screen.blit(text_surface, text_rect)
