"""
Matchmaking service for the client
"""

import asyncio
import json
import logging
import threading
from collections.abc import Callable

import websockets
from websockets.exceptions import ConnectionClosed

from client.services.base import ServiceBase
from core.models.matchmaking import MatchmakingState

logger = logging.getLogger(__name__)


class MatchmakingService(ServiceBase):
    """Service to handle matchmaking WebSocket communication"""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.websocket = None
        self.state = MatchmakingState.DISCONNECTED
        self.queue_position = 0
        self.wait_time = 0
        self.estimated_wait = 0
        self.match_id = None
        self.opponent_id = None
        self.error_message = None

        # Event callbacks
        self.on_state_change_callbacks: list[Callable] = []
        self.on_match_found_callbacks: list[Callable] = []
        self.on_queue_update_callbacks: list[Callable] = []
        self.on_error_callbacks: list[Callable] = []

        # WebSocket connection thread
        self.ws_thread = None
        self.ws_loop = None
        self.running = False

    def add_on_state_change_listener(self, callback: Callable) -> None:
        """Add a listener for state changes

        Args:
            callback: Function to call when state changes
        """
        self.on_state_change_callbacks.append(callback)

    def add_on_match_found_listener(self, callback: Callable) -> None:
        """Add a listener for match found events

        Args:
            callback: Function to call when match is found
        """
        self.on_match_found_callbacks.append(callback)

    def add_on_queue_update_listener(self, callback: Callable) -> None:
        """Add a listener for queue updates

        Args:
            callback: Function to call when queue is updated
        """
        self.on_queue_update_callbacks.append(callback)

    def add_on_error_listener(self, callback: Callable) -> None:
        """Add a listener for errors

        Args:
            callback: Function to call when an error occurs
        """
        self.on_error_callbacks.append(callback)

    def _notify_state_change(self) -> None:
        """Notify all state change listeners"""
        for callback in self.on_state_change_callbacks:
            try:
                callback(self.state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

    def _notify_match_found(self) -> None:
        """Notify all match found listeners"""
        for callback in self.on_match_found_callbacks:
            try:
                callback(self.match_id, self.opponent_id)
            except Exception as e:
                logger.error(f"Error in match found callback: {e}")

    def _notify_queue_update(self) -> None:
        """Notify all queue update listeners"""
        for callback in self.on_queue_update_callbacks:
            try:
                callback(self.queue_position, self.wait_time, self.estimated_wait)
            except Exception as e:
                logger.error(f"Error in queue update callback: {e}")

    def _notify_error(self) -> None:
        """Notify all error listeners"""
        for callback in self.on_error_callbacks:
            try:
                callback(self.error_message)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")

    def _set_state(self, state: MatchmakingState) -> None:
        """Set the state and notify listeners

        Args:
            state: New state
        """
        if self.state != state:
            self.state = state
            self._notify_state_change()

    def join_matchmaking_queue(self) -> None:
        """Join the matchmaking queue"""
        if self.state != MatchmakingState.DISCONNECTED:
            logger.warning("Already connected or connecting to matchmaking")
            return

        if not self.app.auth_service.current_user:
            self.error_message = "Not logged in"
            self._set_state(MatchmakingState.ERROR)
            self._notify_error()
            return

        self._set_state(MatchmakingState.CONNECTING)

        # Start WebSocket connection in a separate thread
        self.running = True
        self.ws_thread = threading.Thread(target=self._run_websocket_thread)
        self.ws_thread.daemon = True
        self.ws_thread.start()

    def leave_matchmaking_queue(self) -> None:
        """Leave the matchmaking queue"""
        if self.state == MatchmakingState.DISCONNECTED:
            return

        self.running = False

        if self.ws_loop is None:
            raise Exception("WebSocket loop is not running")

        # Send leave message if connected
        if self.websocket and self.state == MatchmakingState.QUEUED:
            asyncio.run_coroutine_threadsafe(
                self._send_message({"action": "leave_queue"}), self.ws_loop
            )

        # Thread will clean up and set state to DISCONNECTED

    def _run_websocket_thread(self) -> None:
        """Run the WebSocket connection in a separate thread"""
        self.ws_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.ws_loop)

        try:
            self.ws_loop.run_until_complete(self._websocket_handler())
        except Exception as e:
            logger.error(f"WebSocket thread error: {e}")
            self.error_message = str(e)
            self._set_state(MatchmakingState.ERROR)
            self._notify_error()
        finally:
            self.ws_loop.close()
            self.ws_loop = None
            self._set_state(MatchmakingState.DISCONNECTED)

    async def _websocket_handler(self) -> None:
        """Handle the WebSocket connection"""
        # Get the auth token
        token = self.app.api_client.auth_token
        if not token:
            self.error_message = "No authentication token"
            self._set_state(MatchmakingState.ERROR)
            self._notify_error()
            return

        try:
            # TODO: mover protocolo para dentro de self.app.settings
            protocol = "ws" if self.app.settings.server_debug else "wss"
            uri = f"{protocol}://{self.app.settings.server_endpoint}/ws/matchmaking?token={token}"

            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                self._set_state(MatchmakingState.CONNECTED)

                # Send join queue message
                await self._send_message({"action": "join_queue"})

                # Start ping loop in a separate task
                ping_task = asyncio.create_task(self._ping_loop())

                try:
                    # Process incoming messages
                    while self.running:
                        try:
                            message = await websocket.recv()
                            await self._process_message(str(message))
                        except ConnectionClosed:
                            logger.info("WebSocket connection closed")
                            break
                finally:
                    # Cancel ping task
                    ping_task.cancel()
                    try:
                        await ping_task
                    except asyncio.CancelledError:
                        pass

                    self.websocket = None

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.error_message = str(e)
            self._set_state(MatchmakingState.ERROR)
            self._notify_error()

    async def _ping_loop(self) -> None:
        """Send periodic pings to keep the connection alive"""
        try:
            while self.running and self.websocket:
                await asyncio.sleep(30)  # Send ping every 30 seconds
                if self.websocket:
                    await self._send_message(
                        {"action": "ping", "timestamp": asyncio.get_event_loop().time()}
                    )
        except asyncio.CancelledError:
            # Task was cancelled, exit gracefully
            pass
        except Exception as e:
            logger.error(f"Ping loop error: {e}")

    async def _send_message(self, message: dict) -> None:
        """Send a message to the WebSocket

        Args:
            message: Message to send
        """
        if not self.websocket:
            logger.warning("WebSocket not connected")
            return

        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise

    async def _process_message(self, message_str: str) -> None:
        """Process an incoming WebSocket message

        Args:
            message_str: Message string
        """
        try:
            message = json.loads(message_str)

            if not isinstance(message, dict):
                logger.warning(f"Invalid message format: {message_str}")
                return

            message_type = message.get("type")

            if message_type == "success":
                if message.get("message") == "Joined matchmaking queue":
                    self._set_state(MatchmakingState.QUEUED)

            elif message_type == "queue_joined":
                self._set_state(MatchmakingState.QUEUED)
                self.queue_position = message.get("position", 0)
                self.estimated_wait = message.get("estimated_wait", 0)
                self._notify_queue_update()

            elif message_type == "queue_update":
                self.queue_position = message.get("position", 0)
                self.wait_time = message.get("wait_time", 0)
                self.estimated_wait = message.get("estimated_wait", 0)
                self._notify_queue_update()

            elif message_type == "match_found":
                self.match_id = message.get("match_id")
                self.opponent_id = message.get("opponent_id")
                self._set_state(MatchmakingState.MATCH_FOUND)
                self._notify_match_found()

            elif message_type == "error":
                self.error_message = message.get("message", "Unknown error")
                self._notify_error()

            elif message_type == "pong":
                # Just acknowledge the pong, no action needed
                pass

            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON: {message_str}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
