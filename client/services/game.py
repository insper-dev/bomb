import asyncio
import json
import threading
from typing import Literal

from websockets import ClientConnection, ConnectionClosed, connect

from client.services.base import ServiceBase
from core.models.game import GameState
from core.models.ws import WSMessage


class GameService(ServiceBase):
    """
    Service to handle game WebSocket communication for client (e.g., Pygame).
    Maintains current game state and propagates updates via callbacks.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self.websocket: ClientConnection | None = None
        self.game_state: GameState | None = None
        self.running: bool = False
        self.match_id: str | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def start(self, match_id: str | None = None) -> None:
        """Start WebSocket connection to game server."""
        if match_id:
            self.match_id = match_id
        if not self.match_id:
            raise RuntimeError("No match ID provided")
        token = self.app.api_client.auth_token
        if not token:
            raise RuntimeError("User not authenticated")
        if self.running:
            return
        self.running = True
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop, args=(self.match_id, token), daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop WebSocket loop and close connection."""
        self.running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    def send_move(self, direction: Literal["up", "down", "left", "right"]) -> None:
        """Send a move command: 'up', 'down', 'left' or 'right'."""
        if not self.running or not self.websocket or not self._loop:
            return
        try:
            payload = WSMessage(action="move", direction=direction).model_dump()
            asyncio.run_coroutine_threadsafe(self.websocket.send(json.dumps(payload)), self._loop)
        except Exception:
            pass

    def _run_loop(self, game_id: str, token: str) -> None:
        asyncio.set_event_loop(self._loop)
        if not self._loop:
            return
        self._loop.run_until_complete(self._connect(game_id, token))

    async def _connect(self, game_id: str, token: str) -> None:
        protocol = "wss" if self.app.settings.server_endpoint_ssl else "ws"
        uri = f"{protocol}://{self.app.settings.server_endpoint}/ws/game/{game_id}?token={token}"
        try:
            async with connect(uri) as ws:
                self.websocket = ws
                # Initial empty state
                self.game_state = GameState()
                while self.running:
                    try:
                        raw = await ws.recv()
                        data = json.loads(raw)
                        # Parse into GameState
                        state = GameState.model_validate(data)
                        self.game_state = state
                    except ConnectionClosed:
                        break
        except Exception:
            pass
        finally:
            self.running = False
            self.websocket = None
            self._loop = None
