import pygame

from client.components import Button, State, Text
from client.scenes.base import BaseScene, Scenes
from core.constants import BLACK, FONT_MAP, FONT_SIZE_MAP, SIZE_MAP, VARIANT_MAP


class LoginScene(BaseScene):
    """
    Login / Signup embutido, sem usar componente externo de Input.
    Agora exibe label acima de cada campo em vez de placeholder.
    """

    BLINK_INTERVAL = 500  # ms

    def __init__(self, app) -> None:
        super().__init__(app)
        cx, cy = self.app.screen_center

        # valores dos campos
        self.username = ""
        self.password = ""

        # qual campo está ativo: "username", "password" ou None
        self.active_field: str | None = "username"

        # controle do cursor piscante
        self._cursor_visible = True
        self._last_blink = pygame.time.get_ticks()

        # configurações de input (tamanho e espessura de borda)
        coord, thickness = SIZE_MAP[False]["input"]["md"]
        self.input_size: tuple[int, int] = coord
        self.input_thickness: int = thickness

        # posições dos campos
        spacing = 80
        self.positions = {
            "username": (cx, cy - spacing / 2),
            "password": (cx, cy + spacing / 2),
        }

        # labels acima dos inputs
        label_offset = self.input_size[1] / 2 + 20
        ux, uy = self.positions["username"]
        px, py = self.positions["password"]
        self.label_username = Text(
            app.screen,
            position=(ux, int(uy - label_offset)),
            label="Username",
            text_type="subtitle",
            hover=False,
            is_topleft=False,
        )
        self.label_password = Text(
            app.screen,
            position=(px, int(py - label_offset)),
            label="Password",
            text_type="subtitle",
            hover=False,
            is_topleft=False,
        )

        # componentes de UI reutilizáveis
        self.back_btn = Button(
            app.screen,
            position=(cx - 100, cy + 150),
            label="Back",
            text_type="standard",
            variant="outline",
            size="sm",
            is_topleft=False,
            callback=lambda: setattr(self.app, "current_scene", Scenes.MAIN_MENU),
        )
        self.toggle_btn = Button(
            app.screen,
            position=(cx + 100, cy + 150),
            label="Sign-up",
            text_type="standard",
            variant="outline",
            size="sm",
            is_topleft=False,
            callback=self._on_toggle_mode,
        )
        self.loading_state = State(
            app.screen,
            position=(cx, cy + 100),
            label="Enviar",
            text_type="standard",
            is_topleft=False,
            callback=self._submit,
        )
        self.title_txt = Text(
            app.screen,
            position=(cx, cy - 200),
            label="Login",
            text_type="title",
            hover=False,
            is_topleft=False,
        )
        self.error_txt = Text(
            app.screen,
            position=(cx, cy + 200),
            label="",
            text_type="text",
            hover=False,
            is_topleft=False,
        )

        # callbacks de auth
        auth = app.auth_service
        auth.register_login_success_callback(self._on_auth_success)
        auth.register_login_error_callback(self._on_auth_error)

        # registra componentes para handle/update
        self.components = [
            self.back_btn,
            self.toggle_btn,
            self.loading_state,
            self.title_txt,
            self.error_txt,
            self.label_username,
            self.label_password,
        ]
        self.is_signup_mode = False
        self.error_message = ""

    def _draw_input(self, field: str) -> None:
        """Desenha o campo de texto 'field'."""
        surf = pygame.Surface(self.input_size, flags=pygame.SRCALPHA)
        rect = surf.get_rect(center=self.positions[field])

        # foco
        is_focused = self.active_field == field

        # cores
        colors = VARIANT_MAP[False][is_focused]["standard"]
        bg_col = colors["bg"]
        bd_col = colors["border"]
        text_col = colors["text"]

        # fundo e borda
        pygame.draw.rect(
            surf,
            bg_col,
            surf.get_rect().inflate(-self.input_thickness, -self.input_thickness),
            border_radius=5,
        )
        pygame.draw.rect(
            surf,
            bd_col,
            surf.get_rect(),
            width=self.input_thickness,
            border_radius=5,
        )

        # conteúdo
        val = getattr(self, field)
        display = val if (val or is_focused) else ""

        # máscara no password
        if field == "password":
            masked = "*" * len(self.password)
            display = masked + ("|" if is_focused and self._cursor_visible else "")
        else:
            if is_focused and self._cursor_visible:
                display += "|"

        # texto
        font_size = FONT_SIZE_MAP[is_focused]["standard"]["md"]
        font = pygame.font.Font(FONT_MAP["normal"], font_size)
        txt_surf = font.render(display, True, text_col)
        surf.blit(
            txt_surf,
            (10, (self.input_size[1] - txt_surf.get_height()) // 2),
        )

        # guardar rect para eventos
        setattr(self, f"{field}_rect", rect)
        self.app.screen.blit(surf, rect)

    def handle_event(self, event: pygame.event.Event) -> None:
        # navegação por Tab e setas
        if event.type == pygame.KEYDOWN and event.key in (
            pygame.K_TAB,
            pygame.K_DOWN,
            pygame.K_UP,
        ):
            fields = ["username", "password"]
            if self.active_field not in fields:
                self.active_field = fields[0]
            else:
                idx = fields.index(self.active_field)
                if event.key in (pygame.K_TAB, pygame.K_DOWN):
                    idx = (idx + 1) % len(fields)
                else:
                    idx = (idx - 1) % len(fields)
                self.active_field = fields[idx]
            return

        # clique para foco
        if event.type == pygame.MOUSEBUTTONDOWN:
            for fld in ("username", "password"):
                if getattr(self, f"{fld}_rect").collidepoint(event.pos):
                    self.active_field = fld
                    break
            else:
                self.active_field = None

        # digitação
        if self.active_field and event.type == pygame.KEYDOWN:
            fld = self.active_field
            if event.key == pygame.K_BACKSPACE:
                setattr(self, fld, getattr(self, fld)[:-1])
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._submit()
            elif event.unicode and event.unicode.isprintable():
                setattr(self, fld, getattr(self, fld) + event.unicode)

    def render(self) -> None:
        # fundo preto da base
        self.app.screen.fill(BLACK)

        # atualiza loading
        auth = self.app.auth_service
        self.loading_state.active = (
            auth.is_login_loading or auth.is_signup_loading or auth.is_current_user_loading
        )

        # texto de erro
        self.error_txt.label = self.error_message or ""

        # desenhar título e labels
        self.title_txt.render()
        self.label_username.render()
        self.label_password.render()

        # desenhar inputs
        self._draw_input("username")
        self._draw_input("password")

        # desenhar botões e erro
        for comp in (
            self.back_btn,
            self.toggle_btn,
            self.loading_state,
            self.error_txt,
        ):
            comp.render()

    def update(self) -> None:
        # blink cursor
        now = pygame.time.get_ticks()
        if now - self._last_blink >= self.BLINK_INTERVAL:
            self._cursor_visible = not self._cursor_visible
            self._last_blink = now

        # captura erros de auth
        auth = self.app.auth_service
        err = auth.get_signup_error() if self.is_signup_mode else auth.get_login_error()
        if err:
            self.error_message = err

        # desabilita envio se loading
        self.loading_state.is_disabled = self.loading_state.active

        super().update()

    def _submit(self) -> None:
        if not self.username.strip():
            self.error_message = "Username cannot be empty"
            return
        if not self.password:
            self.error_message = "Password cannot be empty"
            return
        if len(self.password) < 6:
            self.error_message = "Password must be at least 6 characters"
            return
        self.error_message = ""
        svc = self.app.auth_service
        if self.is_signup_mode:
            svc.signup(self.username, self.password)
        else:
            svc.login(self.username, self.password)

    def _on_auth_success(self, token: str) -> None:
        self.app.current_scene = Scenes.MAIN_MENU

    def _on_auth_error(self, message: str) -> None:
        self.error_message = message
        self.loading_state.is_disabled = False

    def _on_toggle_mode(self) -> None:
        self.is_signup_mode = not self.is_signup_mode
        self.toggle_btn.label = "Login" if self.is_signup_mode else "Sign-up"
        self.title_txt.label = "Cadastro" if self.is_signup_mode else "Login"
