import asyncio
import logging
import threading

import websockets
from prisma.partials import Opponent
from websockets import ClientConnection, connect

from client.services.base import ServiceBase
from core.models.ws import MatchMakingEvent


class MatchmakingService(ServiceBase):
    """
    Connect to server, wait for a single 'match_found' message, then notify listeners.
    """

    oponent: Opponent
    match_id: str

    def __init__(self, app) -> None:
        super().__init__(app)
        self.websocket: ClientConnection | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self.running: bool = False

    def start(self) -> None:
        """Begin matchmaking: opens a WebSocket, blocks until match found."""
        token = self.app.api_client.auth_token
        if not token:
            raise RuntimeError("Not authenticated")
        if self.running:
            return
        self.running = True
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the matchmaking loop and close connection."""
        self.running = False
        if self.websocket and self._loop:
            asyncio.run_coroutine_threadsafe(self.websocket.close(), self._loop)
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        if not self._loop:
            return
        self._loop.run_until_complete(self._handler())

    async def _handler(self) -> None:
        """Connect, await match_found, then close."""
        protocol = "wss" if self.app.settings.server_endpoint_ssl else "ws"
        uri = f"{protocol}://{self.app.settings.server_endpoint}/ws/matchmaking?token={self.app.api_client.auth_token}"

        max_retries = 3
        retry_count = 0
        retry_delay = 1  # seconds

        while retry_count < max_retries and self.running:
            try:
                async with connect(uri) as ws:
                    self.websocket = ws
                    while self.running:
                        raw = await ws.recv()
                        data = MatchMakingEvent.model_validate_json(raw)
                        match data.event:
                            case "match_found":
                                self.opponent = data.opponent  # type: ignore [fé]
                                self.match_id = data.match_id  # type: ignore [fé]

                                self.running = False
                                break

            except (
                websockets.exceptions.ConnectionClosed,
                websockets.exceptions.InvalidHandshake,
            ) as e:
                logging.error(f"WebSocket connection error: {e!s}")
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(retry_delay)
                    continue
                raise  # Re-raise on max retries

            except Exception as e:
                logging.error(f"Unexpected error in matchmaking: {e!s}")
                raise

        self.websocket = None
        self.running = False
