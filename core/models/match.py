from pydantic import BaseModel, Field


class PlayerStats(BaseModel):
    user_id: str
    username: str
    bombs_placed: int = 0
    players_killed: int = 0
    is_winner: bool = False


class MatchStats(BaseModel):
    match_id: str
    winner_id: str | None = None
    players: list[PlayerStats] = Field(default_factory=list)
    duration_seconds: int | None = None
