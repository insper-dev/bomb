import asyncio
import threading
import time
from collections import deque
from collections.abc import Callable

from websockets import ClientConnection, ConnectionClosed, connect

from client.services.base import ServiceBase
from core.models.game import BombState, GameState, GameStatus
from core.models.ws import CollectPowerUpEvent, MovimentEvent, PlaceBombEvent
from core.serialization import unpack_game_state
from core.ssl_config import get_websocket_ssl_context
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
        self._ping_stats = {
            "count": 0,
            "current_ping": 0.0,
            "average_ping": 0.0,
            "history": [],  # Last 10 pings
            "quality": "good",  # good/fair/poor
        }
        self._latency = 0
        self._packet_loss = 0

        # Compressão de estado
        self._use_compression = True
        self._last_full_state = None

        self._movement_sequence_id = 0
        self._pending_movements = deque(maxlen=50)
        self._server_position = None
        self._prediction_enabled = True

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

    def clear_game_state(self) -> None:
        """Clear game state and match_id for new matchmaking."""
        self.state = None
        self.match_id = None

    def send_move(self, direction: PlayerDirectionState) -> None:
        """
        Send a movement event with client-side prediction and server reconciliation.
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

        # Incrementa sequence ID para rastreamento
        self._movement_sequence_id += 1
        sequence_id = self._movement_sequence_id

        # Calcula nova posição antes de aplicar
        dx, dy = MovimentEvent.dxdy(direction)
        current_player = self.state.players.get(user.id)
        if not current_player:
            return

        # Tenta mover localmente para validar
        new_position = self.state.move_player(user.id, dx, dy, direction)
        if new_position is None:
            return  # Movimento inválido, não envia

        # Armazena movimento pendente para reconciliação
        if self._prediction_enabled:
            self._pending_movements.append(
                {
                    "sequence_id": sequence_id,
                    "direction": direction,
                    "dx": dx,
                    "dy": dy,
                    "old_position": (current_player.x - dx, current_player.y - dy),
                    "new_position": new_position,
                    "timestamp": current_time,
                }
            )

        # Aplica movimento local imediatamente (prediction)
        for cb in self._moviment_callbacks:
            cb(new_position)

        # Seria ideal adicionar sequence_id ao MovimentEvent, mas por agora mantemos simples
        ev1 = MovimentEvent(direction=direction)
        self._queue_message(ev1.model_dump_json())
        self._last_send_time = current_time

        # Envia para servidor com sequence ID
        if any(pu for pu in self.state.map_state.objects if pu.position == new_position):
            ev2 = CollectPowerUpEvent(x=new_position[0], y=new_position[1])
            self._queue_message(ev2.model_dump_json(), high_priority=True)

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

        if pstate.bombs and len(pstate.bombs) >= pstate.max_bombs:
            return  # Limite de bombas atingido

        if any(b for b in pstate.bombs if b.x == pstate.x and b.y == pstate.y):
            return  # Já há uma bomba na posição

        # Local update para responsividade
        bomb = BombState(x=pstate.x, y=pstate.y, radius=pstate.bomb_radius)
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
        print(f"[DEBUG] Tentando conectar ao game WebSocket: {uri[:100]}...")
        print(f"[DEBUG] Match ID: {self.match_id}")
        print(f"[DEBUG] Token exists: {bool(self._token)}")

        try:
            # Configure SSL context for websocket connection
            ssl_context = get_websocket_ssl_context() if protocol == "wss" else None

            async with connect(
                uri,
                ssl=ssl_context,
                ping_interval=None,  # Disable automatic ping
                ping_timeout=10,
                max_size=2**20,
                max_queue=32,
            ) as ws:
                self.websocket = ws
                previous_status: GameStatus | None = None

                # Task para processar ping/pong
                ping_task = asyncio.create_task(self._ping_loop())

                try:
                    while self.running:
                        try:
                            # Timeout menor para responsividade
                            raw = await asyncio.wait_for(ws.recv(), timeout=0.1)

                            # Handle packed data from server
                            if isinstance(raw, bytes):
                                # Unpack msgpack data
                                try:
                                    state_dict = unpack_game_state(raw)
                                    # Convert back to state object
                                    new_state = GameState.model_validate(state_dict)
                                except Exception as e:
                                    print(f"[ERROR] Failed to unpack data: {e}")
                                    continue
                            else:
                                # Fallback for JSON (shouldn't happen in normal operation)
                                raw_str = str(raw)
                                new_state = self._parse_state_optimized(raw_str)

                            if new_state:
                                # Aplica reconciliação de estado antes de atualizar
                                if self._prediction_enabled:
                                    new_state = self._reconcile_server_state(new_state)

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
                pong_waiter = await self.websocket.ping()
                await pong_waiter  # Wait for pong response

                # Calculate latency when pong is received
                if self._ping_start > 0:
                    self._latency = time.time() - self._ping_start
                    self._update_ping_stats()
                    self._ping_start = 0

                await asyncio.sleep(2)  # Ping a cada 2 segundos
            except Exception as e:
                print(f"[DEBUG] Ping failed: {e}")
                break

    def _update_ping_stats(self) -> None:
        """Update ping statistics after receiving pong."""
        # Update ping statistics
        self._ping_stats["count"] += 1
        self._ping_stats["current_ping"] = self._latency
        self._ping_stats["history"].append(self._latency)

        # Keep only last 10 pings
        if len(self._ping_stats["history"]) > 10:
            self._ping_stats["history"] = self._ping_stats["history"][-10:]

        # Calculate average
        history = self._ping_stats["history"]
        self._ping_stats["average_ping"] = sum(history) / len(history)

        # Update quality
        if self._latency < 0.05:
            self._ping_stats["quality"] = "excellent"
        elif self._latency < 0.1:
            self._ping_stats["quality"] = "good"
        elif self._latency < 0.2:
            self._ping_stats["quality"] = "fair"
        else:
            self._ping_stats["quality"] = "poor"

    def _on_pong(self, _data) -> None:
        """Callback de pong para calcular latência - não usado mais."""
        pass

    def _reconcile_server_state(self, server_state: GameState) -> GameState:
        """
        Reconcilia estado do servidor com previsões do cliente.
        Resolve o lag de movimento mantendo apenas movimentos não confirmados.
        """
        if not self.state:
            return server_state

        user = self.app.auth_service.current_user
        if not user or user.id not in server_state.players:
            return server_state

        server_player = server_state.players[user.id]
        local_player = self.state.players.get(user.id)

        if not local_player:
            return server_state

        # Atualiza posição de referência do servidor
        self._server_position = (server_player.x, server_player.y)

        # Se não há movimentos pendentes, aceita estado do servidor
        if not self._pending_movements:
            return server_state

        # Remove movimentos antigos (mais de 1 segundo)
        current_time = time.time()
        self._pending_movements = deque(
            [m for m in self._pending_movements if current_time - m["timestamp"] < 1.0], maxlen=50
        )

        # Se ainda há movimentos pendentes, reaplicá-los sobre a posição do servidor
        if self._pending_movements:
            # Cria uma cópia do estado do servidor para modificar
            reconciled_state = GameState.model_validate(server_state.model_dump())

            # Cria lista de movimentos para processar (evita mutação durante iteração)
            movements_to_process = list(self._pending_movements)
            movements_to_remove = []

            # Reaplicar apenas movimentos que ainda não foram confirmados
            for movement in movements_to_process:
                # Verifica se este movimento já foi processado pelo servidor
                # comparando com a posição esperada
                expected_pos = (
                    movement["old_position"][0] + movement["dx"],
                    movement["old_position"][1] + movement["dy"],
                )

                # Se a posição do servidor ainda não chegou na posição esperada,
                # reaplicar o movimento
                if (server_player.x, server_player.y) != expected_pos:
                    # Tenta reaplicar o movimento
                    new_pos = reconciled_state.move_player(
                        user.id, movement["dx"], movement["dy"], movement["direction"]
                    )
                    if new_pos:
                        # Atualiza callbacks para nova posição
                        for cb in self._moviment_callbacks:
                            cb(new_pos)
                else:
                    # Movimento já foi confirmado pelo servidor, marca para remoção
                    movements_to_remove.append(movement)

            # Remove movimentos confirmados (fora do loop de iteração)
            for movement in movements_to_remove:
                try:
                    self._pending_movements.remove(movement)
                except ValueError:
                    pass  # Já foi removido

            return reconciled_state

        return server_state

    def disable_prediction(self) -> None:
        """Desabilita client-side prediction (útil para debug)."""
        self._prediction_enabled = False
        self._pending_movements.clear()

    def enable_prediction(self) -> None:
        """Habilita client-side prediction."""
        self._prediction_enabled = True
