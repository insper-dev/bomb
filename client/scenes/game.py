import pygame

from client.game.player import Player
from client.scenes.base import BaseScene, Scenes
from client.services.game import GameService
from core.constants import BLOCKS, BOMB_COKING, EXPLOSION_PARTICLES, MODULE_SIZE, PURPLE
from core.models.game import GameState, GameStatus


class GameScene(BaseScene):
    """
    Cena principal do jogo. Atualiza e renderiza o mapa,
    jogadores e bombas conforme o estado vindo do servidor.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self.service: GameService = app.game_service
        self.service.register_game_ended_callback(self._on_game_end)

        # Espera o primeiro state ser carregado
        while not self.service.state:
            pass

        # Calcula margem para centralizar o mapa
        self._calc_margin(self.service.state)

        # Cria instâncias de Player para cada participante
        self.players = {
            pid: Player(self.service, self.margim, pid) for pid in self.service.state.players
        }

    @property
    def state(self) -> GameState | None:
        return self.service.state

    def _on_game_end(self, status: GameStatus, winner: str | None) -> None:
        # Apenas troca de cena ou exibe mensagem
        self.service.stop()
        self.app.current_scene = Scenes.START

    def _calc_margin(self, state: GameState) -> None:
        # Centraliza o grid na tela
        w_tiles = len(state.map[0])
        h_tiles = len(state.map)
        x = self.app.screen_center[0] - w_tiles * MODULE_SIZE // 2
        y = self.app.screen_center[1] - h_tiles * MODULE_SIZE // 2
        self.margim = (x, y)

    def handle_event(self, event) -> None:
        if event.type in (pygame.KEYDOWN,):
            # encaminha para cada Player (usa só o atual dentro de Player.handle_event)
            user = self.app.auth_service.current_user
            if user and user.id in self.players:
                self.players[user.id].handle_event(event)

            # ESC ou RETURN volta ao menu
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.service.stop()
                self.app.current_scene = Scenes.START

    def render(self) -> None:
        screen = self.app.screen
        screen.fill(PURPLE)

        if not self.state:
            return

        # Desenha cada célula do mapa
        for y, row in enumerate(self.state.map):
            for x, cell in enumerate(row):
                rect = pygame.Rect(
                    self.margim[0] + x * MODULE_SIZE,
                    self.margim[1] + y * MODULE_SIZE,
                    MODULE_SIZE,
                    MODULE_SIZE,
                )
                sprite = BLOCKS.get(cell)
                if sprite:
                    screen.blit(sprite, rect)

        # Desenha grid opcional
        for y in range(len(self.state.map) + 1):
            pygame.draw.line(
                screen,
                (255, 255, 255),
                (self.margim[0], self.margim[1] + y * MODULE_SIZE),
                (
                    self.margim[0] + len(self.state.map[0]) * MODULE_SIZE,
                    self.margim[1] + y * MODULE_SIZE,
                ),
            )
        for x in range(len(self.state.map[0]) + 1):
            pygame.draw.line(
                screen,
                (255, 255, 255),
                (self.margim[0] + x * MODULE_SIZE, self.margim[1]),
                (
                    self.margim[0] + x * MODULE_SIZE,
                    self.margim[1] + len(self.state.map) * MODULE_SIZE,
                ),
            )

        # Renderiza todas as Players (teleporte imediato)
        for player in self.players.values():
            player.render()

        # Renderiza as bombas conforme o estado do servidor
        for pstate in self.state.players.values():
            for bomb in pstate.bombs:
                bx = self.margim[0] + bomb.x * MODULE_SIZE
                by = self.margim[1] + bomb.y * MODULE_SIZE
                rect = pygame.Rect(bx, by, MODULE_SIZE, MODULE_SIZE)

                if bomb.exploded_at:
                    # explosão
                    screen.blit(EXPLOSION_PARTICLES["geo"][0], rect)
                    for i, (dx, dy) in enumerate([(0, -1), (1, 0), (0, 1), (-1, 0)]):
                        tip_rect = rect.move(dx * MODULE_SIZE, dy * MODULE_SIZE)
                        screen.blit(EXPLOSION_PARTICLES["tip"][i], tip_rect)
                else:
                    # bomba cronometrada
                    frame = (pygame.time.get_ticks() // 200) % len(BOMB_COKING)
                    screen.blit(BOMB_COKING[frame], rect)
