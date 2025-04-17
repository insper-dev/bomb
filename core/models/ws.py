from enum import IntEnum
from typing import Literal

from pydantic import BaseModel


class WebSocketCloseCode(IntEnum):
    """Custom close codes for WebSocket"""

    NORMAL = 1000
    MATCH_FOUND = 4000
    LEAVE_QUEUE = 4001
    ERROR = 4002
    UNAUTHORIZED = 4003


class WSMessage(BaseModel):
    action: Literal["move"]
    direction: Literal["up", "down", "left", "right"]
