import math
import time

import pygame
from prisma.partials import Opponent

from client.scenes.base import BaseScene, Scenes
from client.services.matchmaking import MatchmakingService
from core.constants import (
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_YELLOW,
    DARK_NAVY,
    SLATE_GRAY,
    WHITE,
)


class MatchmakingScene(BaseScene):
    """Tela moderna de matchmaking com animações e efeitos visuais."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.matchmaking: MatchmakingService = app.matchmaking_service
        self.matchmaking.start()

        cx, cy = self.app.screen_center

        # Estado visual
        self.start_time = time.time()
        self.searching_animation = 0.0
        self.particles = []
        self.ripples = []

        # Posições dos elementos
        self.title_pos = (cx, cy - 150)
        self.status_pos = (cx, cy - 50)
        self.cancel_rect = pygame.Rect(cx - 100, cy + 175, 200, 50)
        self.cancel_hover = False

        # Configurações de animação
        self.dots_animation = 0
        self.last_dot_update = pygame.time.get_ticks()

    def handle_event(self, event) -> None:
        mouse_pos = pygame.mouse.get_pos()

        # Processa clique no botão cancelar
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.cancel_rect.collidepoint(mouse_pos):
                self._cancel_matchmaking()
                return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._cancel_matchmaking()

    @property
    def match_id(self) -> str | None:
        return getattr(self.matchmaking, "match_id", None)

    @property
    def oponent(self) -> Opponent | None:
        return getattr(self.matchmaking, "opponent", None)

    def update(self) -> None:
        if self.match_id:
            self.matchmaking.stop()
            self.app.game_service.start(self.match_id)
            self.app.current_scene = Scenes.GAME
        super().update()

    def render(self) -> None:
        # Background moderno
        self._render_modern_background()

        # Atualiza animações
        self._update_animations()

        # Renderiza efeitos visuais
        self._render_search_animation()
        self._render_particles()

        # Atualiza textos baseado no estado
        self._update_status_text()

        # Renderiza componentes
        self._render_title()
        self._render_status()

        # Botão cancelar
        mouse_pos = pygame.mouse.get_pos()
        self.cancel_hover = self.cancel_rect.collidepoint(mouse_pos)
        self._render_cancel_button()

        # Informações adicionais
        self._render_time_elapsed()
        self._render_instructions()

    def _cancel_matchmaking(self) -> None:
        """Cancela o matchmaking e volta ao menu principal."""
        self.matchmaking.stop()
        self.app.current_scene = Scenes.MAIN_MENU

    def _render_modern_background(self) -> None:
        """Renderiza background animado."""
        screen_w, screen_h = self.app.screen.get_size()

        # Background base
        self.app.screen.fill(DARK_NAVY)

        # Círculos animados de fundo
        current_time = time.time()
        for i in range(3):
            angle = current_time * 0.5 + i * (2 * math.pi / 3)
            radius = 100 + 50 * math.sin(current_time * 0.3 + i)
            x = screen_w // 2 + int(radius * math.cos(angle))
            y = screen_h // 2 + int(radius * math.sin(angle))

            # Círculo com alpha
            circle_surface = pygame.Surface((40, 40), pygame.SRCALPHA)
            alpha = int(30 + 20 * math.sin(current_time * 2 + i))
            color = (*ACCENT_BLUE[:3], alpha)
            pygame.draw.circle(circle_surface, color, (20, 20), 20)
            self.app.screen.blit(circle_surface, (x - 20, y - 20))

    def _update_animations(self) -> None:
        """Atualiza animações da tela."""
        current_time = pygame.time.get_ticks()

        # Animação de dots
        if current_time - self.last_dot_update > 500:
            self.dots_animation = (self.dots_animation + 1) % 4
            self.last_dot_update = current_time

        # Adiciona partículas ocasionalmente
        if len(self.particles) < 10 and current_time % 100 == 0:
            self._add_search_particle()

        # Atualiza partículas
        self.particles = [p for p in self.particles if p["life"] > 0]
        for particle in self.particles:
            particle["angle"] += particle["speed"]
            particle["life"] -= 1

        # Adiciona ripples ocasionalmente
        if current_time % 1000 == 0:
            cx, cy = self.app.screen_center
            self._add_ripple(cx, cy)

        # Atualiza ripples
        self.ripples = [r for r in self.ripples if r["life"] > 0]
        for ripple in self.ripples:
            ripple["radius"] += ripple["speed"]
            ripple["life"] -= 1

    def _update_status_text(self) -> None:
        """Atualiza texto de status baseado no estado atual."""
        if self.match_id:
            self.title_text = "Partida Encontrada!"
            self.status_text = "Partida encontrada! Conectando..."
        else:
            self.title_text = "Procurando Oponente"
            dots = "." * self.dots_animation
            elapsed = int(time.time() - self.start_time)

            if elapsed < 5:
                self.status_text = f"Entrando na fila{dots}"
            elif elapsed < 15:
                self.status_text = f"Procurando jogadores{dots}"
            elif elapsed < 30:
                self.status_text = f"Expandindo busca{dots}"
            else:
                self.status_text = f"Procurando em todas as regiões{dots}"

    def _render_title(self) -> None:
        """Renderiza título da tela."""
        font = pygame.font.SysFont("Arial", 42, bold=True)

        # Efeito pulse se não encontrou partida ainda
        if not self.match_id:
            pulse = 1 + 0.1 * math.sin(time.time() * 3)
            font_size = int(42 * pulse)
            font = pygame.font.SysFont("Arial", font_size, bold=True)

        # Efeito glow
        for offset in [(2, 2), (-2, -2), (2, -2), (-2, 2)]:
            glow_surface = font.render(self.title_text, True, ACCENT_BLUE)
            glow_rect = glow_surface.get_rect(
                center=(self.title_pos[0] + offset[0], self.title_pos[1] + offset[1])
            )
            self.app.screen.blit(glow_surface, glow_rect)

        # Texto principal
        text_surface = font.render(self.title_text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.title_pos)
        self.app.screen.blit(text_surface, text_rect)

    def _render_status(self) -> None:
        """Renderiza texto de status."""
        font = pygame.font.SysFont("Arial", 24)
        text_surface = font.render(self.status_text, True, SLATE_GRAY)
        text_rect = text_surface.get_rect(center=self.status_pos)
        self.app.screen.blit(text_surface, text_rect)

    def _render_cancel_button(self) -> None:
        """Renderiza botão cancelar."""
        # Cores baseadas no hover
        bg_color = (30, 40, 55) if self.cancel_hover else (20, 30, 45)
        border_color = ACCENT_BLUE
        text_color = WHITE

        # Fundo do botão
        pygame.draw.rect(self.app.screen, bg_color, self.cancel_rect, border_radius=6)
        pygame.draw.rect(self.app.screen, border_color, self.cancel_rect, 2, border_radius=6)

        # Texto do botão
        font = pygame.font.SysFont("Arial", 20, bold=True)
        text_surface = font.render("Cancelar", True, text_color)
        text_rect = text_surface.get_rect(center=self.cancel_rect.center)
        self.app.screen.blit(text_surface, text_rect)

    def _render_search_animation(self) -> None:
        """Renderiza animação de busca no centro."""
        if self.match_id:
            return

        cx, cy = self.app.screen_center
        current_time = time.time()

        # Círculos concêntricos pulsantes
        for i in range(3):
            radius = 30 + i * 20 + int(20 * math.sin(current_time * 3 + i))
            alpha = int(100 - i * 30)

            circle_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            color = (*ACCENT_YELLOW[:3], alpha)
            pygame.draw.circle(circle_surface, color, (radius, radius), radius, 2)
            self.app.screen.blit(circle_surface, (cx - radius, cy - radius))

    def _render_particles(self) -> None:
        """Renderiza partículas de busca."""
        cx, cy = self.app.screen_center

        for particle in self.particles:
            x = cx + particle["radius"] * math.cos(particle["angle"])
            y = cy + particle["radius"] * math.sin(particle["angle"])

            alpha = int(255 * (particle["life"] / particle["max_life"]))
            size = max(1, int(4 * (particle["life"] / particle["max_life"])))

            particle_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            color = (*ACCENT_BLUE[:3], alpha)
            pygame.draw.circle(particle_surface, color, (size, size), size)
            self.app.screen.blit(particle_surface, (x - size, y - size))

        # Renderiza ripples
        for ripple in self.ripples:
            alpha = int(100 * (ripple["life"] / ripple["max_life"]))
            ripple_surface = pygame.Surface(
                (ripple["radius"] * 2, ripple["radius"] * 2), pygame.SRCALPHA
            )
            color = (*ACCENT_GREEN[:3], alpha)
            pygame.draw.circle(
                ripple_surface, color, (ripple["radius"], ripple["radius"]), ripple["radius"], 2
            )
            self.app.screen.blit(
                ripple_surface, (ripple["x"] - ripple["radius"], ripple["y"] - ripple["radius"])
            )

    def _add_search_particle(self) -> None:
        """Adiciona partícula de busca."""
        import random

        self.particles.append(
            {
                "radius": random.randint(50, 150),
                "angle": random.uniform(0, 2 * math.pi),
                "speed": random.uniform(0.02, 0.05),
                "life": 120,
                "max_life": 120,
            }
        )

    def _add_ripple(self, x: int, y: int) -> None:
        """Adiciona efeito ripple."""
        self.ripples.append({"x": x, "y": y, "radius": 5, "speed": 2, "life": 60, "max_life": 60})

    def _render_time_elapsed(self) -> None:
        """Renderiza tempo decorrido."""
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        time_text = f"Tempo: {mins:02d}:{secs:02d}"

        font = pygame.font.SysFont("Arial", 16)
        text_surface = font.render(time_text, True, WHITE)
        self.app.screen.blit(text_surface, (20, 20))

    def _render_instructions(self) -> None:
        """Renderiza instruções na parte inferior."""
        instructions = ["ESC - Cancelar busca", "O matchmaking pode levar alguns minutos"]

        font = pygame.font.SysFont("Arial", 14)
        y_start = self.app.screen.get_height() - 60

        for i, instruction in enumerate(instructions):
            text_surface = font.render(instruction, True, SLATE_GRAY)
            self.app.screen.blit(text_surface, (20, y_start + i * 20))
