import pygame

from client.services.game import GameService
from core.constants import MODULE_SIZE, PLAYERS_MAP, MapBlockType
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
        self.interpolation_speed = 0.2  # Aumentado para resposta mais rápida

        # Animação de sprite
        self.animation_frame = 0
        self.animation_timer = 0
        self.animation_speed = 120  # Reduzido para animação mais fluida

        # Cache do último estado conhecido
        self.last_server_x = 0
        self.last_server_y = 0
        self.last_server_timestamp = 0

        # Buffer de input para responsividade
        self.pending_moves = []
        self.last_move_time = 0
        self.move_cooldown = 100  # Aumentado para reduzir spam

        # Sistema de correção de posição
        self.correction_threshold = 1.5  # Distância para forçar correção
        self.last_correction_time = 0

        # Outline pulsante para jogador local
        self.outline_timer = 0
        self.outline_interval = 500  # Intervalo de pulsação

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
        Processa eventos com throttling e validação melhorados.
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

            # Validação de movimento antes de enviar
            if self._can_move(direction):
                # Predição local mais conservadora
                self._predict_movement(direction)
                self.game_service.send_move(direction)
                self.last_move_time = current_time

                # Adiciona movimento ao buffer para reconciliação
                self.pending_moves.append({"direction": direction, "timestamp": current_time})

                # Limpa movimentos antigos do buffer
                self._clean_pending_moves(current_time)

        elif event.key == pygame.K_SPACE:
            # Throttling para bombas também
            if current_time - self.last_move_time < self.move_cooldown // 2:
                return
            self.game_service.send_bomb()
            self.last_move_time = current_time

    def _can_move(self, direction: PlayerDirectionState) -> bool:
        """Valida se o movimento é possível baseado no estado atual."""
        ps = self.player_state
        if not ps:
            return False

        # Calcula nova posição
        dx, dy = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}.get(
            direction, (0, 0)
        )

        # Calcula nova posição baseada na direção
        new_x = ps.x + dx
        new_y = ps.y + dy

        # Obtem o mapa atual do estado do jogo (se existir)
        map = self.game_service.state.map if self.game_service.state else None
        if map:
            # Verifica limites do mapa
            lim_x = len(map[0])
            lim_y = len(map)

            # Verifica se a nova posição é válida dentro do mapa
            if new_x < 0 or new_x >= lim_x or new_y < 0 or new_y >= lim_y:
                return False

            # Verifica se o espaço é vazio ou não):
            space = map[new_y][new_x]
            if not (space == MapBlockType.EMPTY or space is None):
                return False
        else:
            # Se não houver mapa, assume que o movimento é válido com limites básicos
            # Verifica limites básicos do mapa
            if not (0 <= new_x <= 15 and 0 <= new_y <= 11):
                return False

        return True

    def _predict_movement(self, direction: PlayerDirectionState) -> None:
        """Predição local mais conservadora do movimento."""
        ps = self.player_state
        if not ps:
            return

        # Calcula nova posição baseada na direção
        dx, dy = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}.get(
            direction, (0, 0)
        )

        # Aplica predição apenas se a diferença atual for pequena
        current_diff = abs(self.target_x - ps.x) + abs(self.target_y - ps.y)
        if current_diff < 0.5:  # Só prediz se estiver sincronizado
            new_x = max(0, min(ps.x + dx, 15))
            new_y = max(0, min(ps.y + dy, 11))

            self.target_x = new_x
            self.target_y = new_y

    def _clean_pending_moves(self, current_time: int) -> None:
        """Remove movimentos antigos do buffer."""
        # Remove movimentos com mais de 2 segundos
        self.pending_moves = [
            move for move in self.pending_moves if current_time - move["timestamp"] < 2000
        ]

    def update(self) -> None:
        """Atualiza interpolação, animações e reconciliação."""
        ps = self.player_state
        if not ps:
            return

        current_time = pygame.time.get_ticks()

        # Detecta mudança significativa no estado do servidor
        server_moved = ps.x != self.last_server_x or ps.y != self.last_server_y

        if server_moved:
            # Calcula distância da discrepância
            distance = ((ps.x - self.target_x) ** 2 + (ps.y - self.target_y) ** 2) ** 0.5

            # Se a discrepância for muito grande, força correção
            if distance > self.correction_threshold:
                self.target_x = ps.x
                self.target_y = ps.y
                self.visual_x = ps.x
                self.visual_y = ps.y
                self.last_correction_time = current_time
            else:
                # Atualização suave para pequenas discrepâncias
                self.target_x = ps.x
                self.target_y = ps.y

            self.last_server_x = ps.x
            self.last_server_y = ps.y
            self.last_server_timestamp = current_time

        # Interpolação suave da posição visual
        lerp_speed = self.interpolation_speed

        # Acelera interpolação se estiver muito longe do target
        distance_to_target = abs(self.target_x - self.visual_x) + abs(self.target_y - self.visual_y)
        if distance_to_target > 0.5:
            lerp_speed *= 2  # Acelera para alcançar rapidamente

        self.visual_x += (self.target_x - self.visual_x) * lerp_speed
        self.visual_y += (self.target_y - self.visual_y) * lerp_speed

        # Snap para posição final se muito próximo
        if abs(self.target_x - self.visual_x) < 0.02:
            self.visual_x = self.target_x
        if abs(self.target_y - self.visual_y) < 0.02:
            self.visual_y = self.target_y

        # Atualiza animação baseada no movimento
        self._update_animation(current_time)

    def _update_animation(self, current_time: int) -> None:
        """Atualiza animação baseada no estado de movimento."""
        ps = self.player_state
        if not ps:
            return

        # Determina se está se movendo
        is_moving = (
            abs(self.target_x - self.visual_x) > 0.02 or abs(self.target_y - self.visual_y) > 0.02
        )

        # Ajusta velocidade da animação baseada no movimento
        anim_speed = self.animation_speed if is_moving else self.animation_speed * 2

        if current_time - self.animation_timer > anim_speed:
            frames = PLAYERS_MAP[ps.skin][ps.direction_state]
            if is_moving:
                self.animation_frame = (self.animation_frame + 1) % len(frames)
            else:
                # Para em frame neutro quando parado
                self.animation_frame = 0
            self.animation_timer = current_time

    def render(self) -> None:
        """
        Renderização otimizada com melhor feedback visual.
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

        # Feedback visual melhorado
        current = self.app.auth_service.current_user
        is_local = current and current.id == self.player_id

        # Renderização com efeitos -- desativado por enquanto
        # if is_local:
        #     self._render_local_player_effects(x_px, y_px)

        # Sprite principal
        self.app.screen.blit(sprite, (x_px, y_px))

        # Contorno para jogador local
        if is_local:
            self._render_local_player_outline(sprite, x_px, y_px)
        else:
            self._render_enemy_outline(sprite, x_px, y_px)

        # Indicadores de status -- desativado por enquanto
        self._render_status_indicators(x_px, y_px, ps)

    def _render_local_player_effects(self, x_px: float, y_px: float) -> None:
        """Renderiza efeitos para o jogador local."""
        # Sombra suave
        shadow_size = MODULE_SIZE + 6
        shadow_surface = pygame.Surface((shadow_size, shadow_size), pygame.SRCALPHA)

        # Gradient shadow
        for i in range(3):
            alpha = 60 - i * 15
            radius = (shadow_size // 2) - i
            pygame.draw.circle(
                shadow_surface, (0, 0, 0, alpha), (shadow_size // 2, shadow_size // 2), radius
            )

        self.app.screen.blit(shadow_surface, (x_px - 3, y_px + 1))

    def __get_outline_color(self, cor, sprite) -> pygame.Surface:
        mask = pygame.mask.from_surface(sprite)
        surface = pygame.Surface((mask.get_size()), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))  # Cor dour
        outline = mask.outline()
        for point in outline:
            surface.set_at(point, cor)
        return surface

    def _render_local_player_outline(
        self, sprite: pygame.Surface, x_px: float, y_px: float
    ) -> None:
        """Renderiza contorno dourado para jogador local."""
        rect = sprite.get_rect(topleft=(x_px, y_px))

        # Efeito pulsante
        current_time = pygame.time.get_ticks()
        pulse = abs((current_time % 1250) - 750) / 750.0
        blue_intensity = int(180 + 75 * pulse)

        # Gradiente dourado
        blue_color = (blue_intensity * 0.1, int(blue_intensity * 0.1), int(blue_intensity))

        # Contorno Azul
        outline = self.__get_outline_color(blue_color, sprite)
        self.app.screen.blit(outline, rect.topleft)

    def _render_enemy_outline(self, sprite: pygame.Surface, x_px: float, y_px: float) -> None:
        """Renderiza contorno vermelho para jogadores inimigos."""
        rect = sprite.get_rect(topleft=(x_px, y_px))

        # Efeito pulsante
        current_time = pygame.time.get_ticks()
        pulse = abs((current_time % 1250) - 750) / 750.0
        red_intensity = int(180 + 75 * pulse)

        # Gradiente vermelho
        red_color = (red_intensity, int(red_intensity * 0.1), int(red_intensity * 0.1))

        # Red mask outline
        outline = self.__get_outline_color(red_color, sprite)
        self.app.screen.blit(outline, rect.topleft)

    def _render_status_indicators(self, x_px: float, y_px: float, ps: PlayerState) -> None:
        """Renderiza indicadores de status do jogador."""
        # Indicador de lag/sincronização
        current_time = pygame.time.get_ticks()
        if current_time - self.last_correction_time < 1000:  # Mostra por 1 segundo após correção
            # Pequeno indicador vermelho para mostrar correção de posição
            indicator_surface = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(indicator_surface, (255, 50, 50, 180), (3, 3), 3)
            self.app.screen.blit(indicator_surface, (x_px + MODULE_SIZE - 8, y_px - 8))

        # Barra de vida se implementada no futuro
        if hasattr(ps, "health") and ps.health < 100:
            self._render_health_bar(x_px, y_px - 10, ps.health)

    def _render_health_bar(self, x: float, y: float, health: int) -> None:
        """Renderiza barra de vida melhorada sobre o jogador."""
        bar_width = MODULE_SIZE
        bar_height = 6

        # Fundo da barra com bordas
        bg_rect = pygame.Rect(x - 1, y - 1, bar_width + 2, bar_height + 2)
        pygame.draw.rect(self.app.screen, (20, 20, 20), bg_rect)

        inner_rect = pygame.Rect(x, y, bar_width, bar_height)
        pygame.draw.rect(self.app.screen, (60, 60, 60), inner_rect)

        # Barra de vida com gradiente
        health_width = int((health / 100) * bar_width)
        if health_width > 0:
            # Cores baseadas na vida
            if health < 25:
                color = (255, 50, 50)  # Vermelho crítico
            elif health < 50:
                color = (255, 150, 50)  # Laranja
            elif health < 75:
                color = (255, 255, 50)  # Amarelo
            else:
                color = (50, 255, 50)  # Verde

            health_rect = pygame.Rect(x, y, health_width, bar_height)
            pygame.draw.rect(self.app.screen, color, health_rect)

            # Brilho na barra
            if health_width > 2:
                highlight_rect = pygame.Rect(x, y, health_width, 2)
                highlight_color = tuple(min(255, c + 40) for c in color)
                pygame.draw.rect(self.app.screen, highlight_color, highlight_rect)
