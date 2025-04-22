from enum import Enum

from pydantic import BaseModel, Field

from core.types import PlayerDirectionState


class GameStatus(str, Enum):
    PLAYING = "playing"
    DRAW = "draw"
    WINNER = "winner"


class PlayerState(BaseModel):
    player_id: str
    movement_state: PlayerDirectionState = "stand_by"
    x: int = 0
    y: int = 0


class BombState(BaseModel):
    bomb_id: str
    x: int
    y: int
    owner_id: str
    radius: int = 1


class ExplosionState(BaseModel):
    bomb_id: str
    x: int
    y: int
    radius: int
    duration: float = 0.5  # segundos de animação


class GameState(BaseModel):
    game_id: str
    players: dict[str, PlayerState] = Field(default_factory=dict)
    map: list[list[int]] = Field(default_factory=lambda: [[0] * 11 for _ in range(13)])
    status: GameStatus = GameStatus.PLAYING
    winner_id: str | None = None
    bombs: list[BombState] = Field(default_factory=list)
    explosions: list[ExplosionState] = Field(default_factory=list)

    def add_players(self, player_ids: list[str]) -> None:
        """Add players to the game with initial positions"""
        positions = [(3, 3), (4, 4)]  # Starting positions for 2 players

        for i, pid in enumerate(player_ids):
            x, y = positions[i] if i < len(positions) else (1, 1)
            self.players[pid] = PlayerState(player_id=pid, x=x, y=y)

    def move_player(
        self,
        player_id: str,
        dx: int,
        dy: int,
        direction: PlayerDirectionState,
    ) -> None:
        """Move a player if possible"""
        # Don't allow moves if game is over
        if self.status != GameStatus.PLAYING:
            return

        if player_id not in self.players:
            return
        p = self.players[player_id]
        new_x = max(0, min(len(self.map[0]) - 1, p.x + dx))
        new_y = max(0, min(len(self.map) - 1, p.y + dy))
        p.x, p.y, p.movement_state = new_x, new_y, direction

    def end_game(self, winner_id: str | None = None) -> None:
        """End the game, optionally with a winner"""
        if winner_id:
            self.status = GameStatus.WINNER
            self.winner_id = winner_id
        else:
            self.status = GameStatus.DRAW

    def add_bomb(self, bomb: BombState) -> None:
        self.bombs.append(bomb)

    def explode_bomb(self, bomb_id: str) -> None:
        self.bombs = [b for b in self.bombs if b.bomb_id != bomb_id]

    def add_explosion(self, bomb_id: str, x: int, y: int, radius: int) -> ExplosionState:
        explosion = ExplosionState(bomb_id=bomb_id, x=x, y=y, radius=radius)
        self.explosions.append(explosion)
        return explosion

    def clear_explosion(self, bomb_id: str) -> None:
        self.explosions = [e for e in self.explosions if e.bomb_id != bomb_id]
