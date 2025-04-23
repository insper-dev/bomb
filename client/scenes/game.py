import pygame

from client.game.player import Player
from client.scenes.base import BaseScene, Scenes
from client.services.game import GameService
from core.constants import BLOCKS, BOMB_COKING, EXPLOSION_PARTICLES, MODULE_SIZE, PURPLE
from core.models.game import UNDESTOYABLE_BOXES, GameState, GameStatus, MapBlockType


class GameScene(BaseScene):
    """
    Cena principal do jogo. Atualiza e renderiza o mapa,
    jogadores, bombas e explosões conforme o estado vindo do servidor.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self.service: GameService = app.game_service
        self.service.register_game_ended_callback(self._on_game_end)

        # Espera até o primeiro estado chegar
        while not self.service.state:
            pass

        # Calcula margem para centralizar o mapa
        self._calc_margin(self.service.state)

        # Instancia um Player para cada participante
        self.players = {
            pid: Player(self.service, self.margim, pid) for pid in self.service.state.players
        }

    @property
    def state(self) -> GameState | None:
        return self.service.state

    def _on_game_end(self, status: GameStatus, winner: str | None) -> None:
        # No próximo render() será trocada a cena
        ...

    def _calc_margin(self, state: GameState) -> None:
        w_tiles = len(state.map[0])
        h_tiles = len(state.map)
        x = self.app.screen_center[0] - w_tiles * MODULE_SIZE // 2
        y = self.app.screen_center[1] - h_tiles * MODULE_SIZE // 2
        self.margim = (x, y)

    def handle_event(self, event) -> None:
        # Encaminha apenas para o player local
        if event.type == pygame.KEYDOWN:
            user = self.app.auth_service.current_user
            if user and user.id in self.players:
                self.players[user.id].handle_event(event)
            # ESC ou ENTER retorna ao menu
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.service.stop()
                self.app.current_scene = Scenes.START

    def render(self) -> None:
        screen = self.app.screen
        screen.fill(PURPLE)

        if not self.state:
            return

        # Se o jogo acabou, muda de cena
        if self.state.status != GameStatus.PLAYING:
            self.service.stop()
            self.app.current_scene = Scenes.GAME_OVER
            return

        # 1) Desenha o mapa
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

        # 2) Grade opcional
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

        # 3) Jogadores
        for player in self.players.values():
            player.render()

        # 4) Bombas não explodidas (animação de cooking)
        for pstate in self.state.players.values():
            for bomb in pstate.bombs:
                if bomb.exploded_at is None:
                    # bomba ainda contando
                    bx = self.margim[0] + bomb.x * MODULE_SIZE
                    by = self.margim[1] + bomb.y * MODULE_SIZE
                    frame = (pygame.time.get_ticks() // 200) % len(BOMB_COKING)
                    screen.blit(BOMB_COKING[frame], (bx, by))

        # 5) Explosões (telegráfica em “cruz” com base em bomb.radius)
        for pstate in self.state.players.values():
            for bomb in pstate.bombs:
                if bomb.exploded_at:
                    # centro da explosão
                    cx = self.margim[0] + bomb.x * MODULE_SIZE
                    cy = self.margim[1] + bomb.y * MODULE_SIZE
                    # sprite central
                    screen.blit(EXPLOSION_PARTICLES["geo"][0], (cx, cy))

                    # Direções e seus índices para rotação dos sprites
                    directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # up, right, down, left

                    # Calcula os tiles afetados em cada direção uma vez só
                    explosion_tiles = {i: [] for i in range(4)}
                    for i, (dx, dy) in enumerate(directions):
                        current_tiles = []

                        # Percorre até o raio máximo ou encontrar obstáculo
                        for step in range(1, bomb.radius + 1):
                            tx = bomb.x + dx * step
                            ty = bomb.y + dy * step

                            # Verifica limites e obstáculos
                            if (
                                tx < 0
                                or ty < 0
                                or ty >= len(self.state.map)
                                or tx >= len(self.state.map[0])
                            ):
                                break

                            if self.state.map[ty][tx] in UNDESTOYABLE_BOXES:
                                break

                            # Adiciona tile à lista desta direção
                            current_tiles.append((tx, ty))

                            # Para em blocos destrutíveis após incluí-los
                            if self.state.map[ty][tx] in {
                                MapBlockType.WOODEN_BOX,
                                MapBlockType.SAND_BOX,
                            }:
                                break

                        # Armazena os tiles desta direção
                        explosion_tiles[i] = current_tiles

                    # Renderiza as explosões usando os tiles pré-calculados
                    for direction_idx, tiles in explosion_tiles.items():
                        for tx, ty in tiles:
                            px = self.margim[0] + tx * MODULE_SIZE
                            py = self.margim[1] + ty * MODULE_SIZE

                            # Check if this is the last tile in this direction
                            is_last_tile = bool(tiles) and (tx, ty) == tiles[-1]

                            # Choose and render the appropriate sprite
                            if is_last_tile:
                                # Último tile usa sprite de ponta na direção correta
                                # Rotação: up=0, right=1, down=2, left=3
                                sprite = EXPLOSION_PARTICLES["tip"][direction_idx]
                            else:
                                # Tiles intermediários usam sprite de cauda com mesma rotação
                                sprite = EXPLOSION_PARTICLES["tail"][direction_idx]

                            screen.blit(sprite, (px, py))
