import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from fastapi import WebSocket
from prisma.models import Match, MatchPlayer
from prisma.types import MatchUpdateInput

from core.models.game import BombState, GameState

logger = logging.getLogger(__name__)


class GameService:
    """Gerencia jogos em memória e suas conexões WebSocket"""

    def __init__(self) -> None:
        self._games: dict[str, GameState] = {}
        self._connections: dict[str, list[WebSocket]] = {}
        self._timers: dict[str, asyncio.Task] = {}

    async def create_game(self, player_ids: list[str]) -> str:
        """
        Cria um novo jogo no banco de dados e em memória.

        Args:
            player_ids: Lista de IDs dos jogadores

        Returns:
            ID do jogo criado
        """
        db_match = await Match.prisma().create(
            data={"players": {"create": [{"userId": player_id} for player_id in player_ids]}}
        )

        game_id = db_match.id

        game = GameState(game_id=game_id)
        game.add_players(player_ids)

        self._games[game_id] = game
        self._connections[game_id] = []

        self._timers[game_id] = asyncio.create_task(self._end_game_after_timeout(game_id, 60))

        logger.info(f"Game created with ID: {game_id}")
        return game_id

    async def _end_game_after_timeout(self, game_id: str, seconds: int) -> None:
        """
        Encerra o jogo após o timeout especificado.

        Args:
            game_id: ID do jogo
            seconds: Tempo em segundos para encerrar o jogo
        """
        try:
            await asyncio.sleep(seconds)
            if game_id in self._games:
                logger.info(f"Game {game_id} timeout reached ({seconds}s). Ending as draw.")
                # Atualiza o objeto de jogo para indicar fim de jogo (empate)
                self._games[game_id].end_game(winner_id=None)
                # Finaliza o jogo no banco de dados
                await self._finalize_match(game_id, winner_id=None)
                # Notifica todos os clientes
                await self.broadcast_state(game_id)
                # Não remove o jogo para permitir que clientes vejam o estado final
        except asyncio.CancelledError:
            logger.info(f"Timer for game {game_id} was cancelled")
        except Exception as e:
            logger.error(f"Error in game timeout handler: {e}")

    async def _finalize_match(self, game_id: str, winner_id: str | None = None) -> None:
        """
        Finaliza o jogo no banco de dados.

        Args:
            game_id: ID do jogo (que é o mesmo do Match no banco)
            winner_id: ID do jogador vencedor, ou None se empate
        """
        # Atualiza o match no banco de dados (o game_id já é o ID do Match)
        update_data: MatchUpdateInput = {
            "endedAt": datetime.now(),
        }

        if winner_id:
            update_data["winnerUserId"] = winner_id
            await MatchPlayer.prisma().update_many(
                where={"matchId": game_id, "userId": winner_id}, data={"isWinner": True}
            )

        await Match.prisma().update(where={"id": game_id}, data=update_data)

        logger.info(f"Match {game_id} finalized. Winner: {winner_id or 'Draw'}")

    def get_game(self, game_id: str) -> GameState:
        """Retorna o GameState existente ou levanta KeyError"""
        return self._games[game_id]

    def add_connection(self, game_id: str, websocket: WebSocket) -> None:
        """Adiciona uma conexão WebSocket a um jogo"""
        if game_id not in self._connections:
            self._connections[game_id] = []
        self._connections[game_id].append(websocket)
        logger.info(
            f"Added connection to game {game_id}, total connections: {len(self._connections[game_id])}"  # noqa: E501
        )

    def remove_connection(self, game_id: str, websocket: WebSocket) -> None:
        """Remove uma conexão WebSocket de um jogo"""
        if game_id in self._connections:
            self._connections[game_id] = [
                ws for ws in self._connections[game_id] if ws != websocket
            ]
            logger.info(
                f"Removed connection from game {game_id}, remaining connections: {len(self._connections[game_id])}"  # noqa: E501
            )

    async def broadcast_state(self, game_id: str) -> None:
        """Envia o estado atual do jogo para todos os jogadores conectados"""
        if game_id not in self._games or game_id not in self._connections:
            return

        game = self._games[game_id]
        state = game.model_dump()
        dead_connections = []

        for websocket in self._connections[game_id]:
            try:
                await websocket.send_json(state)
            except Exception as e:
                logger.error(f"Failed to send state update: {e}")
                dead_connections.append(websocket)

        # Remove conexões mortas
        for websocket in dead_connections:
            self.remove_connection(game_id, websocket)

    async def place_bomb(self, game_id: str, owner_id: str, x: int, y: int, radius: int) -> None:
        game = self._games[game_id]
        bomb_id = str(uuid4())
        bomb = BombState(bomb_id=bomb_id, x=x, y=y, owner_id=owner_id, radius=radius)
        game.add_bomb(bomb)

        logger.info(f"Game {game_id}: bomb placed {bomb_id} at ({x},{y})")
        await self.broadcast_state(game_id)

        # incrementa contador de bombas no DB
        try:
            await MatchPlayer.prisma().update_many(
                where={"matchId": game_id, "userId": owner_id},
                data={"bombsPlaced": {"increment": 1}},
            )
        except Exception as e:
            logger.error(
                f"Failed to update bombsPlaced for match {game_id}, user {owner_id}: {e!s}"
            )

        # programa explosão após 3s
        async def _explode() -> None:
            await asyncio.sleep(3)
            game.explode_bomb(bomb_id)
            explosion_state = game.add_explosion(bomb_id, x, y, radius)
            await self.broadcast_state(game_id)

            logger.info(f"Game {game_id}: bomb {bomb_id} exploded")

            await asyncio.sleep(explosion_state.duration)
            game.clear_explosion(bomb_id)
            await self.broadcast_state(game_id)

        self._timers[f"{game_id}_{bomb_id}"] = asyncio.create_task(_explode())


# instância única para injeção
game_service = GameService()
