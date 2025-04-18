import asyncio
from collections import deque

from fastapi import WebSocket

from server.services.game import game_service


class MatchmakingService:
    """Simple in-memory matchmaking: pairs players as they join, with timeout."""

    def __init__(self, timeout: float = 30.0) -> None:
        # FIFO queue of user_ids waiting for match
        self._queue: deque[str] = deque()
        # Active websocket connections by user_id
        self._connections: dict[str, WebSocket] = {}
        # Futures to block join() until match is ready
        self._futures: dict[str, asyncio.Future[None]] = {}
        # Async lock to protect queue
        self._lock = asyncio.Lock()
        # Max wait time before timing out
        self.timeout = timeout

    async def join(self, user_id: str, ws: WebSocket) -> None:
        """
        Add player to queue and wait for a match or timeout.
        """
        loop = asyncio.get_event_loop()
        fut: asyncio.Future[None] = loop.create_future()

        async with self._lock:
            # Enqueue player
            self._queue.append(user_id)
            self._connections[user_id] = ws
            self._futures[user_id] = fut

            # If two or more players waiting, match them
            if len(self._queue) >= 2:
                u1 = self._queue.popleft()
                u2 = self._queue.popleft()
                ws1 = self._connections.pop(u1)
                ws2 = self._connections.pop(u2)
                fut1 = self._futures.pop(u1)
                fut2 = self._futures.pop(u2)

                # Create the game
                match_id = await game_service.create_game([u1, u2])

                # Notify both players
                msg1 = {"type": "match_found", "match_id": match_id, "opponent_id": u2}
                msg2 = {"type": "match_found", "match_id": match_id, "opponent_id": u1}
                await ws1.send_json(msg1)
                await ws2.send_json(msg2)

                # Close matchmaking sockets
                await ws1.close(code=4000)
                await ws2.close(code=4000)

                # Unblock coroutines
                fut1.set_result(None)
                fut2.set_result(None)

        # Wait here until matched or timeout
        try:
            await asyncio.wait_for(fut, timeout=self.timeout)
        except TimeoutError:
            # Timeout: cleanup queue and futures
            async with self._lock:
                try:
                    self._queue.remove(user_id)
                except ValueError:
                    pass
                self._connections.pop(user_id, None)
                self._futures.pop(user_id, None)

            # Notify player about timeout
            try:
                await ws.send_json(
                    {"type": "queue_timeout", "message": "Matchmaking timed out, please try again."}
                )
            except Exception:
                pass
            # Close connection with timeout code
            await ws.close(code=4001)


matchmaking_service = MatchmakingService()
