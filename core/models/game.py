import uuid

from pydantic import BaseModel, Field


class PlayerState(BaseModel):
    player_id: str
    x: int = 0
    y: int = 0


class GameState(BaseModel):
    game_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    players: dict[str, PlayerState] = Field(default_factory=dict)
    # Map 13x11: 0 = empty, future codes for bombs, walls, etc.
    map: list[list[int]] = Field(default_factory=lambda: [[0] * 11 for _ in range(13)])

    def add_players(self, player_ids: list[str]) -> None:
        for pid in player_ids:
            self.players[pid] = PlayerState(player_id=pid)

    def move_player(self, player_id: str, dx: int, dy: int) -> None:
        if player_id not in self.players:
            return
        p = self.players[player_id]
        new_x = max(0, min(len(self.map[0]) - 1, p.x + dx))
        new_y = max(0, min(len(self.map) - 1, p.y + dy))
        p.x, p.y = new_x, new_y
