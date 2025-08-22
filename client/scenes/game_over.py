import math
import time

import pygame

from client.scenes.base import BaseScene, Scenes
from client.services.game_over import GameOverService
from core.constants import (
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_RED,
    ACCENT_YELLOW,
    DARK_NAVY,
    EXPLOSION_ORANGE,
    SLATE_GRAY,
    WHITE,
)


class GameOverScene(BaseScene):
    """Tela moderna de game over com estatísticas e efeitos visuais."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.match_id = app.game_service.state.game_id if app.game_service.state else ""
        self.game_over_service = GameOverService(app)

        cx, cy = self.app.screen_center

        # Estado visual
        self.start_time = time.time()
        self.particles = []
        self.celebration_particles = []
        self.show_stats = False
        self.stats_reveal_time = 0

        # Posições dos elementos
        self.title_pos = (cx, cy - 200)
        self.loading_pos = (cx, cy - 50)
        self.winner_pos = (cx, cy - 100)
        self.play_again_rect = pygame.Rect(cx - 220, cy + 175, 200, 50)
        self.menu_rect = pygame.Rect(cx + 20, cy + 175, 150, 50)

        # Estado visual dos botões
        self.play_again_hover = False
        self.menu_hover = False

        # Textos dinâmicos
        self.title_text = "Game Over"
        self.loading_text = "Carregando estatísticas..."
        self.winner_text = ""

        # Start loading stats if we have a match ID
        if self.match_id:
            self.game_over_service.fetch_stats(self.match_id)

    def handle_event(self, event) -> None:
        # Processa eventos dos botões
        mouse_pos = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.play_again_rect.collidepoint(mouse_pos):
                    self._play_again()
                    return
                elif self.menu_rect.collidepoint(mouse_pos):
                    self._return_to_menu()
                    return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._play_again()
            elif event.key == pygame.K_ESCAPE:
                self._return_to_menu()

    def render(self) -> None:
        # Background moderno
        self._render_modern_background()

        # Atualiza animações
        self._update_animations()

        # Renderiza efeitos visuais
        self._render_particles()

        # Título
        self._render_title()

        # Conteúdo baseado no estado
        if self.game_over_service.is_stats_loading:
            self._render_loading_state()
        elif self.game_over_service.match_stats:
            self._render_stats()
        elif error := self.game_over_service.get_stats_error():
            self._render_error_state(error)

        # Botões (sempre visíveis)
        mouse_pos = pygame.mouse.get_pos()
        self.play_again_hover = self.play_again_rect.collidepoint(mouse_pos)
        self.menu_hover = self.menu_rect.collidepoint(mouse_pos)

        self._render_buttons()

        # Instruções
        self._render_instructions()

    def _render_title(self) -> None:
        """Renderiza título da tela."""
        font = pygame.font.SysFont("Arial", 56, bold=True)

        # Efeito glow
        for offset in [(3, 3), (-3, -3), (3, -3), (-3, 3)]:
            glow_surface = font.render(self.title_text, True, ACCENT_BLUE)
            glow_rect = glow_surface.get_rect(
                center=(self.title_pos[0] + offset[0], self.title_pos[1] + offset[1])
            )
            self.app.screen.blit(glow_surface, glow_rect)

        # Texto principal
        text_surface = font.render(self.title_text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.title_pos)
        self.app.screen.blit(text_surface, text_rect)

    def _render_buttons(self) -> None:
        """Renderiza botões da tela."""
        # Botão jogar novamente
        bg_color = ACCENT_GREEN if self.play_again_hover else ACCENT_BLUE
        pygame.draw.rect(self.app.screen, bg_color, self.play_again_rect, border_radius=6)
        pygame.draw.rect(self.app.screen, bg_color, self.play_again_rect, 2, border_radius=6)

        font = pygame.font.SysFont("Arial", 18, bold=True)
        text_surface = font.render("Jogar Novamente", True, WHITE)
        text_rect = text_surface.get_rect(center=self.play_again_rect.center)
        self.app.screen.blit(text_surface, text_rect)

        # Botão menu
        bg_color = (30, 40, 55) if self.menu_hover else (20, 30, 45)
        pygame.draw.rect(self.app.screen, bg_color, self.menu_rect, border_radius=6)
        pygame.draw.rect(self.app.screen, ACCENT_BLUE, self.menu_rect, 2, border_radius=6)

        text_surface = font.render("Menu", True, WHITE)
        text_rect = text_surface.get_rect(center=self.menu_rect.center)
        self.app.screen.blit(text_surface, text_rect)

    def _play_again(self) -> None:
        """Volta para o matchmaking."""
        self.app.current_scene = Scenes.MATCHMAKING

    def _return_to_menu(self) -> None:
        """Volta para o menu principal."""
        self.app.current_scene = Scenes.MAIN_MENU

    def _render_modern_background(self) -> None:
        """Renderiza background animado."""
        screen_w, screen_h = self.app.screen.get_size()

        # Background base
        self.app.screen.fill(DARK_NAVY)

        # Gradiente sutil
        for y in range(0, screen_h, 8):
            ratio = y / screen_h
            color_r = int(DARK_NAVY.r + (SLATE_GRAY.r - DARK_NAVY.r) * ratio * 0.2)
            color_g = int(DARK_NAVY.g + (SLATE_GRAY.g - DARK_NAVY.g) * ratio * 0.2)
            color_b = int(DARK_NAVY.b + (SLATE_GRAY.b - DARK_NAVY.b) * ratio * 0.2)
            pygame.draw.line(self.app.screen, (color_r, color_g, color_b), (0, y), (screen_w, y))
            pygame.draw.line(
                self.app.screen, (color_r, color_g, color_b), (0, y + 1), (screen_w, y + 1)
            )
            pygame.draw.line(
                self.app.screen, (color_r, color_g, color_b), (0, y + 2), (screen_w, y + 2)
            )
            pygame.draw.line(
                self.app.screen, (color_r, color_g, color_b), (0, y + 3), (screen_w, y + 3)
            )

    def _update_animations(self) -> None:
        """Atualiza animações da tela."""
        current_time = time.time()

        # Verifica se estatísticas foram carregadas
        if self.game_over_service.match_stats and not self.show_stats:
            self.show_stats = True
            self.stats_reveal_time = current_time

            # Adiciona partículas de celebração se houver vencedor ou empate
            stats = self.game_over_service.match_stats
            if stats.winner_id:
                winner_name = next(
                    (p.username for p in stats.players if p.user_id == stats.winner_id), "Vencedor"
                )
                self.winner_text = f"Vencedor: {winner_name}"
                self._add_celebration_particles()
            else:
                # Empate
                self.winner_text = "Empate!"
                self._add_celebration_particles()

        # Adiciona partículas de fundo ocasionais
        if len(self.particles) < 15 and current_time % 0.1 < 0.02:
            self._add_background_particle()

        # Atualiza partículas de fundo
        self.particles = [p for p in self.particles if p["life"] > 0]
        for particle in self.particles:
            particle["x"] += particle["dx"]
            particle["y"] += particle["dy"]
            particle["life"] -= 1

        # Atualiza partículas de celebração
        self.celebration_particles = [p for p in self.celebration_particles if p["life"] > 0]
        for particle in self.celebration_particles:
            particle["x"] += particle["dx"]
            particle["y"] += particle["dy"]
            particle["dy"] += 0.2  # Gravidade
            particle["life"] -= 1

    def _render_particles(self) -> None:
        """Renderiza partículas visuais."""
        # Partículas de fundo
        for particle in self.particles:
            alpha = int(80 * (particle["life"] / particle["max_life"]))
            size = max(1, int(2 * (particle["life"] / particle["max_life"])))

            particle_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            color = (*particle["color"][:3], alpha)
            pygame.draw.circle(particle_surface, color, (size, size), size)
            self.app.screen.blit(particle_surface, (particle["x"] - size, particle["y"] - size))

        # Partículas de celebração
        for particle in self.celebration_particles:
            alpha = int(255 * (particle["life"] / particle["max_life"]))
            size = max(2, int(4 * (particle["life"] / particle["max_life"])))

            particle_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            color = (*particle["color"][:3], alpha)
            pygame.draw.circle(particle_surface, color, (size, size), size)
            self.app.screen.blit(particle_surface, (particle["x"] - size, particle["y"] - size))

    def _add_background_particle(self) -> None:
        """Adiciona partícula de fundo."""
        import random

        screen_w, screen_h = self.app.screen.get_size()

        self.particles.append(
            {
                "x": random.randint(-50, screen_w + 50),
                "y": random.randint(-50, screen_h + 50),
                "dx": random.uniform(-0.5, 0.5),
                "dy": random.uniform(-0.5, 0.5),
                "color": ACCENT_BLUE,
                "life": 180,
                "max_life": 180,
            }
        )

    def _add_celebration_particles(self) -> None:
        """Adiciona partículas de celebração."""
        import random

        cx, cy = self.app.screen_center

        colors = [ACCENT_YELLOW, EXPLOSION_ORANGE, ACCENT_GREEN, ACCENT_BLUE]

        for _ in range(50):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 8)

            self.celebration_particles.append(
                {
                    "x": cx + random.uniform(-50, 50),
                    "y": cy - 100 + random.uniform(-20, 20),
                    "dx": speed * math.cos(angle),
                    "dy": speed * math.sin(angle) - random.uniform(2, 5),
                    "color": random.choice(colors),
                    "life": 120,
                    "max_life": 120,
                }
            )

    def _render_loading_state(self) -> None:
        """Renderiza estado de carregamento."""
        font = pygame.font.SysFont("Arial", 20)
        text_surface = font.render(self.loading_text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.loading_pos)
        self.app.screen.blit(text_surface, text_rect)

        # Spinner animado
        cx, cy = self.app.screen_center
        current_time = time.time()

        for i in range(8):
            angle = (i / 8) * 2 * math.pi + current_time * 4
            radius = 30
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)

            alpha = int(255 * (1 - i / 8))
            size = 4

            circle_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            color = (*ACCENT_BLUE[:3], alpha)
            pygame.draw.circle(circle_surface, color, (size, size), size)
            self.app.screen.blit(circle_surface, (x - size, y - size))

    def _render_stats(self) -> None:
        """Renderiza estatísticas da partida."""
        stats = self.game_over_service.match_stats
        cx, cy = self.app.screen_center

        # Texto do resultado (vencedor ou empate)
        if self.winner_text:
            font = pygame.font.SysFont("Arial", 32, bold=True)

            # Efeito pulse
            pulse = 1 + 0.1 * math.sin(time.time() * 3)
            font_size = int(32 * pulse)
            font = pygame.font.SysFont("Arial", font_size, bold=True)

            text_surface = font.render(self.winner_text, True, ACCENT_YELLOW)
            text_rect = text_surface.get_rect(center=(cx, cy - 100))
            self.app.screen.blit(text_surface, text_rect)

        # Duração da partida
        y_offset = -20 if self.winner_text else -60
        if stats.duration_seconds is not None:
            mins, secs = divmod(stats.duration_seconds, 60)
            duration_text = f"Duração: {mins}:{secs:02d}"
            font = pygame.font.SysFont("Arial", 20)
            text_surface = font.render(duration_text, True, WHITE)
            text_rect = text_surface.get_rect(center=(cx, cy + y_offset))
            self.app.screen.blit(text_surface, text_rect)
            y_offset += 40

        # Estatísticas dos jogadores
        y_offset += 20
        font = pygame.font.SysFont("Arial", 18)

        for _, player in enumerate(stats.players):
            color = ACCENT_YELLOW if player.is_winner else WHITE

            # Nome do jogador
            player_name = font.render(f"{player.username}", True, color)
            name_rect = player_name.get_rect(center=(cx - 100, cy + y_offset))
            self.app.screen.blit(player_name, name_rect)

            # Estatísticas
            stats_text = font.render(
                f"Bombas: {player.bombs_placed} | Kills: {player.players_killed}", True, SLATE_GRAY
            )
            stats_rect = stats_text.get_rect(center=(cx + 80, cy + y_offset))
            self.app.screen.blit(stats_text, stats_rect)

            y_offset += 35

    def _render_error_state(self, error: str) -> None:
        """Renderiza estado de erro."""
        cx, cy = self.app.screen_center

        error_text = f"Erro: {error}"
        font = pygame.font.SysFont("Arial", 20)
        text_surface = font.render(error_text, True, ACCENT_RED)
        text_rect = text_surface.get_rect(center=(cx, cy - 50))
        self.app.screen.blit(text_surface, text_rect)

    def _render_instructions(self) -> None:
        """Renderiza instruções na parte inferior."""
        instructions = ["ENTER - Jogar novamente | ESC - Voltar ao menu"]

        font = pygame.font.SysFont("Arial", 14)
        y_start = self.app.screen.get_height() - 40

        for i, instruction in enumerate(instructions):
            text_surface = font.render(instruction, True, SLATE_GRAY)
            text_rect = text_surface.get_rect(
                center=(self.app.screen.get_width() // 2, y_start + i * 20)
            )
            self.app.screen.blit(text_surface, text_rect)
