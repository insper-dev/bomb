import pygame

from client.services.game import GameService
from core.constants import MODULE_SIZE, PLAYERS_MAP
from core.models.game import PlayerState
from core.types import PlayerDirectionState


class Player:
    """
    Representa um jogador na cena. Cada instância lida com um único player_id,
    renderizando sua posição e tratando eventos de teclado apenas para o player local.
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
        Processa eventos de tecla apenas para o jogador local.
        Seta movimento ou coloca bomba via GameService.
        """
        # Só reagir a pressionamentos de tecla
        if event.type != pygame.KEYDOWN:
            return

        # Ignorar eventos de outros players
        current = self.app.auth_service.current_user
        if not current or current.id != self.player_id:
            return

        # Mapeia setas para direções
        key_map: dict[int, PlayerDirectionState] = {
            pygame.K_UP: "up",
            pygame.K_DOWN: "down",
            pygame.K_LEFT: "left",
            pygame.K_RIGHT: "right",
        }

        if event.key in key_map:
            # Envia evento de movimento ao servidor
            self.game_service.send_move(key_map[event.key])
        elif event.key == pygame.K_SPACE:
            # Envia evento de plantio de bomba ao servidor
            self.game_service.send_bomb()

    def render(self) -> None:
        """
        Desenha o sprite do jogador na tela, usando
        posição e direção obtidas do estado do servidor.
        """
        ps = self.player_state
        if ps is None:
            return

        # Seleciona o primeiro quadro (sem animação) para a direção atual
        frames = PLAYERS_MAP[ps.skin][ps.direction_state]
        sprite = frames[0]

        # Converte coordenada de tile para pixels e aplica margem
        x_px = ps.x * MODULE_SIZE + self.margin[0]
        y_px = ps.y * MODULE_SIZE + self.margin[1]

        self.app.screen.blit(sprite, (x_px, y_px))
