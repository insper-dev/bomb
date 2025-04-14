# Credits: The idea was made by the ClaudeAI.
# The thread-safe, modeling and singleton instance implementation was mabe by @felipeadeildo.
import asyncio
import logging
import time

from fastapi import WebSocket

from core.models.matchmaking import QueuedPlayer
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
        # thread-safe lock to access matchmaking queue
        self.lock = asyncio.Lock()

        self.running = False

        # task for processing the matchmaking queue
        self.matchmaking_task = None
        # queue process interval in seconds
        self.processing_interval = 1.0
        self.max_wait_time = 60.0  # 1 minute

        self._initialized = True
        logger.info("Matchmaking queue initialized")

    async def start(self) -> None:
        if self.running:
            return

        self.running = True
        self.matchmaking_task = asyncio.create_task(self._process_queue_loop())
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
                logger.warning(f"Player {user_id} already in queue")
                return False

            # Add the player to the queue
            self.queue[user_id] = QueuedPlayer(user_id=user_id, joined_at=time.time())

            # Register the WebSocket connection
            self.connections[user_id] = websocket

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

            # Remove the WebSocket connection
            self.connections.pop(user_id, None)

            logger.info(f"Player {user_id} removed from matchmaking queue")
            return True

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
        # Continue the loop even in case of an error

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

                # Create a match for the two players
                match_id = await self._create_match([player1, player2])

                # If the match was created successfully, add the players to matched
                if match_id:
                    matched_players.extend([player1, player2])

                    # Notify the players about the match
                    await self._notify_match_found(player1, player2, match_id)
                    logger.info(f"Match found: {player1} vs {player2} (match_id: {match_id})")

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
        # try:
        match_id = await game_service.create_game(player_ids)
        return match_id
        # except Exception as e:
        #     logger.error(f"Error creating match: {e}")
        #     return None

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

            # If this is a match found notification, close the connection properly
            if data.get("type") == "match_found":
                try:
                    # Remove from connections before closing to prevent further attempts to send
                    self.connections.pop(player_id, None)
                    await websocket.close(code=4000)  # MATCH_FOUND code
                except Exception as close_error:
                    logger.error(f"Error closing WebSocket for player {player_id}: {close_error}")

        except Exception as e:
            logger.error(f"Error notifying player {player_id}: {e}")
            # Remove the connection in case of error
            self.connections.pop(player_id, None)

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

                    # Check queue timeout
                    if wait_time > self.max_wait_time:
                        # In a real system, this player could be paired with bots
                        # or relax the matchmaking criteria
                        pass

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


matchmaking_queue = MatchmakingQueue()
