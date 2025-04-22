import json
from pathlib import Path

import pygame

from client.game.base_block import BaseBlock
from client.game.bomb import Bomb
from client.game.particles import Particles
from client.game.players import Carlitos, Player
from client.scenes.base import BaseScene, Scenes
from client.services.game import GameService
from core.constants import FLOORS, MODULE_SIZE, PURPLE
from core.models.game import GameState, GameStatus


class GameScene(BaseScene):
    """Scene to render and control the Bomberman game via WebSocket."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.game_service: GameService = app.game_service
        self.game_id: str = app.matchmaking_service.match_id or ""
        self.game_service.start(self.game_id)

        # Initiate Game Music
        self.song = "client/assets/sounds/map1_song.mpeg"
        pygame.mixer.music.load(self.song)
        pygame.mixer.music.play(-1)
        pygame.mixer.music.stop()

        # Register callback for game end
        self.game_service.register_game_ended_callback(self._on_game_ended)

        # UI elements
        self.font_large = pygame.font.SysFont(None, 48)
        self.font_medium = pygame.font.SysFont(None, 36)
        self.font_small = pygame.font.SysFont(None, 24)

        # Auto-return to menu timer
        self.return_to_menu_timer = None
        self.return_countdown = 5  # seconds

        # Initiate players objects
        self.players: dict[str, Player] = {}
        self.players_initialized = False

        # Initiate bombs objects
        self.bombs: dict[str, Bomb] = {}

        # Initiate particles objects
        self.particles: dict[str, Particles] = {}

        # Initiate map
        with open(Path("client/game/maps.json")) as map:
            self.map = json.load(map)["map2"]
        self.margin: tuple[int, int] = (
            int(self.app.screen_center[0] - (len(self.map[0]) * MODULE_SIZE) // 2),
            int(self.app.screen_center[1] - (len(self.map) * MODULE_SIZE) // 2),
        )
        self._initiate_map()

        # Local init state
        self.state: dict[str, int | float | tuple] = {"player_position": 0}

    def _on_game_ended(self, status: GameStatus, winner_id: str | None) -> None:
        """Called when the game ends"""
        # Não chame game_service.stop() aqui - isso tentará parar a thread de dentro dela mesma
        # Apenas definimos uma flag para fazer a transição na thread principal
        self.should_transition_to_game_over = True

    def _create_playes_objects(self, state: GameState) -> None:
        for player_id, pstate in state.players.items():
            print(pstate.x, pstate.y)
            self.players[player_id] = Carlitos(
                self.app.screen,
                (
                    pstate.x,
                    pstate.y,
                ),
                self.game_service,
                self.margin,
                self.map,
            )

    def _initiate_map(self) -> None:
        self.blocks: list[list[BaseBlock | tuple[pygame.Surface, pygame.Rect]]] = [[]]
        for y, linha in enumerate(self.map):
            pre_list: list[BaseBlock | tuple[pygame.Surface, pygame.Rect]] = []
            for x, name in enumerate(linha):
                if name[0:2] != "f_":
                    pre_list.append(
                        BaseBlock(
                            self.app.screen,
                            name,
                            (self.margin[0] + x * MODULE_SIZE, self.margin[1] + y * MODULE_SIZE),
                        )
                    )
                else:
                    surface = pygame.Surface((MODULE_SIZE, MODULE_SIZE))
                    surface.fill(FLOORS[name])
                    rect = surface.get_rect(
                        topleft=(self.margin[0] + x * MODULE_SIZE, self.margin[1] + y * MODULE_SIZE)
                    )
                    pre_list.append((surface, rect))
            self.blocks.append(pre_list)
            pre_list = []

    def handle_event(self, event) -> None:
        if event.type == pygame.QUIT:
            self.app.running = False
        elif event.type == pygame.KEYDOWN:
            # Exit to menu
            if event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
                self.game_service.stop()
                self.app.current_scene = Scenes.START

        for pid, player in self.players.items():
            user = self.app.auth_service.current_user
            state = self.game_service.state
            if state is not None:
                for id, psta in state.players.items():
                    if user is not None and user.id != pid and pid == id:
                        player.moviment_state = psta.movement_state
            if user is not None and user.id == pid:
                player.handle_events(event)
                if (
                    event.type == pygame.KEYDOWN
                    and event.key == pygame.K_SPACE
                    and not self.game_service.is_game_ended
                ):
                    self.game_service.send_bomb(
                        explosion_radius=player.status["power"], explosion_time=1
                    )

    def update(self) -> None:
        # Primeiro verificamos se o jogo sinalizou que acabou e devemos transitar para o game over
        if hasattr(self, "should_transition_to_game_over") and self.should_transition_to_game_over:
            # Primeiro paramos o game service (na thread principal)
            if self.game_service.running:
                print("Stopping game service from main thread")
                self.game_service.stop()
            # Então mudamos para a cena de game over
            self.app.current_scene = Scenes.GAME_OVER
            return

        # Processamento normal
        super().update()

    def render(self) -> None:
        screen = self.app.screen
        screen.fill(PURPLE)
        state = self.game_service.state
        if not state:
            return

        # Draw grid
        for y in range(len(self.map)):
            for x in range(len(self.map[0])):
                rect = pygame.Rect(
                    self.margin[0] + x * MODULE_SIZE,
                    self.margin[1] + y * MODULE_SIZE,
                    MODULE_SIZE,
                    MODULE_SIZE,
                )
                pygame.draw.rect(screen, (50, 50, 50), rect, width=1)

        # Draw map objects
        for list in self.blocks:
            for object in list:
                if isinstance(object, BaseBlock):
                    object.render()
                else:
                    surface, rect = object
                    self.app.screen.blit(surface, rect)

        # Draw players

        if not self.players_initialized:
            self._create_playes_objects(state)
            self.players_initialized = True

        for player_id, player_state in state.players.items():
            for id, player in self.players.items():
                if id == player_id:
                    if player.moviment_state == "stand_by":
                        x = player_state.x
                        y = player_state.y
                        if player.last_position != (x, y):
                            player.relative_position = (x, y)
        for player in self.players.values():
            player.render()

        # Draw bombs

        for bomb in state.bombs:
            if bomb.bomb_id not in self.bombs:
                x = bomb.x
                y = bomb.y
                self.bombs[bomb.bomb_id] = Bomb(self.app.screen, (x, y), self.margin)

        for bomb in self.bombs.values():
            bomb.render()

        # Draw explosions as a "+" cross
        for exp in state.explosions:
            x = self.margin[0] + exp.x * MODULE_SIZE
            y = self.margin[1] + exp.y * MODULE_SIZE
            position = (x, y)
            to_remove = []
            for id in self.bombs:
                if exp.bomb_id == id:
                    to_remove.append(id)
                    if id not in self.particles:
                        self.particles[id] = Particles(
                            self.app.screen, self.particles, position, exp.radius
                        )
            for item in to_remove:
                del self.bombs[item]

        to_remove = []
        for particle in self.particles.values():
            yup = particle.render()
            if yup != "":
                to_remove.append(yup)

        for item in to_remove:
            del self.particles[item]

        if self.game_service.is_game_ended:
            result_text = self.game_service.game_result
            text = self.font_large.render(result_text, True, (255, 255, 255))
            rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() - 80))
            screen.blit(text, rect)

            if self.return_to_menu_timer:
                remaining = max(0, (self.return_to_menu_timer - pygame.time.get_ticks()) // 1000)
                countdown = self.font_medium.render(
                    f"Returning to menu in {remaining} seconds...", True, (200, 200, 200)
                )
                screen.blit(
                    countdown,
                    (
                        screen.get_width() // 2 - countdown.get_width() // 2,
                        screen.get_height() - 40,
                    ),
                )
        else:
            # Regular game instructions
            instr = self.font_small.render("Use arrow keys to move", True, (180, 180, 180))
            screen.blit(instr, (self.margin[0], screen.get_height() - 80))

            instr2 = self.font_small.render("Press ESC to return to menu", True, (180, 180, 180))
            screen.blit(instr2, (self.margin[1], screen.get_height() - 50))
