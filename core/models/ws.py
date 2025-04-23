from enum import IntEnum
from typing import Annotated, Literal

from prisma.partials import Opponent
from pydantic import BaseModel, Field, TypeAdapter


class WebSocketCloseCode(IntEnum):
    """Custom close codes for WebSocket"""

    NORMAL = 1000
    MATCH_FOUND = 4000
    LEAVE_QUEUE = 4001
    ERROR = 4002
    UNAUTHORIZED = 4003


class MovimentEvent(BaseModel):
    event: Literal["move"] = "move"
    direction: Literal["up", "down", "left", "right", "stand_by"]


class PlaceBombEvent(BaseModel):
    event: Literal["place_bomb"] = "place_bomb"
    x: int
    y: int
    radius: int = Field(default=1)
    explosion_time: float


GameEventType = Annotated[MovimentEvent | PlaceBombEvent, Field(discriminator="event")]
GameEvent: TypeAdapter[GameEventType] = TypeAdapter(GameEventType)


class MatchMakingEvent(BaseModel):
    event: Literal["match_found", "error"] = "match_found"
    match_id: str | None = None
    opponent: Opponent | None = None
