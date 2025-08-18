import pygame

from client.services.game import GameService
from core.constants import MODULE_SIZE, PLAYERS_MAP
from core.models.game import PlayerState
from core.types import PlayerDirectionState


class Player:
    """
    Representa um jogador na cena com interpolação suave de movimento
    para reduzir lag visual e melhorar a experiência do usuário.
    """

    def __init__(
        self,
        game_service: GameService,
        margin: tuple[int, int],
        player_id: str,
    ) -> None:
        # Serviço que mantém o estado do jogo e envia eventos ao servidor
        self.game_service = game_service
        self.app = game_service.app

        # Offset em pixels para centralizar o mapa na tela
        self.margin = margin

        # ID do jogador a quem esta instância corresponde
        self.player_id = player_id

        # Sistema de interpolação suave para reduzir lag visual
        self.visual_x = 0.0
        self.visual_y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.interpolation_speed = 0.15  # Velocidade da interpolação

        # Animação de sprite
        self.animation_frame = 0
        self.animation_timer = 0
        self.animation_speed = 150  # ms por frame

        # Cache do último estado conhecido
        self.last_server_x = 0
        self.last_server_y = 0

        # Buffer de input para responsividade
        self.pending_moves = []
        self.last_move_time = 0
        self.move_cooldown = 50  # ms entre movimentos

        # Inicializa posições visuais com posição inicial do servidor
        self._initialize_visual_position()

    def _initialize_visual_position(self) -> None:
        """Inicializa posições visuais com dados do servidor."""
        ps = self.player_state
        if ps:
            self.visual_x = ps.x
            self.visual_y = ps.y
            self.target_x = ps.x
            self.target_y = ps.y
            self.last_server_x = ps.x
            self.last_server_y = ps.y

    @property
    def player_state(self) -> PlayerState | None:
        """
        Retorna o PlayerState correspondente a este player_id,
        ou None se o estado ainda não estiver disponível.
        """
        state = self.game_service.state
        if not state:
            return None
        return state.players.get(self.player_id)

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Processa eventos com throttling para reduzir lag de input.
        """
        if event.type != pygame.KEYDOWN:
            return

        current = self.app.auth_service.current_user
        if not current or current.id != self.player_id:
            return

        current_time = pygame.time.get_ticks()

        # Throttling para movimentos
        if current_time - self.last_move_time < self.move_cooldown:
            return

        key_map: dict[int, PlayerDirectionState] = {
            pygame.K_UP: "up",
            pygame.K_DOWN: "down",
            pygame.K_LEFT: "left",
            pygame.K_RIGHT: "right",
        }

        if event.key in key_map:
            direction = key_map[event.key]
            # Predição local otimista para responsividade
            self._predict_movement(direction)
            self.game_service.send_move(direction)
            self.last_move_time = current_time
        elif event.key == pygame.K_SPACE:
            self.game_service.send_bomb()

    def _predict_movement(self, direction: PlayerDirectionState) -> None:
        """Predição local otimista do movimento para reduzir lag percebido."""
        ps = self.player_state
        if not ps:
            return

        # Calcula nova posição baseada na direção
        dx, dy = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}.get(
            direction, (0, 0)
        )

        # Atualiza posição visual instantaneamente
        new_x = max(0, min(ps.x + dx, 15))  # Limites básicos do mapa
        new_y = max(0, min(ps.y + dy, 11))

        self.target_x = new_x
        self.target_y = new_y

    def update(self) -> None:
        """Atualiza interpolação e animações."""
        ps = self.player_state
        if not ps:
            return

        # Detecta mudança no estado do servidor
        if ps.x != self.last_server_x or ps.y != self.last_server_y:
            self.target_x = ps.x
            self.target_y = ps.y
            self.last_server_x = ps.x
            self.last_server_y = ps.y

        # Interpolação suave da posição visual
        self.visual_x += (self.target_x - self.visual_x) * self.interpolation_speed
        self.visual_y += (self.target_y - self.visual_y) * self.interpolation_speed

        # Se muito próximo, assume posição final
        if abs(self.target_x - self.visual_x) < 0.01:
            self.visual_x = self.target_x
        if abs(self.target_y - self.visual_y) < 0.01:
            self.visual_y = self.target_y

        # Atualiza animação
        current_time = pygame.time.get_ticks()
        if current_time - self.animation_timer > self.animation_speed:
            frames = PLAYERS_MAP[ps.skin][ps.direction_state]
            self.animation_frame = (self.animation_frame + 1) % len(frames)
            self.animation_timer = current_time

    def render(self) -> None:
        """
        Renderização otimizada com interpolação suave e melhor feedback visual.
        """
        ps = self.player_state
        if ps is None:
            return

        # Usa posição interpolada para movimento suave
        x_px = self.visual_x * MODULE_SIZE + self.margin[0]
        y_px = self.visual_y * MODULE_SIZE + self.margin[1]

        # Seleção de sprite animado
        frames = PLAYERS_MAP[ps.skin][ps.direction_state]
        sprite = frames[self.animation_frame]

        # Renderização com shadow para profundidade
        current = self.app.auth_service.current_user
        is_local = current and current.id == self.player_id

        if is_local:
            # Sombra para jogador local
            shadow_color = (0, 0, 0, 80)
            shadow_surface = pygame.Surface((MODULE_SIZE + 4, MODULE_SIZE + 4), pygame.SRCALPHA)
            shadow_surface.fill(shadow_color)
            self.app.screen.blit(shadow_surface, (x_px - 2, y_px + 2))

        # Sprite principal
        self.app.screen.blit(sprite, (x_px, y_px))

        # Contorno melhorado para jogador local
        if is_local:
            rect = sprite.get_rect(topleft=(x_px, y_px))
            # Gradiente dourado pulsante
            pulse = abs(pygame.time.get_ticks() % 1000 - 500) / 500.0
            gold_intensity = int(200 + 55 * pulse)
            gold_color = (gold_intensity, int(gold_intensity * 0.84), 0)
            pygame.draw.rect(self.app.screen, gold_color, rect, width=3)

        # Indicador de vida/status se necessário
        if hasattr(ps, "health") and ps.health < 100:
            self._render_health_bar(x_px, y_px - 8, ps.health)

    def _render_health_bar(self, x: float, y: float, health: int) -> None:
        """Renderiza barra de vida sobre o jogador."""
        bar_width = MODULE_SIZE
        bar_height = 4

        # Fundo da barra
        bg_rect = pygame.Rect(x, y, bar_width, bar_height)
        pygame.draw.rect(self.app.screen, (60, 60, 60), bg_rect)

        # Barra de vida
        health_width = int((health / 100) * bar_width)
        if health_width > 0:
            health_color = (
                (255, 0, 0) if health < 30 else (255, 255, 0) if health < 70 else (0, 255, 0)
            )
            health_rect = pygame.Rect(x, y, health_width, bar_height)
            pygame.draw.rect(self.app.screen, health_color, health_rect)
