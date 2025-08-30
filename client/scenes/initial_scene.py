import math
import time

import pygame

from client.scenes.base import BaseScene, Scenes
from core.constants import (
    ACCENT_BLUE,
    ACCENT_GREEN,
    EXPLOSION_ORANGE,
    SCENES_IMAGE_MAP,
    WHITE,
)


class InitialScene(BaseScene):
    """Tela inicial moderna com animações e efeitos visuais."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.app.auth_service.get_current_user()

        cx, cy = self.app.screen_center

        # Estado visual
        self.start_time = time.time()
        self.particles = []
        self.wave_phase = 0

        # Posições dos elementos
        self.title_pos = (cx, int(cy * 0.7))
        self.subtitle_pos = (cx, cy)
        self.instruction_pos = (cx, int(cy * 1.3))

        # Textos
        self.title_text = "BOMB INSPER"
        self.subtitle_text = "Onde bombas podem ser legalmente colocadas"
        self.instruction_text = "Clique ou pressione ENTER para continuar"

        # Configuração de componentes (compatibilidade)
        self.components = []

    def render(self) -> None:
        """Renderiza a tela inicial moderna."""
        # Background moderno
        self._render_modern_background()

        # Atualiza animações
        self._update_animations()

        # Renderiza efeitos visuais
        self._render_particles()
        self._render_wave_effects()

        # Componentes de texto
        self._render_title()
        self._render_instruction()

    def handle_event(self, event) -> None:
        """Handle user input events."""
        if event.type == pygame.MOUSEBUTTONDOWN or (
            event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN
        ):
            self.app.current_scene = Scenes.MAIN_MENU

    def _render_title(self) -> None:
        """Renderiza título da tela."""
        # A imagem da logo vem de cima para baixo com o tempo e para no centro
        logo = pygame.transform.scale_by(SCENES_IMAGE_MAP["logo"], 1.15)
        elapsed = time.time() - self.start_time
        position = (self.title_pos[0], self.title_pos[1] - 80)
        offset_y = max(-180, -180 + int(elapsed * 100))

        if offset_y >= abs(position[1] - (self.title_pos[1]) + 82):
            offset_y = int(5 * math.sin(time.time() * 3))

        center = (self.title_pos[0], self.title_pos[1] + offset_y)
        logo_rect = logo.get_rect(center=center)
        self.app.screen.blit(logo, logo_rect)

    def _render_instruction(self) -> None:
        """Renderiza instrução com efeito pulse."""
        pulse = 1 + 0.3 * math.sin(time.time() * 2)
        alpha = int(255 * (0.7 + 0.3 * pulse))

        font = pygame.font.SysFont("Arial", 18)
        text_surface = font.render(self.instruction_text, True, WHITE)
        text_surface.set_alpha(alpha)
        text_rect = text_surface.get_rect(center=self.instruction_pos)
        self.app.screen.blit(text_surface, text_rect)

    def _render_modern_background(self) -> None:
        """Renderiza background moderno com gradiente."""
        background = SCENES_IMAGE_MAP["background"].copy()
        # Fade in com o tempo
        elapsed = time.time() - self.start_time
        alpha = min(255, int((elapsed / 2) * 255))
        background.set_alpha(alpha)
        self.app.screen.blit(background, (0, 0))

    def _update_animations(self) -> None:
        """Atualiza animações da tela."""
        current_time = time.time()
        self.wave_phase = current_time * 2

        # Adiciona partículas ocasionais
        if len(self.particles) < 20 and current_time % 0.2 < 0.05:
            self._add_floating_particle()

        # Atualiza partículas
        self.particles = [p for p in self.particles if p["life"] > 0]
        for particle in self.particles:
            particle["x"] += particle["dx"]
            particle["y"] += particle["dy"]
            particle["angle"] += particle["rotation"]
            particle["life"] -= 1

    def _render_particles(self) -> None:
        """Renderiza partículas flutuantes."""
        for particle in self.particles:
            alpha = int(150 * (particle["life"] / particle["max_life"]))
            size = int(particle["size"] * (particle["life"] / particle["max_life"]))

            if size > 0:
                particle_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                color = (*particle["color"][:3], alpha)
                pygame.draw.circle(particle_surface, color, (size, size), size)
                self.app.screen.blit(particle_surface, (particle["x"] - size, particle["y"] - size))

    def _render_wave_effects(self) -> None:
        """Renderiza efeitos de onda ao redor do título."""
        cx, cy = self.app.screen_center
        title_y = int(cy * 0.7)

        # Ondas concêntricas
        for i in range(3):
            radius = 200 + i * 50 + int(30 * math.sin(self.wave_phase + i))
            alpha = int(40 - i * 10)

            if alpha > 0:
                circle_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                color = (*EXPLOSION_ORANGE[:3], alpha)
                pygame.draw.circle(circle_surface, color, (radius, radius), radius, 2)
                self.app.screen.blit(circle_surface, (cx - radius, title_y - radius))

    def _add_floating_particle(self) -> None:
        """Adiciona partícula flutuante."""
        import random

        screen_w, screen_h = self.app.screen.get_size()

        colors = [ACCENT_BLUE, ACCENT_GREEN, EXPLOSION_ORANGE]

        self.particles.append(
            {
                "x": random.randint(-50, screen_w + 50),
                "y": random.randint(-50, screen_h + 50),
                "dx": random.uniform(-1, 1),
                "dy": random.uniform(-1, 1),
                "angle": 0,
                "rotation": random.uniform(-0.1, 0.1),
                "size": random.randint(2, 6),
                "color": random.choice(colors),
                "life": 300,
                "max_life": 300,
            }
        )
