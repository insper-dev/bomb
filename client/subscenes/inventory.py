"""
Inventory subscene for displaying player inventory and stats.
"""

import pygame

from core.constants import (
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_YELLOW,
    DARK_NAVY,
    LIGHT_GRAY,
    WHITE,
)

from .base import BaseSubScene, SubSceneType


class InventorySubScene(BaseSubScene):
    """Inventory and stats subscene that overlays the game."""

    def __init__(self, app, parent_scene) -> None:
        super().__init__(app, parent_scene)

        self.modal = True
        self.background_alpha = 140

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle inventory events."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_i, pygame.K_TAB):
                self._close_inventory()
                return True

        return False

    def render(self, screen: pygame.Surface) -> None:
        """Render the inventory overlay."""
        if not self.active:
            return

        # Semi-transparent background
        self._render_background_overlay(screen)

        screen_w, screen_h = screen.get_size()

        # Inventory panel
        panel_width = 500
        panel_height = 400
        panel_x = (screen_w - panel_width) // 2
        panel_y = (screen_h - panel_height) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        self._render_panel(screen, panel_rect, DARK_NAVY, ACCENT_BLUE)

        # Title
        title_font = pygame.font.SysFont("Arial", 32, bold=True)
        title_text = title_font.render("INVENTÁRIO", True, WHITE)
        title_rect = title_text.get_rect(center=(screen_w // 2, panel_y + 40))
        screen.blit(title_text, title_rect)

        # Player stats (if game service available)
        self._render_player_stats(screen, panel_x, panel_y + 80, panel_width)

        # Instructions
        instructions_font = pygame.font.SysFont("Arial", 16)
        instruction_text = "ESC/I/TAB: Fechar inventário"
        inst_surface = instructions_font.render(instruction_text, True, LIGHT_GRAY)
        inst_rect = inst_surface.get_rect(center=(screen_w // 2, panel_y + panel_height - 30))
        screen.blit(inst_surface, inst_rect)

    def _render_player_stats(self, screen: pygame.Surface, x: int, y: int, width: int) -> None:
        """Render current player statistics."""
        # Section title
        section_font = pygame.font.SysFont("Arial", 24, bold=True)
        section_text = section_font.render("Estatísticas do Jogador", True, ACCENT_GREEN)
        screen.blit(section_text, (x + 20, y))

        # Get player data if available
        stats = self._get_player_stats()

        stat_font = pygame.font.SysFont("Arial", 18)
        stat_y = y + 40

        for i, (label, value, color) in enumerate(stats):
            # Label
            label_surface = stat_font.render(f"{label}:", True, WHITE)
            screen.blit(label_surface, (x + 30, stat_y + i * 25))

            # Value
            value_surface = stat_font.render(str(value), True, color)
            screen.blit(value_surface, (x + 200, stat_y + i * 25))

    def _get_player_stats(self) -> list[tuple[str, str, pygame.Color]]:
        """Get current player statistics."""
        stats = []

        # Try to get player data from game service
        if hasattr(self.app, "game_service") and self.app.game_service.state:
            game_state = self.app.game_service.state
            user = self.app.auth_service.current_user

            if user and user.id in game_state.players:
                player = game_state.players[user.id]

                stats.extend(
                    [
                        ("Nome", player.username, WHITE),
                        ("Posição", f"({player.x}, {player.y})", ACCENT_YELLOW),
                        ("Bombas Ativas", str(len(player.bombs)), ACCENT_GREEN),
                        ("Máximo de Bombas", str(player.max_bombs), ACCENT_BLUE),
                        ("Raio das Bombas", str(player.bomb_radius), ACCENT_GREEN),
                        (
                            "Tem Escudo",
                            "Sim" if "shield" in player.power_ups else "Não",
                            ACCENT_BLUE,
                        ),
                        (
                            "Status",
                            "Vivo" if player.alive else "Morto",
                            ACCENT_GREEN if player.alive else pygame.Color(255, 100, 100),
                        ),
                    ]
                )
            else:
                stats.append(("Status", "Dados indisponíveis", LIGHT_GRAY))
        else:
            stats.append(("Status", "Fora do jogo", LIGHT_GRAY))

        return stats

    def _close_inventory(self) -> None:
        """Close the inventory."""
        if hasattr(self.parent_scene, "subscene_manager"):
            self.parent_scene.subscene_manager.hide_subscene(SubSceneType.INVENTORY)
