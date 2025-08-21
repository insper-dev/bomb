import asyncio
import logging
import threading

from prisma.partials import Opponent
from websockets import ClientConnection, ConnectionClosed, connect
from websockets.exceptions import InvalidHandshake

from client.services.base import ServiceBase
from core.models.ws import MatchMakingEvent
from core.ssl_config import get_websocket_ssl_context


class MatchmakingService(ServiceBase):
    """
    Connect to server, wait for a single 'match_found' message, then notify listeners.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self.websocket: ClientConnection | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self.running: bool = False
        self.match_id: str | None = None
        self.opponent: Opponent | None = None

    def start(self) -> None:
        """Begin matchmaking: opens a WebSocket, blocks until match found."""
        token = self.app.api_client.auth_token
        if not token:
            raise RuntimeError("Not authenticated")
        if self.running:
            return

        self.match_id = None
        self.opponent = None

        self.running = True
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the matchmaking loop and close connection."""
        if not self.running:
            return
        self.running = False

        async def _close_and_stop() -> None:
            if self.websocket and self._loop:
                try:
                    await self.websocket.close()
                finally:
                    self._loop.stop()

        if self.websocket and self._loop:
            asyncio.run_coroutine_threadsafe(_close_and_stop(), self._loop)
        elif self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def _run_loop(self) -> None:
        """Set up the event loop, dispare o handler e mantenha-o vivo."""
        if not self._loop:
            return

        asyncio.set_event_loop(self._loop)
        # registra o handler como tarefa
        self._loop.create_task(self._handler())
        # fica rodando até que alguém chame loop.stop()
        self._loop.run_forever()

        # cleanup: cancela tarefas pendentes e fecha o loop
        pending = asyncio.all_tasks(self._loop)
        for task in pending:
            task.cancel()
        self._loop.run_until_complete(self._loop.shutdown_asyncgens())
        self._loop.close()

    async def _handler(self) -> None:
        """Connect, await match_found, then close."""
        protocol = "wss" if self.app.settings.server_endpoint_ssl else "ws"
        uri = f"{protocol}://{self.app.settings.server_endpoint}/ws/matchmaking?token={self.app.api_client.auth_token}"

        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            if not self.running:
                break

            try:
                # Configure SSL context for websocket connection
                ssl_context = get_websocket_ssl_context() if protocol == "wss" else None
                async with connect(uri, ssl=ssl_context) as ws:
                    self.websocket = ws
                    # aguarda evento match_found
                    while self.running:
                        msg = await ws.recv()
                        data = MatchMakingEvent.model_validate_json(msg)
                        if data.event == "match_found":
                            self.opponent = data.opponent
                            self.match_id = data.match_id
                            self.running = False
                            break
                    return  # sai do handler ao reunir dois jogadores

            except (ConnectionClosed, InvalidHandshake) as e:
                logging.error(f"WS error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    raise

            except Exception as e:
                logging.error(f"Unexpected error in matchmaking: {e}")
                raise

        self.running = False
        self.websocket = None
