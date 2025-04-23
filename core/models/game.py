import random
from datetime import datetime
from enum import Enum
from uuid import uuid4

from prisma.models import User
from pydantic import BaseModel, Field, field_serializer, field_validator

from core.types import PlayerDirectionState, PlayerType


class GameStatus(str, Enum):
    PLAYING = "playing"
    DRAW = "draw"
    WINNER = "winner"


class MapBlockType(str, Enum):
    EMPTY = "empty"
    SAND_BOX = "sand_box"
    WOODEN_BOX = "wooden_box"
    DIAMOND_BOX = "diamond_box"
    METAL_BOX = "metal_box"
    POWER_UP = "power_up"


DESTROYABLE_BOXES = [MapBlockType.WOODEN_BOX, MapBlockType.SAND_BOX]
UNDESTOYABLE_BOXES = [MapBlockType.DIAMOND_BOX, MapBlockType.METAL_BOX]


class BombState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    x: int
    y: int
    placed_at: datetime = Field(default_factory=datetime.now)
    exploded_at: datetime | None = None

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
    # TODO: to type the power ups and skin.
    power_ups: list[str] = Field(default_factory=list)
    skin: PlayerType = Field(default_factory=lambda: random.choice(["carlitos", "rogerio"]))
    bombs: list[BombState] = Field(default_factory=list)


def generate_map() -> list[list[MapBlockType]]:
    width = 13  # Standard Bomberman-like grid width (odd number)
    height = 11  # Standard Bomberman-like grid height (odd number)

    # Start with an empty grid
    map_grid = [[MapBlockType.EMPTY for _ in range(width)] for _ in range(height)]

    # Place indestructible blocks in a pattern (every other cell)
    for y in range(height):
        for x in range(width):
            if x % 2 == 0 and y % 2 == 0:
                # Random choice between indestructible box types
                map_grid[y][x] = random.choice(UNDESTOYABLE_BOXES)

    # Place destructible boxes randomly with a probability (around 40% of empty spaces)
    for y in range(height):
        for x in range(width):
            # Skip cells with indestructible boxes and keep corners empty for players
            if map_grid[y][x] == MapBlockType.EMPTY and not (
                (x <= 1 and y <= 1) or (x >= width - 2 and y >= height - 2)
            ):
                if random.random() < 0.4:  # 40% chance to place a destructible box
                    map_grid[y][x] = random.choice(DESTROYABLE_BOXES)

    # Ensure corners are empty for player starting positions
    map_grid[0][0] = MapBlockType.EMPTY
    map_grid[0][1] = MapBlockType.EMPTY
    map_grid[1][0] = MapBlockType.EMPTY

    map_grid[height - 1][width - 1] = MapBlockType.EMPTY
    map_grid[height - 1][width - 2] = MapBlockType.EMPTY
    map_grid[height - 2][width - 1] = MapBlockType.EMPTY

    # # Occasionally place power-ups (5% chance in destructible boxes)
    # for y in range(height):
    #     for x in range(width):
    #         if map_grid[y][x] in DESTROYABLE_BOXES and random.random() < 0.05:
    #             map_grid[y][x] = MapBlockType.POWER_UP

    return map_grid


class GameState(BaseModel):
    game_id: str
    players: dict[str, PlayerState] = Field(default_factory=dict)
    # TODO: get map randomly.
    map: list[list[MapBlockType]] = Field(default_factory=generate_map)
    status: GameStatus = GameStatus.PLAYING
    winner_id: str | None = None

    def add_players(self, players: list[User]) -> None:
        """Add players to the game with initial positions"""
        positions = [(1, 1), (10, 10)]  # Starting positions for 2 players

        for i, player in enumerate(players):
            x, y = positions[i] if i < len(positions) else (0, 0)
            self.players[player.username] = PlayerState(
                username=player.username, direction_state="stand_by", x=x, y=y
            )

    def move_player(
        self, player_id: str, dx: int, dy: int, direction: PlayerDirectionState
    ) -> tuple[int, int] | None:
        """Move a player if possible considering walls and map boundaries"""
        # Don't allow moves if game is over
        if self.status != GameStatus.PLAYING:
            return

        if player_id not in self.players:
            return

        p = self.players[player_id]
        new_x = max(0, min(len(self.map[0]) - 1, p.x + dx))
        new_y = max(0, min(len(self.map) - 1, p.y + dy))

        # Check for walls
        if self.map[new_y][new_x] not in {MapBlockType.EMPTY, MapBlockType.POWER_UP}:
            return

        p.x, p.y, p.direction_state = new_x, new_y, direction
        return new_x, new_y

    def end_game(self, winner_id: str | None = None) -> None:
        """End the game, optionally with a winner"""
        if winner_id:
            self.status = GameStatus.WINNER
            self.winner_id = winner_id
        else:
            self.status = GameStatus.DRAW

    def add_bomb(self, player_id: str, bomb: BombState) -> None:
        """Add a bomb for a specific player"""
        if player_id in self.players:
            self.players[player_id].bombs.append(bomb)

    def explode_bomb(self, player_id: str, bomb_id: str) -> None:
        """Explode a bomb for a specific player"""
        if player_id in self.players:
            player = self.players[player_id]
            player.bombs = [b for b in player.bombs if b.id != bomb_id]

            # Set the explosion time for the bomb
            for bomb in player.bombs:
                if bomb.id == bomb_id:
                    bomb.exploded_at = datetime.now()
