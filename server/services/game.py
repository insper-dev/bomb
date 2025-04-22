import asyncio
import logging
from datetime import datetime

from fastapi import WebSocket
from prisma.models import Match, MatchPlayer
from prisma.types import MatchUpdateInput

from core.models.game import BombState, GameState, GameStatus, PlayerState

logger = logging.getLogger(__name__)


class GameService:
    """Manages in-memory games and WebSocket connections."""

    def __init__(self) -> None:
        self.games: dict[str, GameState] = {}
        self.connections: dict[str, list[WebSocket]] = {}
        self.game_timers: dict[str, asyncio.Task] = {}
        self.bomb_timers: dict[tuple[str, str], asyncio.Task] = {}

    async def create_game(self, player_ids: list[str], timeout: int = 60) -> str:
        match = await Match.prisma().create(
            data={"players": {"create": [{"userId": pid} for pid in player_ids]}}
        )
        game_id = match.id

        game = GameState(game_id=game_id)
        positions = [(1, 1), (len(game.map[0]) - 2, len(game.map) - 2)]
        for i, pid in enumerate(player_ids):
            x, y = positions[i] if i < len(positions) else (0, 0)
            game.players[pid] = PlayerState(
                username=pid,
                direction_state="stand_by",
                x=x,
                y=y,
            )

        self.games[game_id] = game
        self.connections[game_id] = []
        self.game_timers[game_id] = asyncio.create_task(
            self._end_game_after_timeout(game_id, timeout)
        )
        logger.info(f"Created game {game_id} with players {player_ids}")
        return game_id

    async def _end_game_after_timeout(self, game_id: str, seconds: int) -> None:
        try:
            await asyncio.sleep(seconds)
            game = self.games.get(game_id)
            if not game or game.status != GameStatus.PLAYING:
                return
            logger.info(f"Game {game_id} timeout; ending as draw")
            game.end_game()
            await self._finalize_match(game_id)
            await self.broadcast_state(game_id)
        except asyncio.CancelledError:
            logger.debug(f"Timeout for game {game_id} cancelled")
        except Exception as e:
            logger.error(f"Error in timeout handler for game {game_id}: {e}")

    async def _finalize_match(self, game_id: str, winner_id: str | None = None) -> None:
        data: MatchUpdateInput = {"endedAt": datetime.now()}
        if winner_id:
            data["winnerUserId"] = winner_id
        try:
            await Match.prisma().update(where={"id": game_id}, data=data)
            if winner_id:
                await MatchPlayer.prisma().update_many(
                    where={"matchId": game_id, "userId": winner_id},
                    data={"isWinner": True},
                )
            logger.info(f"Finalized match {game_id}; winner: {winner_id or 'draw'}")
        except Exception as e:
            logger.error(f"Failed to finalize match {game_id}: {e}")

    def add_connection(self, game_id: str, ws: WebSocket) -> None:
        conns = self.connections.setdefault(game_id, [])
        conns.append(ws)
        logger.debug(f"Added connection to game {game_id}: {len(conns)} total")

    def remove_connection(self, game_id: str, ws: WebSocket) -> None:
        conns = self.connections.get(game_id, [])
        if ws in conns:
            conns.remove(ws)
            logger.debug(f"Removed connection from game {game_id}: {len(conns)} remaining")

    async def broadcast_state(self, game_id: str) -> None:
        game = self.games.get(game_id)
        conns = self.connections.get(game_id, [])
        if not game or not conns:
            return
        state = game.model_dump()
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(state)
            except Exception as e:
                logger.warning(f"Broadcast failed for {game_id}: {e}")
                dead.append(ws)
        for ws in dead:
            self.remove_connection(game_id, ws)

    async def place_bomb(
        self,
        game_id: str,
        owner_id: str,
        x: int,
        y: int,
    ) -> None:
        # TODO: define deplay and radius based on the active powerups.
        radius = 1
        delay = 2
        game = self.games.get(game_id)
        if not game or game.status != GameStatus.PLAYING:
            return

        bomb = BombState(x=x, y=y)
        game.players[owner_id].bombs.append(bomb)
        logger.debug(f"Game {game_id}: bomb {bomb.id} placed by {owner_id}")
        await self.broadcast_state(game_id)
        asyncio.create_task(self._increment_bombs_placed(game_id, owner_id))
        task = asyncio.create_task(
            self._handle_explosion(game_id, owner_id, bomb.id, x, y, radius, delay)
        )
        self.bomb_timers[(game_id, bomb.id)] = task

    async def _increment_bombs_placed(self, game_id: str, owner_id: str) -> None:
        try:
            await MatchPlayer.prisma().update_many(
                where={"matchId": game_id, "userId": owner_id},
                data={"bombsPlaced": {"increment": 1}},
            )
        except Exception as e:
            logger.error(f"Error updating bombsPlaced for {game_id}, user {owner_id}: {e}")

    async def _handle_explosion(
        self,
        game_id: str,
        owner_id: str,
        bomb_id: str,
        x: int,
        y: int,
        radius: int,
        delay: float,
    ) -> None:
        try:
            await asyncio.sleep(delay)
            game = self.games.get(game_id)
            if not game:
                return
            # Mark explosion time
            game.explode_bomb(owner_id, bomb_id)
            await self.broadcast_state(game_id)

            # Immediate hit detection
            hits = [
                pid
                for pid, p in game.players.items()
                if (p.x == x and abs(p.y - y) <= radius) or (p.y == y and abs(p.x - x) <= radius)
            ]
            if hits:
                winners = [pid for pid in game.players if pid not in hits]
                winner = winners[0] if winners else None
                if winner:
                    game.end_game(winner)
                    asyncio.create_task(self._declare_winner(game_id, winner))
                    await self.broadcast_state(game_id)
                    return
        except asyncio.CancelledError:
            logger.debug(f"Explosion cancelled for bomb {bomb_id} in game {game_id}")
        except Exception as e:
            logger.error(f"Error during explosion for {bomb_id} in game {game_id}: {e}")

    async def _declare_winner(self, game_id: str, winner_id: str) -> None:
        try:
            await MatchPlayer.prisma().update_many(
                where={"matchId": game_id, "userId": winner_id},
                data={"isWinner": True},
            )
            await self._finalize_match(game_id, winner_id)
        except Exception as e:
            logger.error(f"Failed to declare winner for game {game_id}: {e}")

    def cancel_timers(self, game_id: str) -> None:
        if task := self.game_timers.pop(game_id, None):
            task.cancel()
        to_cancel = [key for key in self.bomb_timers if key[0] == game_id]
        for key in to_cancel:
            if task := self.bomb_timers.pop(key, None):
                task.cancel()


game_service = GameService()
