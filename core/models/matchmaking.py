import time
from dataclasses import dataclass
from enum import Enum, auto


class PlayerStatus(Enum):
    """Status of a player in the matchmaking queue"""

    QUEUED = auto()  # Player is waiting in queue
    MATCHED = auto()  # Player has been matched
    TIMED_OUT = auto()  # Player waited too long


@dataclass
class QueuedPlayer:
    """Represents a player in the matchmaking queue"""

    user_id: str
    joined_at: float
    status: PlayerStatus = PlayerStatus.QUEUED
    match_id: str | None = None
    opponent_id: str | None = None
    estimated_wait: int = 0
    position: int = 0
    wait_time: int = 0

    @property
    def wait_duration(self) -> float:
        """Calculate how long the player has been waiting"""
        return time.time() - self.joined_at


class MatchmakingState(Enum):
    """State of the matchmaking process"""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    QUEUED = auto()
    MATCH_FOUND = auto()
    ERROR = auto()
