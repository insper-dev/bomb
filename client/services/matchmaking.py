import asyncio
import json
import logging
import threading
from collections.abc import Callable

import websockets
from websockets import ClientConnection, connect

from client.services.base import ServiceBase


class MatchmakingService(ServiceBase):
    """
    Connect to server, wait for a single 'match_found' message, then notify listeners.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self.websocket: ClientConnection | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self.on_match_found_callbacks: list[Callable[[str, str], None]] = []
        self.running: bool = False

    def add_match_found_listener(self, callback: Callable[[str, str], None]) -> None:
        """Register a listener for match_found(match_id, opponent_id)"""
        self.on_match_found_callbacks.append(callback)

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
        """Stop the matchmaking loop (if needed)."""
        self.running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

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
                        try:
                            raw = await ws.recv()
                            data = json.loads(raw)
                            if data.get("type") == "match_found":
                                match_id = data.get("match_id")
                                opponent = data.get("opponent_id")
                                if not match_id or not opponent:
                                    logging.error("Invalid match data received")
                                    continue

                                self.match_id = match_id

                                for cb in self.on_match_found_callbacks:
                                    try:
                                        cb(match_id, opponent)
                                    except Exception as e:
                                        logging.error(f"Error in match callback: {e!s}")

                                # Success - exit both loops
                                self.running = False
                                break

                        except json.JSONDecodeError as e:
                            logging.error(f"Invalid message format: {e!s}")
                            continue

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
