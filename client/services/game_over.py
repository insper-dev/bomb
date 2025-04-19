from __future__ import annotations

from collections.abc import Callable
from typing import Any

from client.services.base import ServiceBase
from core.models.match import MatchStats
from core.models.network import RequestState


class GameOverService(ServiceBase):
    """Service for handling game over statistics and requests."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.match_stats: MatchStats | None = None
        self.get_stats_request_id: str | None = None
        self.errors: dict[str, str | None] = {"get_stats": None}
        self.on_stats_loaded_callbacks: list[Callable[[MatchStats], Any]] = []

    def register_stats_loaded_callback(self, callback: Callable[[MatchStats], Any]) -> None:
        """Register callback for when match stats are loaded."""
        self.on_stats_loaded_callbacks.append(callback)

    def get_stats_status(self) -> RequestState | None:
        """Get current status of the stats request."""
        if not self.get_stats_request_id:
            return None
        return self.app.api_client.get_request_status(self.get_stats_request_id)

    @property
    def is_stats_loading(self) -> bool:
        """Check if stats are currently being loaded."""
        status = self.get_stats_status()
        if not status:
            return False

        if status.status == "completed":
            if status.success and status.data:
                self.match_stats = MatchStats.model_validate(status.data)
                for callback in self.on_stats_loaded_callbacks:
                    try:
                        callback(self.match_stats)
                    except Exception as e:
                        print(f"Error in stats loaded callback: {e}")
            else:
                self.errors["get_stats"] = self._get_error_message(status)
            self.get_stats_request_id = None
            return False

        return status.status == "pending"

    def fetch_stats(self, match_id: str) -> str:
        """Fetch match statistics from the server."""
        if self.is_stats_loading:
            print("A stats request is already in progress.")
            return self.get_stats_request_id or ""

        self.errors["get_stats"] = None
        self.get_stats_request_id = self.app.api_client.request(f"/match/{match_id}/stats", "GET")
        return self.get_stats_request_id

    def get_stats_error(self) -> str | None:
        """Get error message from stats request, if any."""
        return self.errors["get_stats"]

    def _get_error_message(self, status: RequestState) -> str:
        """Extract error message from request state."""
        if not status or not status.error:
            return "Unknown error in request"
        if "message" in status.error:
            return status.error["message"]
        if "detail" in status.error:
            return status.error["detail"]
        return str(status.error)
