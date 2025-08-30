import asyncio
import logging
import random
from datetime import datetime
from xmlrpc.client import Boolean

from fastapi import WebSocket
from icecream import ic
from prisma.models import Match, MatchPlayer, User
from prisma.types import MatchUpdateInput

from core.models.game import BombState, GameState, GameStatus, PlayerState, PowerUpType
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
        # Background tasks tracking for proper cleanup
        self.background_tasks: set[asyncio.Task] = set()

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

        game = GameState(game_id=game_id, time_start=timeout)
        positions = game.map_state.start_positions
        if len(players) < 3:
            positions = [max(positions), min(positions)]

        skins = ["carlitos", "rogerio", "claudio"]
        if len(players) <= 4:
            skins.append(random.choice(["carlitos", "rogerio", "claudio"]))

        for i, player in enumerate(players):
            skin = random.choice(skins)
            skins.remove(skin)
            x, y = positions[i] if i < len(positions) else (0, 0)
            game.players[player.id] = PlayerState(
                username=player.username, direction_state="stand_by", x=x, y=y, skin=skin
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
            pids = self.games[game_id].players.keys()
            for pid in pids:
                await MatchPlayer.prisma().update(
                    where={"matchId_userId": {"matchId": game_id, "userId": pid}},
                    data={
                        "isWinner": False,
                        "playersKilled": self.games[game_id].players[pid].kills,
                    },
                )

            if winner_id:
                await MatchPlayer.prisma().update_many(
                    where={"matchId": game_id, "userId": winner_id},
                    data={
                        "isWinner": True,
                    },
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

            # Properly close the WebSocket connection
            if not ws.client_state.closed:
                close_task = asyncio.create_task(ws.close())
                self.background_tasks.add(close_task)
                close_task.add_done_callback(self.background_tasks.discard)

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
        game = self.games.get(game_id)
        if not game or game.status != GameStatus.PLAYING:
            ic(
                "Cannot place bomb - game invalid or not playing",
                game_id,
                game.status if game else None,
            )
            return

        player = game.players.get(owner_id)
        if not player:
            ic(f"Player {owner_id} not found in game {game_id}")
            return

        if player.alive is False:
            ic(f"Player {owner_id} is not alive in game {game_id}, cannot place bomb")
            return

        # TODO: criar bomba com powerups (só aumento de raio)
        bomb = BombState(x=x, y=y, radius=player.bomb_radius)
        ic(bomb)
        player.bombs.append(bomb)
        delay = player.bomb_delay  # seconds
        logger.debug(
            f"Game {game_id}: bomb {bomb.id} placed by {owner_id} with radius {bomb.radius}"
        )
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

    async def _check_if_hitted(self, game_id: str, hits: list[str], owner_id: str) -> Boolean:
        try:
            ic("Players hit:", hits)
            if not hits:
                return False
            owner = self.games[game_id].players[owner_id]

            hitteds = [
                pid for pid, p in self.games[game_id].players.items() if pid in hits and p.alive
            ]
            for player in hitteds:
                self.games[game_id].players[player].alive = False
                if player != owner_id:
                    owner.kills += 1

            await asyncio.sleep(
                0.1
            )  # Pequena pausa para garantir atualização antes de verificar vencedores
            survivors = [pid for pid, p in self.games[game_id].players.items() if p.alive]
            if not survivors:
                result = "draw"
            elif len(survivors) == 1:
                result = survivors[0]
            else:
                result = None

            # atualiza banco e notificaic(f"Declaring winner: {winner}")

            if result and result == "draw":  # Only declare a winner if one exists
                # If there are hits but no winner, it's a draw
                self.games[game_id].end_game()
                ic("Hits but no winner - finalizing as draw")
                task = asyncio.create_task(self._finalize_match(game_id))
                self.winner_tasks.add(task)
                task.add_done_callback(self.winner_tasks.discard)
                ic("Players hit:", hits, "Survivors:", survivors, "Result:", result)
            elif result:
                self.games[game_id].end_game(result)
                task = asyncio.create_task(self._declare_winner(game_id, result))
                self.winner_tasks.add(task)
                task.add_done_callback(self.winner_tasks.discard)
                ic("Players hit:", hits, "Survivors:", survivors, "Winner:", result)
            await self.broadcast_state(game_id)
            return True if result else False
        except Exception as e:
            ic(f"Error checking hits: {type(e).__name__}", str(e))
            logger.error(f"Error checking hits in game {game_id}: {e}")
            return False

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
            # 6. Verifica hits antes da remoção da bomba
            hits = [
                pid for pid, p in game.players.items() if (p.x, p.y) in affected_tiles and p.alive
            ]
            for ple in hits:
                player = game.players.get(ple)
                if player and "shield" in player.power_ups:
                    game.remove_powerup(ple, PowerUpType.SHIELD)
                    hits.remove(ple)
                    ic(f"Player {ple} blocked explosion with SHIELD")
            ic("Players hit:", hits)
            animation_delay = 0.8  # segundos
            await asyncio.sleep(animation_delay)

            # Finaliza imediatamente caso o acertado
            if await self._check_if_hitted(game_id, hits, owner_id):
                return

            # 5. Remove a bomba e atualiza estado final
            game = self.games.get(game_id)  # Re-fetch game to ensure it still exists
            if game is None:
                return

            game.explode_bomb(owner_id, bomb_id, remove_bomb=True)
            await self.broadcast_state(game_id)

            # 6. Verifica hits depois da remoção da bomba
            hits = [pid for pid, p in game.players.items() if (p.x, p.y) in affected_tiles]
            for ple in hits:
                player = game.players.get(ple)
                if player and "shield" in player.power_ups:
                    game.remove_powerup(ple, PowerUpType.SHIELD)
                    hits.remove(ple)
                    ic(f"Player {ple} blocked explosion with SHIELD")
            ic("Players hit:", hits)

            ic("Total players hit:", hits)

            # Só encerra o jogo se alguém foi atingido
            if await self._check_if_hitted(game_id, hits, owner_id):
                return

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

    async def cleanup(self) -> None:
        """Cleanup all background tasks and resources."""
        logger.info("Starting game service cleanup...")

        # Cancel all background tasks
        tasks_to_cancel = list(self.background_tasks)
        for task in tasks_to_cancel:
            task.cancel()

        # Wait for all tasks to complete cancellation
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        self.background_tasks.clear()
        logger.info(f"Cleaned up {len(tasks_to_cancel)} background tasks")

    async def remove_player(self, game_id: str, player_id: str) -> None:
        """Remove a player from the game and handle game state accordingly."""
        ic(game_id, player_id)
        game = self.games.get(game_id)
        if not game:
            ic(f"Game {game_id} not found for player removal")
            return

        player = game.players.get(player_id)
        if not player:
            ic(f"Player {player_id} not found in game {game_id}")
            return

        # Mark player as not alive
        player.alive = False
        logger.info(f"Player {player_id} removed from game {game_id}")

        # Check if this removal ends the game
        survivors = [pid for pid, p in game.players.items() if p.alive]
        if not survivors:
            result = "draw"
        elif len(survivors) == 1:
            result = survivors[0]
        else:
            result = None

        if result and result == "draw":
            game.end_game()
            ic("Player removal led to draw - finalizing match")
            task = asyncio.create_task(self._finalize_match(game_id))
            self.winner_tasks.add(task)
            task.add_done_callback(self.winner_tasks.discard)
        elif result:
            game.end_game(result)
            task = asyncio.create_task(self._declare_winner(game_id, result))
            self.winner_tasks.add(task)
            task.add_done_callback(self.winner_tasks.discard)

        await self.broadcast_state(game_id)


game_service = GameService()
