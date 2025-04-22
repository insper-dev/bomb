from enum import IntEnum
from typing import Annotated, Literal

from prisma.partials import Opponent
from pydantic import BaseModel, Field, TypeAdapter

from core.types import PlayerDirectionState


class WebSocketCloseCode(IntEnum):
    """Custom close codes for WebSocket"""

    NORMAL = 1000
    MATCH_FOUND = 4000
    LEAVE_QUEUE = 4001
    ERROR = 4002
    UNAUTHORIZED = 4003


class MovimentEvent(BaseModel):
    event: Literal["move"] = "move"
    direction: PlayerDirectionState

    @staticmethod
    def dxdy(direction: PlayerDirectionState) -> tuple[int, int]:
        if direction == "up":
            return (0, -1)
        if direction == "down":
            return (0, 1)
        if direction == "left":
            return (-1, 0)
        if direction == "right":
            return (1, 0)
        return (0, 0)


class PlaceBombEvent(BaseModel):
    event: Literal["place_bomb"] = "place_bomb"
    x: int
    y: int


GameEventType = Annotated[MovimentEvent | PlaceBombEvent, Field(discriminator="event")]
GameEvent: TypeAdapter[GameEventType] = TypeAdapter(GameEventType)


class MatchMakingEvent(BaseModel):
    event: Literal["match_found", "error"] = "match_found"
    match_id: str | None = None
    opponent: Opponent | None = None
