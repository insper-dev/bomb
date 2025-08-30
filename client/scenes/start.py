import math
import time

import pygame

from client.scenes.base import BaseScene, Scenes
from core.constants import ACCENT_BLUE, ACCENT_GREEN, DARK_NAVY, EXPLOSION_ORANGE, SLATE_GRAY, WHITE


class StartScene(BaseScene):
    """Tela de splash moderna com transições animadas."""

    TRANSITION_TIME = 2000  # Tempo mais longo para melhor experiência

    def __init__(self, app) -> None:
        super().__init__(app)
        self._initialize_timer()
        self._initialize_texts()
        self.text_index = 0
        self.fade_alpha = 0
        self.fade_direction = 1
        self.particles = []

        # Estado visual
        self.start_time = time.time()

    def _initialize_timer(self) -> None:
        self.time = {"time_elapsed": 0, "initial_time": pygame.time.get_ticks(), "time_counter": 0}

    def _initialize_texts(self) -> None:
        cx, cy = self.app.screen_center
        self.text_pos = (cx, cy)
        self.texts = [
            "With Pygame Community",
            "From Margenta Production",
            ["Images by Arak", "@arak_in_arts", "arakinarts@gmail.com"],
            ["Sounds and Music by Finx", "@Finx212", "finx2616@gmail.com"],
        ]

    def render(self) -> None:
        # Background moderno
        self._render_modern_background()

        # Atualiza animações
        self._update_animations()

        # Renderiza efeitos visuais
        self._render_particles()

        # Atualiza timer e transições
        self._update_timer()
        self._handle_transition()

        # Renderiza texto atual com fade
        if self.text_index < len(self.texts):
            self._render_current_text()

    def _update_timer(self) -> None:
        current_time = pygame.time.get_ticks()
        self.time["time_elapsed"] = current_time - self.time["initial_time"]
        self.time["initial_time"] = current_time
        self.time["time_counter"] += self.time["time_elapsed"]

        # Atualiza fade
        fade_duration = self.TRANSITION_TIME * 0.3  # 30% do tempo para fade
        progress = min(1.0, self.time["time_counter"] / fade_duration)

        if self.time["time_counter"] < fade_duration:
            # Fade in
            self.fade_alpha = int(255 * progress)
        elif self.time["time_counter"] > self.TRANSITION_TIME - fade_duration:
            # Fade out
            fade_out_progress = (
                self.time["time_counter"] - (self.TRANSITION_TIME - fade_duration)
            ) / fade_duration
            self.fade_alpha = int(255 * (1 - fade_out_progress))
        else:
            # Totalmente visível
            self.fade_alpha = 255

    def _handle_transition(self) -> None:
        if self.time["time_counter"] > self.TRANSITION_TIME:
            self.text_index += 1
            self.time["time_counter"] = 0
            self.fade_alpha = 0

            if self.text_index >= len(self.texts):
                self.app.current_scene = Scenes.INITIAL_SCENE

    def handle_event(self, event) -> None:
        # Permite pular as animações clicando ou pressionando qualquer tecla
        if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
            self.app.current_scene = Scenes.INITIAL_SCENE

    def _render_current_text(self) -> None:
        """Renderiza o texto atual com efeito fade."""
        current_text = self.texts[self.text_index]
        font = pygame.font.SysFont("Arial", 42, bold=True)

        # Efeitos diferentes para cada texto
        if self.text_index == 1:  # Moriaty com glow
            for offset in [(2, 2), (-2, -2), (2, -2), (-2, 2)]:
                glow_surface = font.render(current_text, True, ACCENT_BLUE)
                glow_rect = glow_surface.get_rect(
                    center=(self.text_pos[0] + offset[0], self.text_pos[1] + offset[1])
                )
                self.app.screen.blit(glow_surface, glow_rect)
        elif self.text_index == 2:  # Margenta com pulse
            pulse = 1 + 0.1 * math.sin(time.time() * 4)
            font_size = int(42 * pulse)
            font = pygame.font.SysFont("Arial", font_size, bold=True)
            text_surface = font.render(current_text[0], True, WHITE)

        # Texto principal com alpha
        for i, text in enumerate(
            current_text if isinstance(current_text, list) else [current_text]
        ):
            text_surface = font.render(text, True, WHITE)
            text_surface.set_alpha(self.fade_alpha)
            text_rect = text_surface.get_rect(
                center=(self.text_pos[0], self.text_pos[1] + i * 50 - 25)
            )
            self.app.screen.blit(text_surface, text_rect)

    def _render_modern_background(self) -> None:
        """Renderiza background moderno com gradiente."""
        screen_w, screen_h = self.app.screen.get_size()

        # Background base
        self.app.screen.fill(DARK_NAVY)

        # Gradiente sutil animado
        current_time = time.time()
        for y in range(0, screen_h, 4):
            wave = math.sin(current_time * 2 + y * 0.01) * 20
            ratio = (y + wave) / screen_h

            color_r = int(DARK_NAVY.r + (SLATE_GRAY.r - DARK_NAVY.r) * ratio * 0.1)
            color_g = int(DARK_NAVY.g + (SLATE_GRAY.g - DARK_NAVY.g) * ratio * 0.1)
            color_b = int(DARK_NAVY.b + (SLATE_GRAY.b - DARK_NAVY.b) * ratio * 0.1)

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

        # Adiciona partículas ocasionais
        if len(self.particles) < 10 and current_time % 0.5 < 0.1:
            self._add_ambient_particle()

        # Atualiza partículas
        self.particles = [p for p in self.particles if p["life"] > 0]
        for particle in self.particles:
            particle["x"] += particle["dx"]
            particle["y"] += particle["dy"]
            particle["life"] -= 1

    def _render_particles(self) -> None:
        """Renderiza partículas ambientes."""
        for particle in self.particles:
            alpha = int(100 * (particle["life"] / particle["max_life"]))
            size = max(1, int(3 * (particle["life"] / particle["max_life"])))

            particle_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            color = (*particle["color"][:3], alpha)
            pygame.draw.circle(particle_surface, color, (size, size), size)
            self.app.screen.blit(particle_surface, (particle["x"] - size, particle["y"] - size))

    def _add_ambient_particle(self) -> None:
        """Adiciona partícula ambiente."""
        import random

        screen_w, screen_h = self.app.screen.get_size()

        colors = [ACCENT_BLUE, ACCENT_GREEN, EXPLOSION_ORANGE]

        self.particles.append(
            {
                "x": random.randint(0, screen_w),
                "y": random.randint(0, screen_h),
                "dx": random.uniform(-0.5, 0.5),
                "dy": random.uniform(-0.5, 0.5),
                "color": random.choice(colors),
                "life": 200,
                "max_life": 200,
            }
        )
