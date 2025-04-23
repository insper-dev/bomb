import pygame

from client.game.player import Player
from client.scenes.base import BaseScene, Scenes
from client.services.game import GameService
from core.constants import (
    BLOCKS,
    BOMB_COKING,
    EXPLOSION_PARTICLES,
    MODULE_SIZE,
    PLAYERS_MAP,
    PURPLE,
)
from core.models.game import UNDESTOYABLE_BOXES, GameState, GameStatus, MapBlockType


class GameScene(BaseScene):
    """
    Cena principal: mapa + jogadores + bombas + explosões,
    com HUD no topo mostrando quem está contra quem.
    """

    HUD_HEIGHT = 50

    def __init__(self, app) -> None:
        super().__init__(app)
        self.service: GameService = app.game_service
        self.service.register_game_ended_callback(self._on_game_end)

        # aguarda estado inicial
        while not self.service.state:
            pass

        # calcula margin incluindo HUD
        self._calc_margin(self.service.state)

        # instancia players
        self.players = {
            pid: Player(self.service, self.margin, pid) for pid in self.service.state.players
        }

    @property
    def state(self) -> GameState | None:
        return self.service.state

    def _on_game_end(self, status: GameStatus, winner: str | None) -> None: ...

    def _calc_margin(self, state: GameState) -> None:
        screen_w, screen_h = self.app.screen.get_size()
        w_tiles = len(state.map[0])
        h_tiles = len(state.map)

        total_map_h = h_tiles * MODULE_SIZE
        x = (screen_w - w_tiles * MODULE_SIZE) // 2
        # reserva HUD_HEIGHT no topo, depois centraliza abaixo
        y = self.HUD_HEIGHT + (screen_h - self.HUD_HEIGHT - total_map_h) // 2

        self.margin = (x, y)

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            user = self.app.auth_service.current_user
            if user and user.id in self.players:
                self.players[user.id].handle_event(event)
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.service.stop()
                self.app.current_scene = Scenes.START

    def render(self) -> None:
        screen = self.app.screen
        screen_w, _ = screen.get_size()
        screen.fill(PURPLE)

        if not self.state:
            return

        # HUD no topo
        self._draw_hud(screen, screen_w)

        # se jogo terminou, troca de cena
        if self.state.status != GameStatus.PLAYING:
            self.service.stop()
            self.app.current_scene = Scenes.GAME_OVER
            return

        # 1) Desenha mapa
        for y, row in enumerate(self.state.map):
            for x, cell in enumerate(row):
                rect = pygame.Rect(
                    self.margin[0] + x * MODULE_SIZE,
                    self.margin[1] + y * MODULE_SIZE,
                    MODULE_SIZE,
                    MODULE_SIZE,
                )
                sprite = BLOCKS.get(cell)
                if sprite:
                    screen.blit(sprite, rect)

        # 2) Grade
        rows, cols = len(self.state.map), len(self.state.map[0])
        for i in range(rows + 1):
            pygame.draw.line(
                screen,
                (255, 255, 255),
                (self.margin[0], self.margin[1] + i * MODULE_SIZE),
                (self.margin[0] + cols * MODULE_SIZE, self.margin[1] + i * MODULE_SIZE),
            )
        for j in range(cols + 1):
            pygame.draw.line(
                screen,
                (255, 255, 255),
                (self.margin[0] + j * MODULE_SIZE, self.margin[1]),
                (self.margin[0] + j * MODULE_SIZE, self.margin[1] + rows * MODULE_SIZE),
            )

        # 3) Jogadores
        for player in self.players.values():
            player.render()

        # 4) Bombas (cooking)
        for pstate in self.state.players.values():
            for bomb in pstate.bombs:
                if bomb.exploded_at is None:
                    bx = self.margin[0] + bomb.x * MODULE_SIZE
                    by = self.margin[1] + bomb.y * MODULE_SIZE
                    frame = (pygame.time.get_ticks() // 200) % len(BOMB_COKING)
                    screen.blit(BOMB_COKING[frame], (bx, by))

        # 5) Explosões
        for pstate in self.state.players.values():
            for bomb in pstate.bombs:
                if bomb.exploded_at:
                    cx = self.margin[0] + bomb.x * MODULE_SIZE
                    cy = self.margin[1] + bomb.y * MODULE_SIZE
                    screen.blit(EXPLOSION_PARTICLES["geo"][0], (cx, cy))

                    directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]
                    tiles_by_dir = {i: [] for i in range(4)}
                    for i, (dx, dy) in enumerate(directions):
                        for step in range(1, bomb.radius + 1):
                            tx, ty = bomb.x + dx * step, bomb.y + dy * step
                            if (
                                tx < 0
                                or ty < 0
                                or ty >= rows
                                or tx >= cols
                                or self.state.map[ty][tx] in UNDESTOYABLE_BOXES
                            ):
                                break
                            tiles_by_dir[i].append((tx, ty))
                            if self.state.map[ty][tx] in {
                                MapBlockType.WOODEN_BOX,
                                MapBlockType.SAND_BOX,
                            }:
                                break
                    for dir_idx, tiles in tiles_by_dir.items():
                        for tx, ty in tiles:
                            px = self.margin[0] + tx * MODULE_SIZE
                            py = self.margin[1] + ty * MODULE_SIZE
                            is_last = tiles and (tx, ty) == tiles[-1]
                            part = "tip" if is_last else "tail"
                            sprite = EXPLOSION_PARTICLES[part][dir_idx]
                            screen.blit(sprite, (px, py))

    def _draw_hud(self, screen: pygame.Surface, screen_w: int) -> None:
        """Desenha a barra superior com 'A vs B' e miniaturas."""
        if not self.state:
            return
        # retângulo de fundo
        hud_rect = pygame.Rect(0, 0, screen_w, self.HUD_HEIGHT)
        pygame.draw.rect(screen, (30, 30, 30), hud_rect)

        # extrai os dois primeiros jogadores
        pids = list(self.state.players.keys())
        if len(pids) >= 2:
            a, b = self.state.players[pids[0]], self.state.players[pids[1]]
        else:
            return

        # texto central
        font = pygame.font.SysFont(None, 24)
        vs_text = f"{a.username}  vs  {b.username}"
        text_surf = font.render(vs_text, True, (255, 255, 255))
        txt_x = (screen_w - text_surf.get_width()) // 2
        txt_y = (self.HUD_HEIGHT - text_surf.get_height()) // 2
        screen.blit(text_surf, (txt_x, txt_y))

        # miniaturas (32x32)
        def draw_thumb(ps, x_pos) -> None:
            frames = PLAYERS_MAP[ps.skin]["down"]  # quadro neutro
            thumb = pygame.transform.scale(frames[0], (32, 32))
            y_pos = (self.HUD_HEIGHT - 32) // 2
            screen.blit(thumb, (x_pos, y_pos))

        draw_thumb(a, 10)
        draw_thumb(b, screen_w - 10 - 32)
