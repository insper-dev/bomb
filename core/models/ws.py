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
    direction: Literal["up", "down", "left", "right"]


class BombEvent(BaseModel):
    event: Literal["bomb"] = "bomb"


GameEventType = Annotated[MovimentEvent | BombEvent, Field(discriminator="event")]
GameEvent: TypeAdapter[GameEventType] = TypeAdapter(GameEventType)


class MatchMakingEvent(BaseModel):
    event: Literal["match_found", "error"] = "match_found"
    match_id: str | None = None
    opponent: Opponent | None = None
