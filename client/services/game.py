import asyncio
import json
import threading

from websockets import ClientConnection, ConnectionClosed, connect

from client.services.base import ServiceBase
from core.models.game import GameState, GameStatus
from core.models.ws import MovimentEvent, PlaceBombEvent
from core.types import PlayerDirectionState


class GameService(ServiceBase):
    """
    Service to handle game WebSocket communication for client (e.g., Pygame).
    Maintains current game state and propagates updates via callbacks.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self.websocket: ClientConnection | None = None
        self.state: GameState | None = None
        self.running: bool = False
        self.match_id: str | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._game_ended_callbacks = []

    def register_game_ended_callback(self, callback) -> None:
        """Register a callback for when the game ends"""
        self._game_ended_callbacks.append(callback)

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
        if not self.running:
            return

        self.running = False

        # Verificar se estamos na mesma thread do loop - se sim, não podemos interrompê-lo aqui
        current_thread = threading.current_thread()
        if self._thread and current_thread == self._thread:
            print("Warning: Trying to stop game service from its own thread!")
            return

        # Estamos em thread diferente, podemos fechar o websocket
        if self.websocket and self._loop:
            try:
                asyncio.run_coroutine_threadsafe(self.websocket.close(), self._loop)
            except Exception as e:
                print(f"Error closing websocket: {e}")

        # Paramos o loop
        if self._loop:
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception as e:
                print(f"Error stopping event loop: {e}")

        # Esperamos que a thread termine (com timeout)
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=1)
            except Exception as e:
                print(f"Error joining thread: {e}")

    def send_move(self, direction: PlayerDirectionState) -> None:
        """Send a move command: 'up', 'down', 'left' or 'right', 'stand_by."""
        if not self.running or not self.websocket or not self._loop:
            return

        # Don't send moves if the game has ended
        if self.state and self.state.status != GameStatus.PLAYING:
            return

        try:
            payload = MovimentEvent(direction=direction).model_dump()
            asyncio.run_coroutine_threadsafe(self.websocket.send(json.dumps(payload)), self._loop)
        except Exception:
            pass

    def send_bomb(self) -> None:
        if not self.running or not self.websocket or not self._loop or not self.state:
            return

        if not self.app.auth_service.current_user:
            return

        uid = self.app.auth_service.current_user.id
        p = self.state.players.get(uid)
        if not p:
            return
        try:
            # TODO: esse radius deve ser definido pelo servidor com base nos power-ups ativos.
            ev = PlaceBombEvent(x=p.x, y=p.y, radius=2, explosion_time=1)
            asyncio.run_coroutine_threadsafe(self.websocket.send(ev.model_dump_json()), self._loop)
        except Exception:
            pass

    @property
    def is_game_ended(self) -> bool:
        """Check if the game has ended"""
        if not self.state:
            return False
        return self.state.status != GameStatus.PLAYING

    @property
    def game_result(self) -> str:
        """Get the game result text"""
        if not self.state or self.state.status == GameStatus.PLAYING:
            return "Game in progress"

        if self.state.status == GameStatus.DRAW:
            return "Game ended in a draw"

        if self.state.winner_id:
            user = self.app.auth_service.current_user
            if user and user.id == self.state.winner_id:
                return "You won!"
            return "You lost!"

        return "Game ended"

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
                previous_status = None

                while self.running:
                    try:
                        raw = await ws.recv()
                        data = json.loads(raw)
                        self.state = GameState.model_validate(data)

                        # Check for game end
                        if (
                            previous_status == GameStatus.PLAYING
                            and self.state.status != GameStatus.PLAYING
                        ):
                            # trigger end callbacks
                            for callback in self._game_ended_callbacks:
                                try:
                                    callback(self.state.status, self.state.winner_id)
                                except Exception as e:
                                    print(f"Error in game end callback: {e}")
                            self.running = False
                            await ws.close()
                            break

                        previous_status = self.state.status
                    except ConnectionClosed:
                        break
        except Exception as e:
            print(f"Error in game connection: {e}")
        finally:
            self.running = False
            self.websocket = None
            self._loop = None
