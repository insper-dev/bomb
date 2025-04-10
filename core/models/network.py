from dataclasses import dataclass
from typing import Literal


@dataclass
class RequestState:
    status: Literal["pending", "completed"]
    timestamp: float  # Time when request was created or completed
    success: bool | None = None  # None when pending, True/False when completed
    data: dict | None = None  # Response data when successful
    error: dict | None = None  # Error information when failed
