from enum import Enum

from pydantic import BaseModel, Field


class GameStatus(str, Enum):
    """Status of a game"""

    PLAYING = "playing"
    DRAW = "draw"
    WINNER = "winner"


class PlayerState(BaseModel):
    player_id: str
    x: int = 0
    y: int = 0


class GameState(BaseModel):
    game_id: str
    players: dict[str, PlayerState] = Field(default_factory=dict)
    # Map 13x11: 0 = empty, future codes for bombs, walls, etc.
    map: list[list[int]] = Field(default_factory=lambda: [[0] * 11 for _ in range(13)])
    status: GameStatus = GameStatus.PLAYING
    winner_id: str | None = None

    def add_players(self, player_ids: list[str]) -> None:
        """Add players to the game with initial positions"""
        positions = [(0, 0), (10, 10)]  # Starting positions for 2 players

        for i, pid in enumerate(player_ids):
            x, y = positions[i] if i < len(positions) else (0, 0)
            self.players[pid] = PlayerState(player_id=pid, x=x, y=y)

    def move_player(self, player_id: str, dx: int, dy: int) -> None:
        """Move a player if possible"""
        # Don't allow moves if game is over
        if self.status != GameStatus.PLAYING:
            return

        if player_id not in self.players:
            return
        p = self.players[player_id]
        new_x = max(0, min(len(self.map[0]) - 1, p.x + dx))
        new_y = max(0, min(len(self.map) - 1, p.y + dy))
        p.x, p.y = new_x, new_y

    def end_game(self, winner_id: str | None = None) -> None:
        """End the game, optionally with a winner"""
        if winner_id:
            self.status = GameStatus.WINNER
            self.winner_id = winner_id
        else:
            self.status = GameStatus.DRAW
