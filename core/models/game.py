import json
import random
from datetime import datetime
from enum import Enum
from uuid import uuid4

from icecream import ic
from pydantic import BaseModel, Field, field_serializer, field_validator

from core.types import PlayerDirectionState, PlayerType


class GameStatus(str, Enum):
    PLAYING = "playing"
    DRAW = "draw"
    WINNER = "winner"


class GameTheme(str, Enum):
    """
    Temas disponíveis para o mapa do jogo:\n
    DESERT: Tema desértico com cores quentes e elementos de areia.\n
    SHED: Tema de galpão com elementos rústicos e industriais.\n

    """

    DESERT = "desert"
    SHED = "shed"


class MapBlockType(str, Enum):
    """
    Tipos de blocos que podem compor o mapa do jogo.\n
    EMPTY: Espaço vazio onde os jogadores podem se mover livremente.\n
    BREAKABLE: Bloco que pode ser destruído por uma explosão de bomba.\n
    UNBREAKABLE: Bloco indestrutível que serve como obstáculo permanente.\n
    """

    EMPTY = "empty"
    BREAKABLE = "breakable"
    UNBREAKABLE = "unbreakable"
    POWER_UP = "power_up"


class PowerUpType(str, Enum):
    """_summary_

    Tipos de power-ups disponíveis no jogo.\n
    EXTRA_BOMB: Permite ao jogador colocar uma bomba extra além do limite padrão.\n
    INCREASE_RADIUS: Aumenta o raio de explosão das bombas do jogador.\n
    SHIELD: Concede um escudo temporário que protege o jogador de uma explosão\n
    """

    EXTRA_BOMB = "extra_bomb"
    INCREASE_RADIUS = "increase_radius"
    SHIELD = "shield"


class BombState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    x: int
    y: int
    placed_at: datetime = Field(default_factory=datetime.now)
    exploded_at: datetime | None = None
    radius: int

    @field_validator("placed_at", "exploded_at", mode="before")
    @classmethod
    def validate_placed_at(cls, value) -> datetime | None:
        if value is None:
            return
        elif isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    @field_serializer("placed_at", "exploded_at")
    def serialize_exploded_at(self, value) -> str | None:
        return value.isoformat() if value else None


class PlayerState(BaseModel):
    username: str
    direction_state: PlayerDirectionState
    x: int = 0
    y: int = 0
    power_ups: list[str] = Field(default_factory=list)
    skin: PlayerType = Field(default_factory=lambda: random.choice(["carlitos", "rogerio"]))
    bombs: list[BombState] = Field(default_factory=list)
    max_bombs: int = 2
    bomb_delay: int = 2  # seconds
    bomb_radius: int = 2


def get_theme() -> GameTheme:
    return random.choice(list(GameTheme))


def generate_map(theme) -> list[list[MapBlockType]]:
    maps_path = "core/maps"
    maps_path += "/map1.json"  # Default map

    # Load base map
    with open(maps_path) as f:
        base_map_data = json.load(f)

    # Map structure
    map = base_map_data["map"]
    # columns, rows, layout
    # layout is a 2D array of characters representing block types
    # D = destructible, U = undestructible, E = empty, R = random (D or E)

    width = map.get("columns", 13)  # Default width for bomberman-like games
    height = map.get("rows", 11)  # Default height for bomberman-like games

    ic(f"Generating map: {width}x{height}")

    # Start with an empty grid
    map_grid = [[MapBlockType.EMPTY for _ in range(width)] for _ in range(height)]

    # Place indestructible blocks in layout patern

    # Count indestructible and destructible blocks
    indestructible_count = 0
    destructible_count = 0

    # Asemble the map grid based on the layout
    for y in range(height):
        for x in range(width):
            block_type = map["layout"][y][x]  # get the block type from the layout
            print(f"Processing block at ({x}, {y}): {block_type}")
            if block_type == "R":
                block_type = random.choice(
                    ["D", "E"]
                )  # Randomly choose between destructible or empty
            if block_type == "D":
                block = MapBlockType.BREAKABLE
                destructible_count += 1
            elif block_type == "U":
                indestructible_count += 1
                block = MapBlockType.UNBREAKABLE
            else:
                block = MapBlockType.EMPTY
            map_grid[y][x] = block

    ic(f"Placed {indestructible_count} indestructible blocks")

    ic(f"Placed {destructible_count} destructible blocks")

    # # Occasionally place power-ups (5% chance in destructible boxes)
    # power_up_count = 0
    # for y in range(height):
    #     for x in range(width):
    #         if map_grid[y][x] in DESTROYABLE_BOXES and random.random() < 0.05:
    #             map_grid[y][x] = MapBlockType.POWER_UP
    #             power_up_count += 1
    # ic(f"Placed {power_up_count} power-ups")

    return map_grid


class GameState(BaseModel):
    game_id: str
    players: dict[str, PlayerState] = Field(default_factory=dict)
    game_theme: GameTheme = Field(default_factory=get_theme)  # Random theme
    map: list[list[MapBlockType]] = Field(default_factory=generate_map)
    status: GameStatus = GameStatus.PLAYING
    winner_id: str | None = None
    time_start: int

    def move_player(
        self, player_id: str, dx: int, dy: int, direction: PlayerDirectionState
    ) -> tuple[int, int] | None:
        """Move a player if possible considering walls and map boundaries"""
        ic(f"Move request: player={player_id}, dx={dx}, dy={dy}, direction={direction}")

        # Don't allow moves if game is over
        if self.status != GameStatus.PLAYING:
            ic(f"Move rejected: game not in PLAYING state (current: {self.status})")
            return

        if player_id not in self.players:
            ic(f"Move rejected: player {player_id} not in game")
            return

        p = self.players[player_id]
        old_pos = (p.x, p.y)
        new_x = max(0, min(len(self.map[0]) - 1, p.x + dx))
        new_y = max(0, min(len(self.map) - 1, p.y + dy))
        ic(f"Move calculation: {old_pos} → ({new_x}, {new_y})")

        # Check for walls
        target_block = self.map[new_y][new_x]
        if target_block not in {MapBlockType.EMPTY, MapBlockType.POWER_UP}:
            ic(f"Move rejected: destination has {target_block}")
            return

        p.x, p.y, p.direction_state = new_x, new_y, direction
        ic(f"Player {player_id} moved to ({new_x}, {new_y}) facing {direction}")
        return new_x, new_y

    def end_game(self, winner_id: str | None = None) -> None:
        """End the game, optionally with a winner"""
        ic(f"Ending game {self.game_id}, winner: {winner_id or 'DRAW'}")
        old_status = self.status
        if winner_id:
            self.status = GameStatus.WINNER
            self.winner_id = winner_id
        else:
            self.status = GameStatus.DRAW
        ic(f"Game status changed: {old_status} → {self.status}")

    def add_bomb(self, player_id: str, bomb: BombState) -> None:
        """Add a bomb for a specific player"""
        # TODO: não permitir spammar bombas, a não ser que algum powerup permita.
        ic(f"Adding bomb for player {player_id} at ({bomb.x}, {bomb.y}) with radius {bomb.radius}")
        if player_id in self.players:
            self.players[player_id].bombs.append(bomb)
            ic(f"Player {player_id} now has {len(self.players[player_id].bombs)} active bombs")
        else:
            ic(f"Failed to add bomb: player {player_id} not found")

    def explode_bomb(
        self,
        player_id: str,
        bomb_id: str,
        remove_bomb: bool = False,
    ) -> list[tuple[int, int]]:
        """
        Marca a bomba como explodida, opcionalmente remove-a da lista do jogador,
        destrói paredes quebráveis em cruz e retorna a lista de tiles afetados
        (para facilitar detecção de jogadores atingidos).
        """
        ic(f"Processing explosion: player={player_id}, bomb={bomb_id}")

        # 1) Encontra o estado da bomba
        player = self.players.get(player_id)
        if not player:
            ic(f"Explosion failed: player {player_id} not found")
            return []

        bomb = next((b for b in player.bombs if b.id == bomb_id), None)
        if not bomb:
            ic(f"Explosion failed: bomb {bomb_id} not found for player {player_id}")
            return []

        ic(f"Found bomb at ({bomb.x}, {bomb.y}) with radius={bomb.radius}")

        # 2) Marca timestamp de explosão se ainda não estiver marcado
        if not bomb.exploded_at:
            bomb.exploded_at = datetime.now()

        # 3) Remove da lista de bombas ativas se solicitado
        if remove_bomb:
            old_bomb_count = len(player.bombs)
            player.bombs = [b for b in player.bombs if b.id != bomb_id]
            ic(f"Removed bomb: {old_bomb_count} → {len(player.bombs)} bombs")

        # 4) Calcula alcance em cruz
        affected: list[tuple[int, int]] = [(bomb.x, bomb.y)]
        ic(f"Explosion center: ({bomb.x}, {bomb.y})")

        # Track destroyed blocks
        destroyed_blocks = []

        # Direções corrigidas: usando vetores unitários multiplicados pelo passo
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            direction_name = {
                (1, 0): "RIGHT",
                (-1, 0): "LEFT",
                (0, 1): "DOWN",
                (0, -1): "UP",
            }[(dx, dy)]

            ic(f"Calculating explosion: {direction_name}")

            for step in range(1, bomb.radius + 1):
                nx, ny = bomb.x + (dx * step), bomb.y + (dy * step)

                # verifica limites do mapa
                if nx < 0 or ny < 0 or ny >= len(self.map) or nx >= len(self.map[0]):
                    ic(f"{direction_name}: Hit map boundary at step {step}")
                    break

                cell = self.map[ny][nx]
                ic(f"{direction_name} step {step}: ({nx}, {ny}) - {cell}")

                # se for indestrutível, para nesta direção
                if cell == MapBlockType.UNBREAKABLE:
                    ic(f"{direction_name}: Blocked by {cell} at ({nx}, {ny})")
                    break

                # adiciona ao alcance
                affected.append((nx, ny))

                # se for quebrável, remove e para nesta direção
                if cell == MapBlockType.BREAKABLE:
                    old_cell = self.map[ny][nx]
                    self.map[ny][nx] = MapBlockType.EMPTY
                    destroyed_blocks.append((nx, ny, old_cell))
                    ic(f"{direction_name}: Destroyed {old_cell} at ({nx}, {ny})")
                    break

                # se estiver vazio ou power-up, continua propagando

        ic(f"Explosion complete. Affected: {len(affected)}, Destroyed: {len(destroyed_blocks)}")

        # Check if any players are in the explosion radius
        hit_players = []
        for pid, p in self.players.items():
            if (p.x, p.y) in affected:
                hit_players.append(pid)

        if hit_players:
            ic(f"Players hit: {hit_players}")
        else:
            ic("No players hit")

        return affected
