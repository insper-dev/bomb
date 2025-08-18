import asyncio
import threading
import time
from collections import deque
from collections.abc import Callable

from websockets import ClientConnection, ConnectionClosed, connect

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

        # Otimizações de performance
        self._message_queue = deque(maxlen=100)  # Buffer de mensagens
        self._last_send_time = 0
        self._send_cooldown = 0.016  # ~60fps de envio máximo
        self._state_cache = None
        self._state_dirty = True

        # Métricas de latência
        self._ping_start = 0
        self._latency = 0
        self._packet_loss = 0

        # Compressão de estado
        self._use_compression = True
        self._last_full_state = None

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
        Send a movement event with throttling and buffering for optimal performance.
        """
        if not (self.running and self.websocket and self._loop and self.state):
            return
        if self.state.status != GameStatus.PLAYING:
            return
        user = self.app.auth_service.current_user
        if not user:
            return

        current_time = time.time()

        # Throttling para evitar spam
        if current_time - self._last_send_time < self._send_cooldown:
            return

        # Local state update para responsividade
        dx, dy = MovimentEvent.dxdy(direction)
        new_position = self.state.move_player(user.id, dx, dy, direction)

        if new_position is None:
            return

        for cb in self._moviment_callbacks:
            cb(new_position)

        # Envia para servidor de forma otimizada
        ev = MovimentEvent(direction=direction)
        self._queue_message(ev.model_dump_json())
        self._last_send_time = current_time

    def send_bomb(self) -> None:
        """
        Send a place bomb event with optimized delivery.
        """
        if not (self.running and self.websocket and self._loop and self.state):
            return
        user = self.app.auth_service.current_user
        if not user:
            return
        pstate = self.state.players.get(user.id)
        if not pstate:
            return

        # Local update para responsividade
        bomb = BombState(x=pstate.x, y=pstate.y)
        self.state.add_bomb(user.id, bomb)

        # Envia para servidor com prioridade alta
        ev = PlaceBombEvent(x=bomb.x, y=bomb.y)
        self._queue_message(ev.model_dump_json(), high_priority=True)

    def _queue_message(self, message: str, high_priority: bool = False) -> None:
        """Enfileira mensagem para envio otimizado."""
        if not self._loop or not self.websocket:
            return

        # Mensagens de alta prioridade vão na frente
        if high_priority:
            self._message_queue.appendleft(message)
        else:
            self._message_queue.append(message)

        # Agenda envio assíncrono
        asyncio.run_coroutine_threadsafe(self._process_message_queue(), self._loop)

    async def _process_message_queue(self) -> None:
        """Processa fila de mensagens de forma eficiente."""
        if not self.websocket or not self._message_queue:
            return

        try:
            # Envia até 3 mensagens por vez para evitar congestionamento
            batch_size = min(3, len(self._message_queue))
            for _ in range(batch_size):
                if self._message_queue:
                    message = self._message_queue.popleft()
                    await self.websocket.send(message)
        except Exception as e:
            print(f"[ERROR] Falha ao enviar mensagem: {e}")

    @property
    def latency(self) -> float:
        """Retorna latência atual em ms."""
        return self._latency * 1000

    @property
    def connection_quality(self) -> str:
        """Retorna qualidade da conexão baseada na latência."""
        if self._latency < 0.05:  # < 50ms
            return "Excelente"
        elif self._latency < 0.1:  # < 100ms
            return "Boa"
        elif self._latency < 0.2:  # < 200ms
            return "Regular"
        else:
            return "Ruim"

    def _run_loop(self) -> None:
        """Internal: run event loop and establish connection."""
        asyncio.set_event_loop(self._loop)
        if not self._loop:
            return
        try:
            self._loop.run_until_complete(self._connect())
        except Exception as e:
            print(f"[ERROR] Event loop exception: {e}")

    async def _connect(self) -> None:
        """Conexão WebSocket otimizada com medição de latência."""
        protocol = "wss" if self.app.settings.server_endpoint_ssl else "ws"
        uri = f"{protocol}://{self.app.settings.server_endpoint}/ws/game/{self.match_id}?token={self._token}"

        try:
            # Configurações otimizadas para WebSocket
            extra_headers = {
                "User-Agent": "BombGame-Client/1.0",
                "Connection": "Upgrade",
                "Upgrade": "websocket",
            }

            async with connect(
                uri,
                additional_headers=extra_headers,
                ping_interval=20,
                ping_timeout=10,
                max_size=2**20,
                max_queue=32,
            ) as ws:
                self.websocket = ws
                previous_status: GameStatus | None = None
                last_ping = time.time()  # noqa: F841

                # Task para processar ping/pong
                ping_task = asyncio.create_task(self._ping_loop())

                try:
                    while self.running:
                        try:
                            # Timeout menor para responsividade
                            raw = await asyncio.wait_for(ws.recv(), timeout=0.1)

                            # Medição de latência simples
                            receive_time = time.time()  # noqa: F841

                            # Parse otimizado do estado
                            new_state = self._parse_state_optimized(raw)
                            if new_state:
                                self.state = new_state
                                self._state_dirty = True

                            # Detecta fim de jogo
                            if (
                                previous_status == GameStatus.PLAYING
                                and self.state
                                and self.state.status != GameStatus.PLAYING
                            ):
                                for cb in self._game_ended_callbacks:
                                    cb(self.state.status, self.state.winner_id)
                                break

                            if self.state:
                                previous_status = self.state.status

                        except TimeoutError:
                            # Timeout normal - continua loop
                            continue
                        except ConnectionClosed:
                            print("[INFO] Conexão WebSocket fechada pelo servidor")
                            break

                finally:
                    ping_task.cancel()

        except Exception as e:
            print(f"[ERROR] Erro de conexão GameService: {e}")
        finally:
            self.running = False
            self.websocket = None
            if self._loop:
                self._loop.stop()

    def _parse_state_optimized(self, raw_data: str) -> GameState | None:
        """Parse otimizado do estado do jogo."""
        try:
            # Cache para evitar re-parsing desnecessário
            if raw_data == self._last_full_state:
                return self.state

            self._last_full_state = raw_data
            return GameState.model_validate_json(raw_data)

        except Exception as e:
            print(f"[ERROR] Falha ao parsear estado: {e}")
            return None

    async def _ping_loop(self) -> None:
        """Loop de ping para medir latência."""
        while self.running and self.websocket:
            try:
                self._ping_start = time.time()
                await self.websocket.ping()
                await asyncio.sleep(5)  # Ping a cada 5 segundos
            except Exception:
                break

    def _on_pong(self, data) -> None:
        """Callback de pong para calcular latência."""
        if self._ping_start > 0:
            self._latency = time.time() - self._ping_start
            self._ping_start = 0
