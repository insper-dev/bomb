import asyncio
import json
import threading
from collections.abc import Callable

from websockets import ConnectionClosed, connect
from websockets.client import ClientConnection

from client.services.base import ServiceBase
from core.models.game import BombState, GameState, GameStatus
from core.models.ws import MovimentEvent, PlaceBombEvent
from core.types import PlayerDirectionState


class GameService(ServiceBase):
    """Client service for real-time game WebSocket communication and immediate state feedback."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.websocket: ClientConnection | None = None
        self.state: GameState | None = None
        self.running: bool = False
        self.match_id: str | None = None
        self._token: str | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._game_ended_callbacks: list[Callable[[GameStatus, str | None], None]] = []
        self._moviment_callbacks: list[Callable[[tuple[int, int]], None]] = []

    def register_game_ended_callback(
        self, callback: Callable[[GameStatus, str | None], None]
    ) -> None:
        """Register a callback for when the game ends."""
        self._game_ended_callbacks.append(callback)

    def register_moviment_callback(self, callback: Callable[[tuple[int, int]], None]) -> None:
        self._moviment_callbacks.append(callback)

    def start(self, match_id: str) -> None:
        """Start WebSocket thread for real-time game updates."""
        if self.running:
            return
        self.match_id = match_id
        token = self.app.api_client.auth_token
        if not token:
            raise RuntimeError("User not authenticated")
        self._token = token
        self.running = True
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the WebSocket loop and close the connection."""
        if not self.running:
            return
        self.running = False
        if self.websocket and self._loop:
            asyncio.run_coroutine_threadsafe(self.websocket.close(), self._loop)
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def send_move(self, direction: PlayerDirectionState) -> None:
        """
        Send a movement event to the server and apply local update for instant feedback.
        """
        if not (self.running and self.websocket and self._loop and self.state):
            return
        if self.state.status != GameStatus.PLAYING:
            return
        user = self.app.auth_service.current_user
        if not user:
            return

        # Local state update
        dx, dy = MovimentEvent.dxdy(direction)
        new_position = self.state.move_player(user.id, dx, dy, direction)

        if new_position is None:
            return

        for cb in self._moviment_callbacks:
            cb(new_position)

        # Send to server
        ev = MovimentEvent(direction=direction)
        asyncio.run_coroutine_threadsafe(
            self.websocket.send(json.dumps(ev.model_dump())), self._loop
        )

    def send_bomb(self) -> None:
        """
        Send a place bomb event to the server and update local state immediately.
        """
        if not (self.running and self.websocket and self._loop and self.state):
            return
        user = self.app.auth_service.current_user
        if not user:
            return
        pstate = self.state.players.get(user.id)
        if not pstate:
            return
        # Local update
        bomb = BombState(x=pstate.x, y=pstate.y)
        self.state.add_bomb(user.id, bomb)
        # Send to server
        ev = PlaceBombEvent(x=bomb.x, y=bomb.y)
        asyncio.run_coroutine_threadsafe(self.websocket.send(ev.model_dump_json()), self._loop)

    def _run_loop(self) -> None:
        """Internal: run event loop and establish connection."""
        asyncio.set_event_loop(self._loop)
        if not self._loop:
            return
        self._loop.run_until_complete(self._connect())

    async def _connect(self) -> None:
        """Coroutine to manage WebSocket connection and incoming messages."""
        protocol = "wss" if self.app.settings.server_endpoint_ssl else "ws"
        uri = f"{protocol}://{self.app.settings.server_endpoint}/ws/game/{self.match_id}?token={self._token}"
        try:
            async with connect(uri) as ws:
                self.websocket = ws
                previous_status: GameStatus | None = None
                while self.running:
                    try:
                        raw = await ws.recv()
                        data = json.loads(raw)
                        self.state = GameState.model_validate(data)
                        # Detect end of game
                        if (
                            previous_status == GameStatus.PLAYING
                            and self.state.status != GameStatus.PLAYING
                        ):
                            for cb in self._game_ended_callbacks:
                                cb(self.state.status, self.state.winner_id)
                            break
                        previous_status = self.state.status
                    except ConnectionClosed:
                        break
        except Exception as e:
            print(f"GameService connection error: {e}")
        finally:
            self.running = False
            self.websocket = None
            if self._loop:
                self._loop.stop()
                self._loop.stop()
