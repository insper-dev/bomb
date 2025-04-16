# Credits: The idea was made by the ClaudeAI.
# The thread-safe, modeling and singleton instance implementation was mabe by @felipeadeildo.
import asyncio
import logging
import time

from fastapi import WebSocket

from core.models.matchmaking import PlayerStatus, QueuedPlayer
from server.services.game import game_service

logger = logging.getLogger(__name__)


class MatchmakingQueue:
    """
    Singleton manager for the matchmaking queue.
    """

    _instance = None

    def __new__(cls) -> "MatchmakingQueue":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        # matchmaking queue for awaiting players
        self.queue: dict[str, QueuedPlayer] = {}
        # websocket connections for each player
        self.connections: dict[str, WebSocket] = {}
        # connection status for each player (last active timestamp)
        self.connection_status: dict[str, float] = {}
        # failed match attempts counter
        self.failed_attempts: dict[str, int] = {}
        # thread-safe lock to access matchmaking queue
        self.lock = asyncio.Lock()

        self.running = False

        # task for processing the matchmaking queue
        self.matchmaking_task = None
        # task for cleaning up dead connections
        self.cleanup_task = None
        # queue process interval in seconds
        self.processing_interval = 1.0
        # cleanup interval in seconds
        self.cleanup_interval = 10.0
        # max wait time in seconds (1 minute by default)
        self.max_wait_time = 60.0
        # connection timeout in seconds (5 seconds by default)
        self.connection_timeout = 5.0
        # max failed match attempts before timeout
        self.max_failed_attempts = 3

        self._initialized = True
        logger.info("Matchmaking queue initialized")

    async def start(self) -> None:
        if self.running:
            return

        self.running = True
        self.matchmaking_task = asyncio.create_task(self._process_queue_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Matchmaking queue processing started")

    async def stop(self) -> None:
        if not self.running:
            return

        self.running = False

        if self.matchmaking_task:
            self.matchmaking_task.cancel()
            try:
                await self.matchmaking_task
            except asyncio.CancelledError:
                pass

        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Matchmaking queue processing stopped")

    async def add_player(self, user_id: str, websocket: WebSocket) -> bool:
        """
        Adds a player to the matchmaking queue.

        Args:
            user_id: ID of the user
            websocket: WebSocket connection

        Returns:
            bool: True if the player was added, False otherwise
        """
        async with self.lock:
            # Check if the player is already in the queue
            if user_id in self.queue:
                # If the player is already in the queue, update the connection
                self.connections[user_id] = websocket
                self.connection_status[user_id] = time.time()
                logger.info(f"Updated connection for player {user_id} in matchmaking queue")

                # Notify the player of their current status
                player = self.queue[user_id]
                await self._notify_player(
                    user_id,
                    {
                        "type": "queue_update",
                        "position": player.position,
                        "wait_time": int(player.wait_duration),
                        "estimated_wait": player.estimated_wait,
                    },
                )
                return True

            # Reset failed attempts counter if exists
            self.failed_attempts.pop(user_id, None)

            # Add the player to the queue
            self.queue[user_id] = QueuedPlayer(user_id=user_id, joined_at=time.time())

            # Register the WebSocket connection and status
            self.connections[user_id] = websocket
            self.connection_status[user_id] = time.time()

            logger.info(f"Player {user_id} added to matchmaking queue")

            # Notify the player that they have joined the queue
            await self._notify_player(
                user_id,
                {
                    "type": "queue_joined",
                    "position": len(self.queue),
                    "estimated_wait": self._estimate_wait_time(len(self.queue)),
                },
            )

            return True

    async def remove_player(self, user_id: str) -> bool:
        """
        Removes a player from the matchmaking queue.

        Args:
            user_id: ID of the user

        Returns:
            bool: True if the player was removed, False otherwise
        """
        async with self.lock:
            # Check if the player is in the queue
            if user_id not in self.queue:
                logger.warning(f"Player {user_id} not in queue")
                return False

            # Remove the player from the queue
            self.queue.pop(user_id, None)

            # Remove the WebSocket connection and status
            self.connections.pop(user_id, None)
            self.connection_status.pop(user_id, None)
            self.failed_attempts.pop(user_id, None)

            logger.info(f"Player {user_id} removed from matchmaking queue")
            return True

    async def _cleanup_loop(self) -> None:
        """Periodically clean up dead connections and timed out players."""
        while self.running:
            try:
                await self._cleanup_connections()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in matchmaking cleanup loop: {e}")
                await asyncio.sleep(self.cleanup_interval)  # Still sleep on error

    async def _cleanup_connections(self) -> None:
        """Clean up dead connections and timed out players."""
        async with self.lock:
            current_time = time.time()

            # Identify players to remove
            to_remove = []

            for user_id, player in self.queue.items():
                # Check if connection is active
                last_active = self.connection_status.get(user_id, 0)

                # If connection is too old, mark for removal
                if current_time - last_active > self.connection_timeout:
                    logger.warning(f"Connection timeout for player {user_id}")
                    to_remove.append(user_id)
                    continue

                # Check for players waiting too long
                wait_time = player.wait_duration
                if wait_time > self.max_wait_time:
                    # Check if we've tried matching too many times
                    failed_count = self.failed_attempts.get(user_id, 0)
                    if failed_count >= self.max_failed_attempts:
                        logger.warning(
                            f"Player {user_id} timed out after {failed_count} failed match attempts"
                        )
                        to_remove.append(user_id)

                        # Notify the player they've been timed out
                        try:
                            if user_id in self.connections:
                                await self.connections[user_id].send_json(
                                    {
                                        "type": "queue_timeout",
                                        "message": "You have been removed from queue due to timeout",  # noqa: E501
                                    }
                                )
                        except Exception as e:
                            logger.error(f"Error notifying player {user_id} about timeout: {e}")

            # Remove identified players
            for user_id in to_remove:
                await self.remove_player(user_id)

    async def _process_queue_loop(self) -> None:
        """Main loop for processing the matchmaking queue."""
        while self.running:
            try:
                # Process the queue
                await self._process_queue()

                # Update estimated wait times for players in the queue
                await self._update_queue_status()

                # Wait for the processing interval
                await asyncio.sleep(self.processing_interval)

            except Exception as e:
                logger.error(f"Error processing matchmaking queue: {e}")
                await asyncio.sleep(self.processing_interval)  # Still sleep on error

    async def _process_queue(self) -> None:
        """Processes the matchmaking queue to find matches."""
        async with self.lock:
            # If there are not enough players, do nothing
            if len(self.queue) < 2:
                return

            # Get players in the queue, sorted by wait time
            players = sorted(self.queue.keys(), key=lambda user_id: self.queue[user_id].joined_at)

            # Process players in pairs
            matched_players = []
            i = 0
            while i < len(players) - 1:
                player1 = players[i]
                player2 = players[i + 1]

                # Try to create a match for the two players
                try:
                    match_id = await self._create_match([player1, player2])

                    # If the match was created successfully, add the players to matched
                    if match_id:
                        # Update player status
                        if player1 in self.queue:
                            self.queue[player1].status = PlayerStatus.MATCHED
                            self.queue[player1].match_id = match_id
                            self.queue[player1].opponent_id = player2

                        if player2 in self.queue:
                            self.queue[player2].status = PlayerStatus.MATCHED
                            self.queue[player2].match_id = match_id
                            self.queue[player2].opponent_id = player1

                        matched_players.extend([player1, player2])

                        # Notify the players about the match
                        await self._notify_match_found(player1, player2, match_id)
                        logger.info(f"Match found: {player1} vs {player2} (match_id: {match_id})")

                        # Reset failed attempts counters
                        self.failed_attempts.pop(player1, None)
                        self.failed_attempts.pop(player2, None)
                    else:
                        # Increment failed attempts counter
                        self.failed_attempts[player1] = self.failed_attempts.get(player1, 0) + 1
                        self.failed_attempts[player2] = self.failed_attempts.get(player2, 0) + 1
                        logger.warning(
                            f"Failed to create match for players {player1} and {player2}"
                        )
                except Exception as e:
                    logger.error(f"Error creating match: {e}")
                    # Increment failed attempts counter
                    self.failed_attempts[player1] = self.failed_attempts.get(player1, 0) + 1
                    self.failed_attempts[player2] = self.failed_attempts.get(player2, 0) + 1

                # Move to the next pair
                i += 2

            # Remove players who got matched from the queue
            for player_id in matched_players:
                self.queue.pop(player_id, None)

    async def _create_match(self, player_ids: list[str]) -> str | None:
        """
        Creates a match for the specified players.

        Args:
            player_ids: List of player IDs

        Returns:
            str: ID of the created match or None in case of error
        """
        try:
            match_id = await game_service.create_game(player_ids)
            return match_id
        except Exception as e:
            logger.error(f"Error creating match: {e}")
            return None

    async def _notify_match_found(self, player1_id: str, player2_id: str, match_id: str) -> None:
        """
        Notifies the players that a match has been found.

        Args:
            player1_id: ID of the first player
            player2_id: ID of the second player
            match_id: ID of the created match
        """
        # Notification data
        match_data = {
            "type": "match_found",
            "match_id": match_id,
            "opponent_id": None,  # Will be customized for each player
            "timestamp": time.time(),
        }

        # Notify the first player
        match_data_1 = match_data.copy()
        match_data_1["opponent_id"] = player2_id
        await self._notify_player(player1_id, match_data_1)

        # Notify the second player
        match_data_2 = match_data.copy()
        match_data_2["opponent_id"] = player1_id
        await self._notify_player(player2_id, match_data_2)

    async def _notify_player(self, player_id: str, data: dict) -> None:
        """
        Sends a notification to a player via WebSocket.

        Args:
            player_id: ID of the player
            data: Data to be sent
        """
        if player_id not in self.connections:
            logger.warning(f"No connection for player {player_id}")
            return

        try:
            # Send the data via WebSocket
            websocket = self.connections[player_id]
            await websocket.send_json(data)

            # Update connection status
            self.connection_status[player_id] = time.time()

            # If this is a match found notification, close the connection properly
            if data.get("type") == "match_found":
                try:
                    # Remove from connections before closing to prevent further attempts to send
                    self.connections.pop(player_id, None)
                    self.connection_status.pop(player_id, None)
                    await websocket.close(code=4000)  # MATCH_FOUND code
                except Exception as close_error:
                    logger.error(f"Error closing WebSocket for player {player_id}: {close_error}")

        except Exception as e:
            logger.error(f"Error notifying player {player_id}: {e}")
            # Remove the connection in case of error
            self.connections.pop(player_id, None)
            self.connection_status.pop(player_id, None)

    async def _update_queue_status(self) -> None:
        """Updates the status of the queue for all players."""
        async with self.lock:
            queue_size = len(self.queue)

            # If there are no players in the queue, do nothing
            if queue_size == 0:
                return

            # Calculate the position of each player in the queue
            players = sorted(self.queue.keys(), key=lambda user_id: self.queue[user_id].joined_at)

            # Update each player
            for i, player_id in enumerate(players):
                # Only update if player is still in the queue and has a connection
                if player_id in self.queue and player_id in self.connections:
                    # Calculate wait time and position
                    position = i + 1
                    wait_time = time.time() - self.queue[player_id].joined_at
                    estimated_wait = self._estimate_wait_time(position)

                    # Update player data
                    self.queue[player_id].position = position
                    self.queue[player_id].wait_time = int(wait_time)
                    self.queue[player_id].estimated_wait = estimated_wait

                    # Notify the player
                    await self._notify_player(
                        player_id,
                        {
                            "type": "queue_update",
                            "position": position,
                            "wait_time": int(wait_time),
                            "estimated_wait": estimated_wait,
                            "queue_size": queue_size,
                        },
                    )

    def _estimate_wait_time(self, position: int) -> int:
        """
        Estimates the wait time based on the position in the queue.

        Args:
            position: Position in the queue

        Returns:
            int: Estimated time in seconds
        """
        # Basic implementation - in a real system it would be more complex
        # based on historical times, number of players online, etc.
        base_time = 5  # Base time in seconds
        return max(0, (position // 2) * base_time)

    def get_queue_status(self) -> dict:
        """
        Get the current status of the matchmaking queue.
        Useful for monitoring and debugging.

        Returns:
            dict: Queue status
        """
        return {
            "queue_size": len(self.queue),
            "players": [
                {
                    "id": player_id,
                    "position": player.position,
                    "wait_time": player.wait_time,
                    "estimated_wait": player.estimated_wait,
                    "status": player.status.name,
                    "joined_at": player.joined_at,
                    "match_id": player.match_id,
                }
                for player_id, player in self.queue.items()
            ],
            "connected_players": list(self.connections.keys()),
        }


# Initialize singleton instance
matchmaking_queue = MatchmakingQueue()
