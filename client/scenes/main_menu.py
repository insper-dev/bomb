import math
import time

import pygame

from client.scenes.base import BaseScene, Scenes
from core.constants import (
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_PURPLE,
    BLUE,
    EXPLOSION_ORANGE,
    SCENES_IMAGE_MAP,
    WHITE,
)


class MainMenuScene(BaseScene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.app = app
        self.active_button = 0

        # Efeitos visuais melhorados
        self.title_pulse = 0
        self.particle_timer = 0
        self.particles = []
        self.start_time = time.time()

        # Posições dos botões
        cx, cy = self.app.screen_center
        self.buttons = [
            {
                "rect": pygame.Rect(cx - 100, int(cy * 1.05) - 30, 200, 60),
                "text": "JOGAR",
                "action": self._handle_play_button,
                "variant": "primary",
            },
            {
                "rect": pygame.Rect(int(cx * 0.6) - 90, int(cy * 1.15) - 25, 180, 50),
                "text": "Configurações",
                "action": self._handle_settings,
                "variant": "secondary",
            },
            {
                "rect": pygame.Rect(int(cx * 1.4) - 60, int(cy * 1.15) - 25, 120, 50),
                "text": "Sair",
                "action": self._handle_quit,
                "variant": "outline",
            },
        ]

        # Adiciona botão de logout se logado
        if self.app.auth_service.is_logged_in:
            self.buttons.append(
                {
                    "rect": pygame.Rect(cx - 75, int(cy * 1.3) - 22, 150, 45),
                    "text": "Logout",
                    "action": self._handle_logout,
                    "variant": "danger",
                }
            )

        # Estado visual dos botões
        self.button_hover = [False] * len(self.buttons)

        # Compatibilidade
        self.components = []

        self.app.auth_service.register_logout_callback(self._on_logout)

    def _handle_play_button(self) -> None:
        """Handle play button logic - redirect to login or matchmaking based on auth status"""
        if self.app.auth_service.is_logged_in:
            self.app.current_scene = Scenes.MATCHMAKING
        else:
            self.app.current_scene = Scenes.LOGIN

    def _handle_settings(self) -> None:
        """Handle settings button - go to login/settings."""
        self.app.current_scene = Scenes.LOGIN

    def _handle_quit(self) -> None:
        """Handle quit with confirmation effect."""
        # Adiciona efeito de partículas antes de sair
        for _ in range(20):
            self._add_particle(
                self.app.screen_center[0], self.app.screen_center[1], EXPLOSION_ORANGE
            )
        self.app.running = False

    def _handle_logout(self) -> None:
        """Handle logout."""
        self.app.auth_service.logout()

    def handle_event(self, event: pygame.event.Event) -> None:
        mouse_pos = pygame.mouse.get_pos()

        # Eventos de clique
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Clique esquerdo
                for _, button in enumerate(self.buttons):
                    if button["rect"].collidepoint(mouse_pos):
                        button["action"]()
                        return

        # Navegação por teclado
        self._handle_keyboard_navigation(event)

    def render(self) -> None:
        mouse_pos = pygame.mouse.get_pos()

        # Background moderno com gradiente
        self._render_modern_background()

        # Atualiza partículas e efeitos
        self._update_effects()

        # Renderiza partículas de fundo
        self._render_particles()

        # Título customizado com efeitos
        self._render_custom_title()

        # Renderiza informações de status customizadas
        self._render_status_info()

        # Atualiza estado hover dos botões
        for i, button in enumerate(self.buttons):
            self.button_hover[i] = button["rect"].collidepoint(mouse_pos)

        # Renderiza botões
        for i, button in enumerate(self.buttons):
            is_focused = i == self.active_button
            is_disabled = button["text"] == "Logout" and not self.app.auth_service.is_logged_in
            self._render_button(
                button["rect"],
                button["text"],
                button["variant"],
                self.button_hover[i],
                is_focused,
                is_disabled,
            )

    def _render_modern_background(self) -> None:
        """Renderiza background moderno com gradiente."""
        background = SCENES_IMAGE_MAP["background"]
        self.app.screen.blit(background, (0, 0))

        # Change the intensity of the background over time for a dynamic effect
        elapsed = time.time() - self.start_time
        overlay = pygame.Surface(self.app.screen.get_size(), pygame.SRCALPHA)
        alpha = int((math.sin(elapsed * 0.5) + 1) / 2 * 25)  # Oscila entre 0 e 25
        overlay.fill((0, 0, 0, alpha))
        self.app.screen.blit(overlay, (0, 0))

    def _update_effects(self) -> None:
        """Atualiza efeitos visuais."""
        current_time = pygame.time.get_ticks()

        # Atualiza pulse do título
        self.title_pulse = (current_time % 2000) / 2000.0

        # Adiciona partículas ocasionais
        if current_time - self.particle_timer > 2000:  # A cada 2 segundos
            angle = current_time * 0.001
            radius = 150
            offset_x = math.cos(angle) * radius
            offset_y = math.sin(angle) * radius

            self._add_particle(
                self.app.screen_center[0] + offset_x,
                self.app.screen_center[1] + offset_y,
                ACCENT_BLUE,
            )
            self.particle_timer = current_time

        # Atualiza partículas existentes
        self.particles = [p for p in self.particles if p["life"] > 0]
        for particle in self.particles:
            particle["x"] += particle["dx"]
            particle["y"] += particle["dy"]
            particle["life"] -= 1

    def _add_particle(self, x: float, y: float, color) -> None:
        """Adiciona uma partícula decorativa."""
        import random

        self.particles.append(
            {
                "x": x,
                "y": y,
                "dx": random.uniform(-2, 2),
                "dy": random.uniform(-2, 2),
                "color": color,
                "life": 60,
                "max_life": 60,
            }
        )

    def _render_particles(self) -> None:
        """Renderiza partículas decorativas."""
        for particle in self.particles:
            alpha = int(255 * (particle["life"] / particle["max_life"]))
            size = max(1, int(4 * (particle["life"] / particle["max_life"])))

            particle_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            color = (*particle["color"][:3], alpha)
            pygame.draw.circle(particle_surface, color, (size, size), size)
            self.app.screen.blit(particle_surface, (particle["x"] - size, particle["y"] - size))

    def _render_custom_title(self) -> None:
        """Renderiza título customizado com efeitos."""
        # Get and scale logo
        logo = pygame.transform.scale_by(SCENES_IMAGE_MAP["logo"], 1.15)
        logo_rect = logo.get_rect(
            center=(self.app.screen_center[0], int(self.app.screen_center[1] * 0.5))
        )
        self.app.screen.blit(logo, logo_rect)

    def _render_status_info(self) -> None:
        """Renderiza informações de status do usuário."""
        if self.app.auth_service.is_logged_in and (user := self.app.auth_service.current_user):
            status_text = f"Bem-vindo, {user.username}!"
            color = BLUE
        else:
            status_text = "Clique em JOGAR para começar ou fazer login"
            color = WHITE

        # Bolder text for status

        info_font = pygame.font.SysFont("Arial", 24, bold=True)
        status_surface = info_font.render(status_text, True, color)
        status_rect = status_surface.get_rect(
            center=(self.app.screen_center[0], int(self.app.screen_center[1] * 1.63))
        )
        self.app.screen.blit(status_surface, status_rect)

    def _render_button(
        self,
        rect: pygame.Rect,
        text: str,
        variant: str,
        is_hover: bool,
        is_focused: bool,
        is_disabled: bool = False,
    ) -> None:
        """Renderiza botão moderno."""
        # Cores baseadas no variant e estado
        if is_disabled:
            bg_color = (60, 60, 60)
            text_color = (120, 120, 120)
            border_color = (80, 80, 80)
        elif variant == "primary":
            bg_color = ACCENT_GREEN if is_hover else ACCENT_BLUE
            text_color = WHITE
            border_color = bg_color
        elif variant == "secondary":
            bg_color = ACCENT_PURPLE if is_hover else (70, 50, 100)
            text_color = WHITE
            border_color = ACCENT_PURPLE
        elif variant == "danger":
            bg_color = (180, 50, 50) if is_hover else (150, 40, 40)
            text_color = WHITE
            border_color = bg_color
        else:  # outline
            bg_color = (30, 40, 55) if is_hover else (20, 30, 45)
            text_color = WHITE
            border_color = ACCENT_BLUE

        # Efeito de foco
        if is_focused:
            # Borda extra para indicar foco
            focus_rect = pygame.Rect(rect.x - 2, rect.y - 2, rect.width + 4, rect.height + 4)
            pygame.draw.rect(self.app.screen, ACCENT_GREEN, focus_rect, 2, border_radius=8)

        # Fundo do botão
        pygame.draw.rect(self.app.screen, bg_color, rect, border_radius=6)
        pygame.draw.rect(self.app.screen, border_color, rect, 2, border_radius=6)

        # Texto do botão
        font_size = 28 if variant == "primary" else 20 if variant == "secondary" else 18
        font = pygame.font.SysFont("Arial", font_size, bold=True)
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=rect.center)
        self.app.screen.blit(text_surface, text_rect)

    def _handle_keyboard_navigation(self, event: pygame.event.Event) -> None:
        """Navegação por teclado entre botões."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.active_button = (self.active_button - 1) % len(self.buttons)
            elif event.key == pygame.K_DOWN:
                self.active_button = (self.active_button + 1) % len(self.buttons)
            elif event.key == pygame.K_LEFT:
                if self.active_button in [1, 2]:  # Botões configurações/sair
                    self.active_button = 1 if self.active_button == 2 else 2
            elif event.key == pygame.K_RIGHT:
                if self.active_button in [1, 2]:  # Botões configurações/sair
                    self.active_button = 2 if self.active_button == 1 else 1
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                # Ativa botão focado
                button = self.buttons[self.active_button]
                is_disabled = button["text"] == "Logout" and not self.app.auth_service.is_logged_in
                if not is_disabled:
                    button["action"]()

    def _on_logout(self) -> None:
        """Executado quando o jogador faz logout."""
        # Atualiza lista de botões removendo logout se necessário
        self.buttons = [b for b in self.buttons if b["text"] != "Logout"]
        self.button_hover = [False] * len(self.buttons)
        if self.active_button >= len(self.buttons):
            self.active_button = 0
