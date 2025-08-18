import math

import pygame

from client.scenes.base import BaseScene, Scenes
from core.constants import ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, DARK_NAVY, SLATE_GRAY, WHITE


class LoginScene(BaseScene):
    """Tela de Login/Signup moderna com pygame puro."""

    def __init__(self, app) -> None:
        super().__init__(app)
        cx, cy = self.app.screen_center

        # Estado
        self.is_signup_mode = False
        self.error_message = ""
        self.username_text = ""
        self.password_text = ""
        self.focused_field = "username"  # "username", "password", ou None

        # Efeitos visuais
        self.particles = []
        self.particle_timer = 0
        self.cursor_blink = 0
        self.last_blink = pygame.time.get_ticks()

        # Posições dos elementos
        self.title_pos = (cx, cy - 200)
        self.username_rect = pygame.Rect(cx - 175, cy - 65, 350, 50)
        self.password_rect = pygame.Rect(cx - 175, cy - 15, 350, 50)
        self.submit_rect = pygame.Rect(cx - 100, cy + 95, 200, 50)
        self.toggle_rect = pygame.Rect(cx - 75, cy + 155, 150, 40)
        self.back_rect = pygame.Rect(cx - 60, cy + 205, 120, 40)

        # Estado visual dos botões
        self.submit_hover = False
        self.toggle_hover = False
        self.back_hover = False

        # Callbacks de auth (signup usa os mesmos callbacks do login)
        auth = app.auth_service
        auth.register_login_success_callback(self._on_auth_success)
        auth.register_login_error_callback(self._on_auth_error)

        # Compatibilidade
        self.components = []

    def handle_event(self, event: pygame.event.Event) -> None:
        mouse_pos = pygame.mouse.get_pos()

        # Eventos de clique
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Clique esquerdo
                # Verifica se clicou nos campos de input
                if self.username_rect.collidepoint(mouse_pos):
                    self.focused_field = "username"
                elif self.password_rect.collidepoint(mouse_pos):
                    self.focused_field = "password"
                else:
                    self.focused_field = None

                # Verifica se clicou nos botões
                if self.submit_rect.collidepoint(mouse_pos):
                    self._submit()
                elif self.toggle_rect.collidepoint(mouse_pos):
                    self._on_toggle_mode()
                elif self.back_rect.collidepoint(mouse_pos):
                    self.app.current_scene = Scenes.MAIN_MENU

        # Eventos de teclado
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                # Navega entre os campos
                if self.focused_field == "username":
                    self.focused_field = "password"
                elif self.focused_field == "password":
                    self.focused_field = "username"
                else:
                    self.focused_field = "username"
            elif event.key == pygame.K_RETURN:
                if self.focused_field == "username":
                    self.focused_field = "password"
                elif self.focused_field == "password":
                    self._submit()
                else:
                    self._submit()
            elif event.key == pygame.K_BACKSPACE:
                if self.focused_field == "username" and self.username_text:
                    self.username_text = self.username_text[:-1]
                elif self.focused_field == "password" and self.password_text:
                    self.password_text = self.password_text[:-1]
            elif event.unicode and event.unicode.isprintable():
                # Adiciona caractere digitado
                if self.focused_field == "username":
                    self.username_text += event.unicode
                elif self.focused_field == "password":
                    self.password_text += event.unicode

    def render(self) -> None:
        mouse_pos = pygame.mouse.get_pos()

        # Background moderno com gradiente
        self._render_modern_background()

        # Atualiza efeitos visuais
        self._update_effects()

        # Renderiza partículas de fundo
        self._render_particles()

        # Título
        self._render_title()

        # Campos de input
        self._render_input_field(
            "Usuário",
            self.username_rect,
            self.username_text,
            self.focused_field == "username",
            False,
        )
        self._render_input_field(
            "Senha", self.password_rect, self.password_text, self.focused_field == "password", True
        )

        # Atualiza estado hover dos botões
        self.submit_hover = self.submit_rect.collidepoint(mouse_pos)
        self.toggle_hover = self.toggle_rect.collidepoint(mouse_pos)
        self.back_hover = self.back_rect.collidepoint(mouse_pos)

        # Botões
        auth = self.app.auth_service
        is_loading = auth.is_login_loading or auth.is_signup_loading

        submit_text = "Entrar" if not self.is_signup_mode else "Cadastrar"
        self._render_button(self.submit_rect, submit_text, self.submit_hover, "primary", is_loading)

        toggle_text = "Criar Conta" if not self.is_signup_mode else "Já tenho conta"
        self._render_button(self.toggle_rect, toggle_text, self.toggle_hover, "outline")

        self._render_button(self.back_rect, "Voltar", self.back_hover, "outline")

        # Estado de loading
        if is_loading:
            self._render_loading_indicator()

        # Mensagem de erro
        if self.error_message:
            self._render_error_message()

    def update(self) -> None:
        # Captura erros de auth
        auth = self.app.auth_service
        err = auth.get_signup_error() if self.is_signup_mode else auth.get_login_error()
        if err:
            self.error_message = err

        # Atualiza cursor blink
        current_time = pygame.time.get_ticks()
        if current_time - self.last_blink > 500:
            self.cursor_blink = 1 - self.cursor_blink
            self.last_blink = current_time

        super().update()

    def _submit(self) -> None:
        username = self.username_text.strip()
        password = self.password_text

        if not username:
            self.error_message = "Usuário não pode estar vazio"
            return
        if not password:
            self.error_message = "Senha não pode estar vazia"
            return
        if len(password) < 6:
            self.error_message = "Senha deve ter pelo menos 6 caracteres"
            return

        self.error_message = ""
        svc = self.app.auth_service
        if self.is_signup_mode:
            svc.signup(username, password)
        else:
            svc.login(username, password)

    def _on_auth_success(self, token: str) -> None:
        # Este callback é chamado tanto para login quanto signup
        self.app.current_scene = Scenes.MAIN_MENU

    def _on_auth_error(self, message: str) -> None:
        self.error_message = message

    def _on_toggle_mode(self) -> None:
        self.is_signup_mode = not self.is_signup_mode
        # NÃO limpa campos para preservar dados
        self.error_message = ""

    def _render_title(self) -> None:
        """Renderiza título da tela."""
        title = "Criar Conta" if self.is_signup_mode else "Login"
        font = pygame.font.SysFont("Arial", 48, bold=True)

        # Efeito glow
        for offset in [(2, 2), (-2, -2), (2, -2), (-2, 2)]:
            glow_surface = font.render(title, True, ACCENT_BLUE)
            glow_rect = glow_surface.get_rect(
                center=(self.title_pos[0] + offset[0], self.title_pos[1] + offset[1])
            )
            self.app.screen.blit(glow_surface, glow_rect)

        # Texto principal
        text_surface = font.render(title, True, WHITE)
        text_rect = text_surface.get_rect(center=self.title_pos)
        self.app.screen.blit(text_surface, text_rect)

    def _render_input_field(
        self, label: str, rect: pygame.Rect, text: str, is_focused: bool, is_password: bool
    ) -> None:
        """Renderiza campo de input."""
        # Cor da borda baseada no foco
        border_color = ACCENT_BLUE if is_focused else SLATE_GRAY
        bg_color = (25, 35, 50) if is_focused else (20, 30, 45)

        # Fundo do campo
        pygame.draw.rect(self.app.screen, bg_color, rect, border_radius=8)
        pygame.draw.rect(self.app.screen, border_color, rect, 2, border_radius=8)

        # Label
        if text or is_focused:
            font_label = pygame.font.SysFont("Arial", 14)
            label_surface = font_label.render(label, True, WHITE)
            self.app.screen.blit(label_surface, (rect.x, rect.y - 25))

        # Texto
        font_text = pygame.font.SysFont("Arial", 18)
        display_text = "*" * len(text) if is_password else text

        if not text and not is_focused:
            # Placeholder
            placeholder = f"Digite seu {label.lower()}"
            placeholder_surface = font_text.render(placeholder, True, SLATE_GRAY)
            text_rect = placeholder_surface.get_rect(midleft=(rect.x + 15, rect.centery))
            self.app.screen.blit(placeholder_surface, text_rect)
        else:
            # Texto real
            text_surface = font_text.render(display_text, True, WHITE)
            text_rect = text_surface.get_rect(midleft=(rect.x + 15, rect.centery))
            self.app.screen.blit(text_surface, text_rect)

            # Cursor piscante
            if is_focused and self.cursor_blink:
                cursor_x = text_rect.right + 2
                pygame.draw.line(
                    self.app.screen, WHITE, (cursor_x, rect.y + 12), (cursor_x, rect.bottom - 12), 2
                )

    def _render_button(
        self,
        rect: pygame.Rect,
        text: str,
        is_hover: bool,
        variant: str = "primary",
        is_disabled: bool = False,
    ) -> None:
        """Renderiza botão moderno."""
        if is_disabled:
            bg_color = (60, 60, 60)
            text_color = (120, 120, 120)
            border_color = (80, 80, 80)
        elif variant == "primary":
            bg_color = ACCENT_GREEN if is_hover else ACCENT_BLUE
            text_color = WHITE
            border_color = bg_color
        else:  # outline
            bg_color = (30, 40, 55) if is_hover else (20, 30, 45)
            text_color = WHITE
            border_color = ACCENT_BLUE

        # Fundo do botão
        pygame.draw.rect(self.app.screen, bg_color, rect, border_radius=6)
        pygame.draw.rect(self.app.screen, border_color, rect, 2, border_radius=6)

        # Texto do botão
        font = pygame.font.SysFont("Arial", 18, bold=True)
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=rect.center)
        self.app.screen.blit(text_surface, text_rect)

    def _render_modern_background(self) -> None:
        """Renderiza background moderno com gradiente."""
        screen_w, screen_h = self.app.screen.get_size()

        # Background base
        self.app.screen.fill(DARK_NAVY)

        # Gradiente diagonal otimizado
        for y in range(0, screen_h, 8):
            ratio = y / screen_h
            r = int(DARK_NAVY.r + (SLATE_GRAY.r - DARK_NAVY.r) * ratio * 0.2)
            g = int(DARK_NAVY.g + (SLATE_GRAY.g - DARK_NAVY.g) * ratio * 0.2)
            b = int(DARK_NAVY.b + (SLATE_GRAY.b - DARK_NAVY.b) * ratio * 0.2)
            for i in range(8):
                if y + i < screen_h:
                    pygame.draw.line(self.app.screen, (r, g, b), (0, y + i), (screen_w, y + i))

    def _update_effects(self) -> None:
        """Atualiza efeitos visuais."""
        current_time = pygame.time.get_ticks()

        # Adiciona partículas ocasionais
        if current_time - self.particle_timer > 3000:  # A cada 3 segundos
            import random

            self._add_particle(
                random.randint(0, self.app.screen.get_width()),
                random.randint(0, self.app.screen.get_height()),
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
                "dx": random.uniform(-1, 1),
                "dy": random.uniform(-1, 1),
                "color": color,
                "life": 120,
                "max_life": 120,
            }
        )

    def _render_particles(self) -> None:
        """Renderiza partículas de fundo."""
        for particle in self.particles:
            alpha = int(80 * (particle["life"] / particle["max_life"]))
            size = max(1, int(3 * (particle["life"] / particle["max_life"])))

            particle_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            color = (*particle["color"][:3], alpha)
            pygame.draw.circle(particle_surface, color, (size, size), size)
            self.app.screen.blit(particle_surface, (particle["x"] - size, particle["y"] - size))

    def _render_loading_indicator(self) -> None:
        """Renderiza indicador de carregamento."""
        cx, cy = self.app.screen_center
        loading_text = "Carregando..."
        font = pygame.font.SysFont("Arial", 18)
        text_surface = font.render(loading_text, True, ACCENT_BLUE)
        text_rect = text_surface.get_rect(center=(cx, cy + 280))
        self.app.screen.blit(text_surface, text_rect)

        # Spinner simples
        spinner_time = pygame.time.get_ticks() * 0.01
        for i in range(8):
            angle = (i / 8) * 2 * math.pi + spinner_time
            x = cx + 25 * math.cos(angle)
            y = cy + 300 + 25 * math.sin(angle)
            alpha = int(255 * (1 - i / 8))

            circle_surface = pygame.Surface((6, 6), pygame.SRCALPHA)
            color = (*ACCENT_BLUE[:3], alpha)
            pygame.draw.circle(circle_surface, color, (3, 3), 3)
            self.app.screen.blit(circle_surface, (x - 3, y - 3))

    def _render_error_message(self) -> None:
        """Renderiza mensagem de erro."""
        cx, cy = self.app.screen_center
        font = pygame.font.SysFont("Arial", 16)
        error_surface = font.render(self.error_message, True, ACCENT_RED)
        error_rect = error_surface.get_rect(center=(cx, cy + 280))

        # Fundo semi-transparente para erro
        bg_surface = pygame.Surface(
            (error_surface.get_width() + 20, error_surface.get_height() + 10), pygame.SRCALPHA
        )
        pygame.draw.rect(bg_surface, (*ACCENT_RED[:3], 30), bg_surface.get_rect(), border_radius=5)

        bg_rect = bg_surface.get_rect(center=error_rect.center)
        self.app.screen.blit(bg_surface, bg_rect)
        self.app.screen.blit(error_surface, error_rect)
