"""
Configuration manager for client settings.
"""

import json
from pathlib import Path
from typing import Any

import pygame


class ConfigManager:
    """Manages client configuration including key bindings and audio settings."""

    def __init__(self) -> None:
        self.config_file = Path("client_config.json")
        self.config = self._load_config()

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

    def get_keys_for_action(self, action: str) -> list[int]:
        """Get list of keys bound to an action."""
        return self.config["key_bindings"].get(action, [])

    def is_key_for_action(self, key: int, action: str) -> bool:
        """Check if a key is bound to a specific action."""
        return key in self.get_keys_for_action(action)

    def get_audio_setting(self, setting: str) -> int:
        """Get audio setting value."""
        return self.config.get(setting, 70)

    def reload_config(self) -> None:
        """Reload configuration from file."""
        self.config = self._load_config()


# Global config manager instance
config_manager = ConfigManager()
