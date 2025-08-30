from math import sin

import pygame

from client.game.bomb import Bomb
from client.game.player import Player
from client.scenes.base import BaseScene, Scenes
from client.services.game import GameService
from core.constants import (
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_RED,
    ACCENT_YELLOW,
    BLOCKS,
    DARK_NAVY,
    EARTH,
    EXPLOSION_ORANGE,
    EXPLOSION_PARTICLES,
    LIGHT_GRAY,
    MODULE_SIZE,
    PLAYERS_MAP,
    POWER_UPS,
    SLATE_GRAY,
    SONGS,
    SOUNDS,
    WHITE,
)
from core.models.game import GameState, GameStatus, MapBlockType, PowerUpType


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
            # Adiciona uma pequena pausa para evitar consumo excessivo de CPU
            pygame.time.wait(10)
            # Processa eventos básicos para evitar travamento da janela
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.app.running = False
                    return

        # calcula margin incluindo HUD
        self._calc_margin(self.service.state)

        # instancia players
        self.players = {
            pid: Player(self.service, self.margin, pid) for pid in self.service.state.players
        }

        # instancia bombas
        self.bombs = []  # Lista para gerenciar bombas ativas

        # Tema atual do jogo
        self.theme = self.service.state.game_theme

        # Loading music
        pygame.mixer.music.load(SONGS[self.theme])
        pygame.mixer.music.set_volume(0.3)
        pygame.mixer.music.play(-1)  # Loop infinito

        # Cache para otimização de renderização
        self._map_cache = None
        self._grid_cache = None
        self._need_map_refresh = True

        # Sistema de detecção de mudanças para sincronização
        self._last_state_bomb_count = 0
        self._last_state_hash = ""
        self._last_explosion_count = 0

        # Cache de assets para performance
        self._assets_cache = {}
        self._precache_assets()

        # FPS counter para debug
        self.fps_font = pygame.font.SysFont("Arial", 16)
        self.show_fps = True

        # Dirty rectangles para renderização otimizada
        self._dirty_rects = []
        self._last_rendered_positions = {}

        # instancia temporizador
        self._init_timer()

    @property
    def state(self) -> GameState | None:
        return self.service.state

    def _init_timer(self) -> None:
        """Inicializa o temporizador do jogo."""
        self.start_time = pygame.time.get_ticks()
        if self.state is not None:
            self.limited_time = self.state.time_start

    @property
    def elapsed_time(self) -> int:
        return pygame.time.get_ticks() - self.start_time

    def _on_game_end(self, status: GameStatus, winner: str | None) -> None:
        """Callback chamado quando o jogo termina."""
        print(f"[INFO] Jogo terminou - Status: {status}, Winner: {winner}")
        self.service.stop()
        self.app.current_scene = Scenes.GAME_OVER

    def _calc_margin(self, state: GameState) -> None:
        screen_w, screen_h = self.app.screen.get_size()
        if self.state is None:
            self.margin = (0, 0)
            return
        w_tiles = self.state.map_state.width
        h_tiles = self.state.map_state.height

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
        screen_w, screen_h = screen.get_size()

        # Background gradiente moderno
        self._render_gradient_background(screen, screen_w, screen_h)

        if not self.state:
            return

        # --- DETECÇÃO DE MUDANÇAS CRÍTICAS PARA SINCRONIZAÇÃO ---
        self._detect_state_changes()

        # HUD melhorado
        self._draw_modern_hud(screen, screen_w)

        # se jogo terminou, troca de cena
        if self.state.status != GameStatus.PLAYING:
            self.service.stop()
            self.app.current_scene = Scenes.GAME_OVER
            return

        # 1) Mapa com cache otimizado
        self._render_map_optimized(screen)

        # 2) Grade sutil --removed
        # self._render_subtle_grid(screen)

        # 3 Renderiza power-ups
        self._render_power_ups(screen)

        # 4) Bombas com efeitos melhorados
        self._render_bombs_enhanced(screen)

        # 5) Jogadores com interpolação
        for player in self.players.values():
            player.update()
            player.render()

        # 6) Explosões com partículas melhoradas
        self._render_explosions_enhanced(screen)

        # 7) FPS counter (debug)
        if self.show_fps:
            self._render_fps(screen)

    def _render_gradient_background(self, screen: pygame.Surface, w: int, h: int) -> None:
        """Renderiza background com gradiente moderno."""
        # Gradiente simples de cima para baixo
        for y in range(h):
            ratio = y / h
            r = int(DARK_NAVY.r + (EARTH.r - DARK_NAVY.r) * ratio)
            g = int(DARK_NAVY.g + (EARTH.g - DARK_NAVY.g) * ratio)
            b = int(DARK_NAVY.b + (EARTH.b - DARK_NAVY.b) * ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (w, y))

    def _render_map_optimized(self, screen: pygame.Surface) -> None:
        """Renderização otimizada do mapa com cache."""
        if self._need_map_refresh or not self._map_cache:
            self._build_map_cache()
            self._need_map_refresh = False

        if self._map_cache:
            screen.blit(self._map_cache, self.margin)

    def _build_map_cache(self) -> None:
        """Constrói cache do mapa para melhor performance."""
        if not self.state:
            return

        if not self.theme:
            return

        sprites = BLOCKS.get(self.theme)
        if not sprites:
            return

        rows, cols = self.state.map_state.height, self.state.map_state.width
        # Cria uma superfície invísivel para o cache
        cache_surface = pygame.Surface((cols * MODULE_SIZE, rows * MODULE_SIZE), pygame.SRCALPHA)

        for y, row in enumerate(self.state.map_state.layout):
            for x, cell in enumerate(row):
                rect = pygame.Rect(x * MODULE_SIZE, y * MODULE_SIZE, MODULE_SIZE, MODULE_SIZE)
                sprite = sprites.get(cell)
                if sprite and sprite != MapBlockType.EMPTY:
                    if isinstance(sprite, pygame.Surface):
                        cache_surface.blit(sprite, rect)
                    else:
                        color = sprite
                        pygame.draw.rect(cache_surface, color, rect)

        self._map_cache = cache_surface

    def _render_subtle_grid(self, screen: pygame.Surface) -> None:
        """Grade sutil e moderna."""
        if not self.state:
            return

        rows, cols = self.state.map_state.height, self.state.map_state.width
        grid_color = (*SLATE_GRAY[:3], 60)  # Semi-transparente

        # Linhas horizontais
        for i in range(rows + 1):
            y = self.margin[1] + i * MODULE_SIZE
            pygame.draw.line(
                screen, grid_color, (self.margin[0], y), (self.margin[0] + cols * MODULE_SIZE, y), 1
            )

        # Linhas verticais
        for j in range(cols + 1):
            x = self.margin[0] + j * MODULE_SIZE
            pygame.draw.line(
                screen, grid_color, (x, self.margin[1]), (x, self.margin[1] + rows * MODULE_SIZE), 1
            )

    def _render_bombs_enhanced(self, screen: pygame.Surface) -> None:
        """Bombas com efeitos visuais melhorados."""
        # current_time = pygame.time.get_ticks()

        for pstate in self.state.players.values():
            for bomb in pstate.bombs:
                if bomb.exploded_at is None:
                    if not any(
                        b.position[0] == bomb.x and b.position[1] == bomb.y for b in self.bombs
                    ):
                        new_bomb = Bomb(
                            screen,
                            (bomb.x, bomb.y),
                            self.margin,
                            bomb.id,
                            explosion_time=pstate.bomb_delay,
                        )
                        self.bombs.append(new_bomb)
        for bomb in self.bombs:
            bomb.render()

    def _render_explosions_enhanced(self, screen: pygame.Surface) -> None:
        """Explosões com efeitos de partículas melhorados."""
        if not self.state:
            return

        rows, cols = self.state.map_state.height, self.state.map_state.width

        for pstate in self.state.players.values():
            for bomb in pstate.bombs:
                if bomb.exploded_at:
                    cx = self.margin[0] + bomb.x * MODULE_SIZE
                    cy = self.margin[1] + bomb.y * MODULE_SIZE

                    self.bombs = [b for b in self.bombs if b.id != bomb.id]

                    # Toca som de explosão
                    explosion_sound = pygame.mixer.Sound(SOUNDS["bomb_explosion"])
                    explosion_sound.set_volume(0.1)
                    explosion_sound.play()

                    # Centro da explosão com glow
                    glow_size = MODULE_SIZE + 20
                    glow_surface = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                    pygame.draw.circle(
                        glow_surface,
                        (*EXPLOSION_ORANGE[:3], 150),
                        (glow_size // 2, glow_size // 2),
                        glow_size // 2,
                    )
                    screen.blit(glow_surface, (cx - 10, cy - 10))
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
                                or self.state.map_state.get_block_type(tx, ty)
                                == MapBlockType.UNBREAKABLE
                            ):
                                break
                            tiles_by_dir[i].append((tx, ty))
                            if (
                                self.state.map_state.get_block_type(tx, ty)
                                == MapBlockType.BREAKABLE
                            ):
                                break

                    for dir_idx, tiles in tiles_by_dir.items():
                        for tx, ty in tiles:
                            px = self.margin[0] + tx * MODULE_SIZE
                            py = self.margin[1] + ty * MODULE_SIZE
                            is_last = tiles and (tx, ty) == tiles[-1]
                            part = "tip" if is_last else "tail"

                            # Fix direções
                            fixed_dir_idx = dir_idx
                            if dir_idx == 1:
                                fixed_dir_idx = 3
                            elif dir_idx == 3:
                                fixed_dir_idx = 1

                            # Glow para explosão
                            glow_surface = pygame.Surface(
                                (MODULE_SIZE + 10, MODULE_SIZE + 10), pygame.SRCALPHA
                            )
                            pygame.draw.circle(
                                glow_surface,
                                (*EXPLOSION_ORANGE[:3], 100),
                                (MODULE_SIZE // 2 + 5, MODULE_SIZE // 2 + 5),
                                MODULE_SIZE // 2 + 5,
                            )
                            screen.blit(glow_surface, (px - 5, py - 5))

                            sprite = EXPLOSION_PARTICLES[part][fixed_dir_idx]
                            screen.blit(sprite, (px, py))

    def _render_power_ups(self, screen: pygame.Surface) -> None:
        """Renderiza power-ups no mapa."""
        if not self.state:
            return
        power_ups = self.state.map_state.objects

        floating_var = sin(pygame.time.get_ticks() * 0.005) * 5

        for pu in power_ups:
            pu_type = pu.type
            pu_x, pu_y = pu.position
            if (
                pu_type in PowerUpType
                and self.state.map_state.layout[pu_y][pu_x] == MapBlockType.FLOOR
            ):
                # Posição base do power-up
                pu_screen_x = self.margin[0] + pu_x * MODULE_SIZE
                pu_screen_y = self.margin[1] + pu_y * MODULE_SIZE + floating_var

                # Desenha o power-up por cima da sombra
                sprite = POWER_UPS[pu_type]
                screen.blit(sprite, (pu_screen_x, pu_screen_y))

    def _render_fps(self, screen: pygame.Surface) -> None:
        """Contador de FPS avançado com métricas detalhadas."""
        fps = int(self.app.clock.get_fps())
        fps_color = ACCENT_GREEN if fps >= 50 else ACCENT_YELLOW if fps >= 30 else ACCENT_RED
        fps_text = self.fps_font.render(f"FPS: {fps}", True, fps_color)
        screen.blit(fps_text, (10, 10 + self.margin[1] - 20))

        # Indicador de latência
        latency = self.service._ping_stats["current_ping"] * 1000  # Convert to ms
        quality = self.service.connection_quality

        # Cor baseada na qualidade
        if quality == "Excelente":
            latency_color = ACCENT_GREEN
        elif quality == "Boa":
            latency_color = ACCENT_BLUE
        elif quality == "Regular":
            latency_color = ACCENT_YELLOW
        else:
            latency_color = ACCENT_RED

        latency_text = self.fps_font.render(
            f"Ping: {latency:.0f}ms ({quality})", True, latency_color
        )
        screen.blit(latency_text, (10, 30 + self.margin[1] - 20))

    def _draw_modern_hud(self, screen: pygame.Surface, screen_w: int) -> None:
        """HUD moderno e elegante."""
        if not self.state:
            return

        # Background com gradiente
        hud_rect = pygame.Rect(0, 0, screen_w, self.HUD_HEIGHT)  # noqa: F841
        for y in range(self.HUD_HEIGHT):
            ratio = y / self.HUD_HEIGHT
            r = int(DARK_NAVY.r + (SLATE_GRAY.r - DARK_NAVY.r) * ratio)
            g = int(DARK_NAVY.g + (SLATE_GRAY.g - DARK_NAVY.g) * ratio)
            b = int(DARK_NAVY.b + (SLATE_GRAY.b - DARK_NAVY.b) * ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (screen_w, y))

        # Borda inferior sutil
        pygame.draw.line(
            screen, ACCENT_BLUE, (0, self.HUD_HEIGHT - 1), (screen_w, self.HUD_HEIGHT - 1), 2
        )

        # Informações dos jogadores
        pids = list(self.state.players.keys())
        if not len(pids) >= 2:
            return

        # Fontes modernas
        font_title = pygame.font.SysFont("Arial", 20, bold=True)
        font_info = pygame.font.SysFont("Arial", 14)

        # Player 1 (esquerda)
        positions = [20, screen_w - 210, 250, screen_w - 450]
        for idx, pid in enumerate(pids):
            if idx >= 4:
                break
            self._draw_player_info(
                screen, self.state.players[pid], positions[idx], font_title, font_info, True
            )

        # Timer central com estilo
        timer_text = self._get_timer_text(font_title)
        timer_x = (screen_w - timer_text.get_width()) // 2
        timer_y = (self.HUD_HEIGHT - timer_text.get_height()) // 2

        # Glow para o timer
        glow_surface = pygame.Surface(
            (timer_text.get_width() + 20, timer_text.get_height() + 10), pygame.SRCALPHA
        )
        pygame.draw.ellipse(glow_surface, (*ACCENT_BLUE[:3], 30), glow_surface.get_rect())
        screen.blit(glow_surface, (timer_x - 10, timer_y - 5))
        screen.blit(timer_text, (timer_x, timer_y))

    def _draw_player_info(
        self,
        screen: pygame.Surface,
        player,
        x_pos: int,
        font_title: pygame.font.Font,
        font_info: pygame.font.Font,
        is_left: bool,
    ) -> None:
        """Desenha informações de um jogador no HUD."""
        # Miniatura do jogador
        frames = PLAYERS_MAP[player.skin]["down"]
        thumb = pygame.transform.scale(frames[0], (32, 32))
        thumb_y = (self.HUD_HEIGHT - 32) // 2

        if is_left:
            screen.blit(thumb, (x_pos, thumb_y))
            text_x = x_pos + 40
        else:
            screen.blit(thumb, (x_pos + 90, thumb_y))
            text_x = x_pos

        # Nome do jogador
        name_text = font_title.render(player.username, True, WHITE)
        if not is_left:  # Alinha à direita se for player B
            text_x = x_pos + 90 - name_text.get_width()
        screen.blit(name_text, (text_x, 8))

        # Informações adicionais (bombas, posição, etc.)
        bombs_count = len(player.bombs)
        info_text = f"Bombas: {bombs_count} | Pos: ({player.x},{player.y})"
        info_surface = font_info.render(info_text, True, LIGHT_GRAY)
        if not is_left:
            text_x = x_pos + 90 - info_surface.get_width()
        screen.blit(info_surface, (text_x, 28))

    def _detect_state_changes(self) -> None:
        """
        Sistema crítico de detecção de mudanças para sincronização.
        Resolve o bug principal onde blocos destruídos não são atualizados visualmente.
        """
        if not self.state:
            return

        # 1. Detecta mudanças no número de bombas (colocação ou explosão)
        current_bomb_count = sum(len(p.bombs) for p in self.state.players.values())
        if current_bomb_count != self._last_state_bomb_count:
            self._need_map_refresh = True
            self._last_state_bomb_count = current_bomb_count

        # 2. Detecta explosões ativas (força atualização do mapa)
        explosion_count = 0
        for player in self.state.players.values():
            for bomb in player.bombs:
                if bomb.exploded_at is not None:
                    explosion_count += 1

        for pid, p in self.state.players.items():
            if p.alive is False and pid in self.players:
                del self.players[pid]

        if explosion_count != self._last_explosion_count:
            # CRÍTICO: Explosões sempre invalidam o cache do mapa
            self._need_map_refresh = True
            self._last_explosion_count = explosion_count

        # 3. Hash do estado do mapa para detecção de mudanças finas
        import hashlib

        map_str = str(self.state.map_state.layout)
        current_hash = hashlib.md5(map_str.encode()).hexdigest()
        if current_hash != self._last_state_hash:
            self._need_map_refresh = True
            self._last_state_hash = current_hash

    def _precache_assets(self) -> None:
        """Pré-carrega e cacheia assets para melhor performance."""
        # Cache de explosões em diferentes tamanhos
        for size in [MODULE_SIZE, MODULE_SIZE * 2]:
            for name, anim in EXPLOSION_PARTICLES.items():
                cache_key = f"explosion_{name}_{size}"
                self._assets_cache[cache_key] = [
                    pygame.transform.scale(frame, (size, size)) for frame in anim
                ]

        # Cache de efeitos de glow pré-renderizados
        for radius in [20, 30, 40, 50]:
            glow_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                glow_surface,
                (*EXPLOSION_ORANGE[:3], 100),
                (radius, radius),
                radius,
            )
            self._assets_cache[f"glow_{radius}"] = glow_surface

    # Mantém método antigo para compatibilidade
    def _draw_hud(self, screen: pygame.Surface, screen_w: int) -> None:
        """Método legado - agora chama o moderno."""
        self._draw_modern_hud(screen, screen_w)

    def _get_timer_text(self, font: pygame.font.Font) -> pygame.Surface:
        """Get formatted timer text with color coding based on remaining time."""

        if not self.limited_time:
            # Fallback timer - 3 minutes default
            timer_text = font.render("3:00", True, ACCENT_BLUE)
            self._init_timer()
            return timer_text

        # Game duration in seconds
        game_duration = self.limited_time
        remaining = max(0, game_duration - self.elapsed_time / 1000)

        # Format time as MM:SS
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        time_str = f"{minutes}:{seconds:02d}"

        # Color based on remaining time
        if remaining > (self.limited_time * 0.5):  # More than 50% time left
            color = ACCENT_GREEN
        elif remaining > (self.limited_time * 0.25):  # More than 25% time left
            color = ACCENT_YELLOW
        else:  # Less than 25% time left
            color = ACCENT_RED

        return font.render(time_str, True, color)
