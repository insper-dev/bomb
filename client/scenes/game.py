from typing import Literal

import pygame

from client.game.bomb import Bomb
from client.game.particles import Particles
from client.game.players import Carlitos, Player
from client.scenes.base import BaseScene, Scenes
from client.services.game import GameService
from core.constants import MODULE_SIZE
from core.models.game import GameState, GameStatus


class GameScene(BaseScene):
    """Scene to render and control the Bomberman game via WebSocket."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.game_service: GameService = app.game_service
        self.game_id: str = app.matchmaking_service.match_id or ""
        self.margin: int = 20
        self.game_service.start(self.game_id)

        # Initiate Game Music
        self.song = "client/assets/sounds/map1_song.mpeg"
        pygame.mixer.music.load(self.song)
        pygame.mixer.music.play(-1)
        print(pygame.mixer.music.get_pos(), pygame.mixer.music.get_volume())

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

        # Initiate partivles objects
        self.particles: dict[str, Particles] = {}

    def _on_game_ended(self, status: GameStatus, winner_id: str | None) -> None:
        """Called when the game ends"""
        # Não chame game_service.stop() aqui - isso tentará parar a thread de dentro dela mesma
        # Apenas definimos uma flag para fazer a transição na thread principal
        self.should_transition_to_game_over = True

    def _create_playes_objects(self, state: GameState) -> None:
        for player_id, pstate in state.players.items():
            self.players[player_id] = Carlitos(
                self.app.screen,
                (
                    pstate.x * MODULE_SIZE + self.margin,
                    pstate.y * MODULE_SIZE + self.margin,
                ),
            )

    def handle_event(self, event) -> None:
        if event.type == pygame.QUIT:
            self.app.running = False
        elif event.type == pygame.KEYDOWN:
            # Movement keys
            if not self.game_service.is_game_ended:
                key_map: dict[int, Literal["up", "down", "left", "right"]] = {
                    pygame.K_UP: "up",
                    pygame.K_DOWN: "down",
                    pygame.K_LEFT: "left",
                    pygame.K_RIGHT: "right",
                }
                if event.key in key_map:
                    self.game_service.send_move(key_map[event.key])
            # Exit to menu
            elif event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
                self.game_service.stop()
                self.app.current_scene = Scenes.START

        for pid, player in self.players.items():
            user = self.app.auth_service.current_user
            if user and user.id == pid:
                player.handle_events(event)
                if (
                    event.type == pygame.KEYDOWN
                    and event.key == pygame.K_SPACE
                    and not self.game_service.is_game_ended
                ):
                    self.game_service.send_bomb(
                        explosion_radius=player.status["power"], explosion_time=3.5
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
        screen.fill((0, 0, 0))
        state = self.game_service.state
        if not state:
            return

        rows, cols = len(state.map), len(state.map[0])
        if cols == 0:
            return

        # Draw grid
        for y in range(rows):
            for x in range(cols):
                rect = pygame.Rect(
                    self.margin + x * MODULE_SIZE,
                    self.margin + y * MODULE_SIZE,
                    MODULE_SIZE,
                    MODULE_SIZE,
                )
                pygame.draw.rect(screen, (50, 50, 50), rect, width=1)

        # Draw players

        if not self.players_initialized:
            self._create_playes_objects(state)
            self.players_initialized = True

        for player_id, player_state in state.players.items():
            for id, player in self.players.items():
                if id == player_id:
                    player.position = (
                        player_state.x * MODULE_SIZE + self.margin,
                        player_state.y * MODULE_SIZE + self.margin,
                    )

        for player in self.players.values():
            player.render()

        # Draw bombs

        for bomb in state.bombs:
            if bomb.bomb_id not in self.bombs:
                x = self.margin + bomb.x * MODULE_SIZE
                y = self.margin + bomb.y * MODULE_SIZE
                self.bombs[bomb.bomb_id] = Bomb(self.app.screen, (x, y))

        for bomb in self.bombs.values():
            bomb.render()

        # Draw explosions as a "+" cross
        for exp in state.explosions:
            x = self.margin + exp.x * MODULE_SIZE
            y = self.margin + exp.y * MODULE_SIZE
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
            screen.blit(instr, (self.margin, screen.get_height() - 80))

            instr2 = self.font_small.render("Press ESC to return to menu", True, (180, 180, 180))
            screen.blit(instr2, (self.margin, screen.get_height() - 50))
