import asyncio
import logging
from datetime import datetime

from fastapi import WebSocket
from icecream import ic
from prisma.models import Match, MatchPlayer, User
from prisma.types import MatchUpdateInput

from core.models.game import BombState, GameState, GameStatus, PlayerState
from core.serialization import get_state_hash, pack_game_state

logger = logging.getLogger(__name__)


class GameService:
    """Manages in-memory games and WebSocket connections."""

    def __init__(self) -> None:
        self.games: dict[str, GameState] = {}
        self.connections: dict[str, list[WebSocket]] = {}
        self.game_timers: dict[str, asyncio.Task] = {}
        self.bomb_timers: dict[tuple[str, str], asyncio.Task] = {}
        self.winner_tasks: set[asyncio.Task] = set()
        # Network optimization tracking
        self.last_state_hashes: dict[str, str] = {}
        self.packet_counters: dict[str, int] = {}

    async def create_game(self, player_ids: list[str], timeout: int = 60) -> str:
        ic(player_ids, timeout)
        match = await Match.prisma().create(
            data={"players": {"create": [{"userId": pid} for pid in player_ids]}}
        )
        game_id = match.id
        ic(game_id)

        players: list[User] = [
            await User.prisma().find_unique(where={"id": pid}) for pid in player_ids
        ]  # type: ignore [fé que o ID existe.]

        game = GameState(game_id=game_id)
        positions = [(1, 1), (len(game.map[0]) - 2, len(game.map) - 2)]
        ic(positions)

        for i, player in enumerate(players):
            x, y = positions[i] if i < len(positions) else (0, 0)
            game.players[player.id] = PlayerState(
                username=player.username,
                direction_state="stand_by",
                x=x,
                y=y,
            )
            ic(player, x, y)

        self.games[game_id] = game
        self.connections[game_id] = []
        self.game_timers[game_id] = asyncio.create_task(
            self._end_game_after_timeout(game_id, timeout)
        )
        ic(len(self.games), game_id in self.games)
        logger.info(f"Created game {game_id} with players {player_ids}")
        return game_id

    async def _end_game_after_timeout(self, game_id: str, seconds: int) -> None:
        try:
            ic(f"Game {game_id} timeout countdown: {seconds}s")
            await asyncio.sleep(seconds)
            game = self.games.get(game_id)
            ic(game_id, game is not None, game.status if game else None)
            if not game or game.status != GameStatus.PLAYING:
                ic(f"Game {game_id} not eligible for timeout ending")
                return
            logger.info(f"Game {game_id} timeout; ending as draw")
            game.end_game()
            ic(game.status)
            await self._finalize_match(game_id)
            await self.broadcast_state(game_id)
        except asyncio.CancelledError:
            ic(f"Timeout cancelled for game {game_id}")
            logger.debug(f"Timeout for game {game_id} cancelled")
        except Exception as e:
            ic(f"Error in timeout: {type(e).__name__}", str(e))
            logger.error(f"Error in timeout handler for game {game_id}: {e}")

    async def _finalize_match(self, game_id: str, winner_id: str | None = None) -> None:
        ic(game_id, winner_id)
        data: MatchUpdateInput = {"endedAt": datetime.now()}
        if winner_id:
            data["winnerUserId"] = winner_id
        try:
            ic(data)
            await Match.prisma().update(where={"id": game_id}, data=data)
            if winner_id:
                await MatchPlayer.prisma().update_many(
                    where={"matchId": game_id, "userId": winner_id},
                    data={"isWinner": True},
                )
                ic(f"Updated winner status for {winner_id}")
            logger.info(f"Finalized match {game_id}; winner: {winner_id or 'draw'}")
        except Exception as e:
            ic(f"Error finalizing match: {type(e).__name__}", str(e))
            logger.error(f"Failed to finalize match {game_id}: {e}")

    def add_connection(self, game_id: str, ws: WebSocket) -> None:
        conns = self.connections.setdefault(game_id, [])
        conns.append(ws)
        ic(game_id, len(conns))
        logger.debug(f"Added connection to game {game_id}: {len(conns)} total")

    def remove_connection(self, game_id: str, ws: WebSocket) -> None:
        conns = self.connections.get(game_id, [])
        if ws in conns:
            conns.remove(ws)
            ic(game_id, len(conns))
            logger.debug(f"Removed connection from game {game_id}: {len(conns)} remaining")

    async def broadcast_state(self, game_id: str) -> None:
        game = self.games.get(game_id)
        conns = self.connections.get(game_id, [])
        ic(game_id, game is not None, len(conns))
        if not game or not conns:
            return

        # Generate state with packet ID for tracking
        packet_id = self.packet_counters.get(game_id, 0) + 1
        self.packet_counters[game_id] = packet_id

        state_dict = game.model_dump()

        # Check if state actually changed using hash
        current_hash = get_state_hash(state_dict)
        last_hash = self.last_state_hashes.get(game_id, "")

        if current_hash == last_hash:
            ic(f"State unchanged for {game_id}, skipping broadcast")
            return

        self.last_state_hashes[game_id] = current_hash

        # Pack with msgpack for better performance than JSON+gzip
        packed, stats = pack_game_state(state_dict)

        ic(
            f"State packing: {stats['json_size']}B -> {stats['packed_size']}B "
            f"({stats['size_reduction']:.1f}% reduction) via {stats['format']}"
        )

        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_bytes(packed)
            except Exception as e:
                ic(f"Broadcast error: {type(e).__name__}")
                logger.warning(f"Broadcast failed for {game_id}: {e}")
                dead.append(ws)
        for ws in dead:
            self.remove_connection(game_id, ws)
        ic("Broadcast complete, dead connections:", len(dead))

    async def place_bomb(
        self,
        game_id: str,
        owner_id: str,
        x: int,
        y: int,
    ) -> None:
        ic(game_id, owner_id, x, y)
        # TODO: definir o delay com base em powerups
        delay = 2
        game = self.games.get(game_id)
        if not game or game.status != GameStatus.PLAYING:
            ic(
                "Cannot place bomb - game invalid or not playing",
                game_id,
                game.status if game else None,
            )
            return

        # TODO: criar bomba com powerups (só aumento de raio)
        bomb = BombState(x=x, y=y)
        ic(bomb)
        game.players[owner_id].bombs.append(bomb)
        logger.debug(f"Game {game_id}: bomb {bomb.id} placed by {owner_id}")
        await self.broadcast_state(game_id)
        # ! possível memory leak.
        asyncio.create_task(self._increment_bombs_placed(game_id, owner_id))  # noqa: RUF006

        task = asyncio.create_task(self._handle_explosion(game_id, owner_id, bomb.id, delay))
        self.bomb_timers[(game_id, bomb.id)] = task
        ic(f"Bomb timer set for {delay}s", bomb.id)

    async def _increment_bombs_placed(self, game_id: str, owner_id: str) -> None:
        try:
            ic(game_id, owner_id)
            await MatchPlayer.prisma().update_many(
                where={"matchId": game_id, "userId": owner_id},
                data={"bombsPlaced": {"increment": 1}},
            )
            ic("Bombs placed incremented")
        except Exception as e:
            ic(f"Error incrementing bombs: {type(e).__name__}", str(e))
            logger.error(f"Error updating bombsPlaced for {game_id}, user {owner_id}: {e}")

    # Removido o parâmetro radius, já que agora é uma propriedade da bomba
    async def _handle_explosion(
        self,
        game_id: str,
        owner_id: str,
        bomb_id: str,
        delay: float,
    ) -> None:
        try:
            # 1. Aguarda o delay inicial da bomba
            ic(f"Explosion countdown for bomb {bomb_id}: {delay}s")
            await asyncio.sleep(delay)
            game = self.games.get(game_id)
            if not game:
                ic(f"Game {game_id} not found for explosion")
                return

            # 2. Marca a explosão e calcula tiles afetados (sem remover a bomba ainda)
            affected_tiles = game.explode_bomb(owner_id, bomb_id, remove_bomb=False)
            ic(
                f"Bomb {bomb_id} exploded",
                len(affected_tiles),
                affected_tiles[:5] if affected_tiles else [],
            )

            # 3. Broadcast do estado com animação de explosão
            await self.broadcast_state(game_id)

            # 4. Aguarda tempo para a animação rodar
            animation_delay = 0.8  # segundos
            await asyncio.sleep(animation_delay)

            # 5. Remove a bomba e atualiza estado final
            if game := self.games.get(game_id):  # Re-fetch game to ensure it still exists
                game.explode_bomb(owner_id, bomb_id, remove_bomb=True)
                await self.broadcast_state(game_id)

                # 6. Verifica hits e processa fim de jogo se necessário
                hits = [pid for pid, p in game.players.items() if (p.x, p.y) in affected_tiles]
                ic("Players hit:", hits)

                # Só encerra o jogo se alguém foi atingido
                if hits:
                    # vencedor é quem NÃO foi atingido (assumindo 2 jogadores)
                    survivors = [pid for pid in game.players if pid not in hits]
                    winner = survivors[0] if survivors else None
                    ic("Players hit:", hits, "Survivors:", survivors, "Winner:", winner)
                    game.end_game(winner)

                    # atualiza banco e notifica
                    if winner:  # Only declare a winner if one exists
                        ic(f"Declaring winner: {winner}")
                        task = asyncio.create_task(self._declare_winner(game_id, winner))
                        self.winner_tasks.add(task)
                        task.add_done_callback(self.winner_tasks.discard)
                    else:
                        # If there are hits but no winner, it's a draw
                        ic("Hits but no winner - finalizing as draw")
                        task = asyncio.create_task(self._finalize_match(game_id))
                        self.winner_tasks.add(task)
                        task.add_done_callback(self.winner_tasks.discard)

            # Always broadcast state updates, but only continue game if no hits
            await self.broadcast_state(game_id)
            return

        except asyncio.CancelledError:
            ic(f"Explosion cancelled for bomb {bomb_id}")
            logger.debug(f"Explosion cancelled for bomb {bomb_id} in game {game_id}")
        except Exception as e:
            ic(f"Error in explosion: {type(e).__name__}", str(e))
            logger.error(f"Error during explosion for {bomb_id} in game {game_id}: {e}")

    async def _declare_winner(self, game_id: str, winner_id: str) -> None:
        try:
            ic(game_id, winner_id)
            await MatchPlayer.prisma().update_many(
                where={"matchId": game_id, "userId": winner_id},
                data={"isWinner": True},
            )
            ic("Winner status updated in database")
            await self._finalize_match(game_id, winner_id)
        except Exception as e:
            ic(f"Error declaring winner: {type(e).__name__}", str(e))
            logger.error(f"Failed to declare winner for game {game_id}: {e}")

    def cancel_timers(self, game_id: str) -> None:
        ic(game_id)
        if task := self.game_timers.pop(game_id, None):
            task.cancel()
            ic("Game timer cancelled")
        to_cancel = [key for key in self.bomb_timers if key[0] == game_id]
        ic(f"Bomb timers to cancel: {len(to_cancel)}")
        for key in to_cancel:
            if task := self.bomb_timers.pop(key, None):
                task.cancel()
                ic(f"Bomb timer cancelled for {key[1]}")


game_service = GameService()
