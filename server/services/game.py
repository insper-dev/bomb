import logging

from fastapi import WebSocket

from core.models.game import GameState

logger = logging.getLogger(__name__)


class GameService:
    """Gerencia jogos em memória e suas conexões WebSocket"""

    def __init__(self) -> None:
        self._games: dict[str, GameState] = {}
        self._connections: dict[str, list[WebSocket]] = {}

    async def create_game(self, player_ids: list[str]) -> str:
        """Cria um novo jogo e retorna seu ID"""
        game = GameState()
        game.add_players(player_ids)
        game_id = game.game_id
        self._games[game_id] = game
        self._connections[game_id] = []
        return game_id

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


# instância única para injeção
game_service = GameService()
