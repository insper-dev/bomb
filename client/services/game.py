"""
Game service for the client
"""

import asyncio
import json
import logging
import threading
import time
from collections.abc import Callable

import websockets
from websockets.exceptions import ConnectionClosed

from client.services.base import ServiceBase
from core.models.game import (
    BombState,
    Direction,
    MapState,
    PlayerState,
    Position,
    PowerUpState,
    PowerUpType,
    TileType,
)

logger = logging.getLogger(__name__)


class GameService(ServiceBase):
    """Serviço para gerenciar o estado do jogo e a comunicação com o servidor"""

    def __init__(self, app) -> None:
        super().__init__(app)

        # Conexão WebSocket
        self.websocket = None
        self.ws_thread = None
        self.ws_loop = None
        self.running = False

        self.game_id = None
        self.local_player_id = None
        self.map = None
        self.players = {}
        self.bombs = {}
        self.powerups = {}
        self.explosions = []
        self.game_started = False
        self.game_ended = False
        self.winner_id = None

        # Tratamento de mensagens
        self.message_callbacks: dict[str, list[Callable]] = {
            "game_start": [],
            "state_update": [],
            "bomb_placed": [],
            "explosion": [],
            "powerup_collected": [],
            "player_hit": [],
            "game_end": [],
            "error": [],
        }

    # Métodos para registro de callbacks

    def register_message_callback(self, message_type: str, callback: Callable) -> None:
        """Registra um callback para um tipo específico de mensagem"""
        if message_type in self.message_callbacks:
            self.message_callbacks[message_type].append(callback)

    # Métodos de conexão e comunicação WebSocket

    def connect_to_game(self, game_id: str) -> None:
        """Conecta ao jogo especificado via WebSocket"""
        if self.running:
            logger.warning("Já conectado a um jogo")
            return

        if not self.app.auth_service.current_user:
            logger.error("Não está logado")
            return

        # Adiciona um pequeno delay antes de conectar
        time.sleep(0.2)  # 200ms de delay

        self.game_id = game_id
        self.local_player_id = self.app.auth_service.current_user.id
        self.running = True

        # Inicia thread para WebSocket
        self.ws_thread = threading.Thread(target=self._run_websocket_thread)
        self.ws_thread.daemon = True
        self.ws_thread.start()

    def disconnect_from_game(self) -> None:
        """Desconecta do jogo atual"""
        if not self.running:
            return

        self.running = False

        # O processamento de desconexão é tratado na thread do WebSocket

    def _run_websocket_thread(self) -> None:
        """Executa a conexão WebSocket em uma thread separada"""
        self.ws_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.ws_loop)

        try:
            self.ws_loop.run_until_complete(self._websocket_handler())
        except Exception as e:
            logger.error(f"Erro na thread WebSocket: {e}")
        finally:
            self.ws_loop.close()
            self.ws_loop = None
            self.running = False

    async def _websocket_handler(self) -> None:
        """Manipula a conexão WebSocket"""
        # Obtém o token de autenticação
        token = self.app.api_client.auth_token
        if not token:
            logger.error("Sem token de autenticação")
            return

        try:
            protocol = "wss" if self.app.settings.server_endpoint_ssl else "ws"
            uri = f"{protocol}://{self.app.settings.server_endpoint}/ws/game/{self.game_id}?token={token}"

            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                logger.info(f"Conectado ao jogo {self.game_id}")

                # Processa mensagens recebidas
                while self.running:
                    try:
                        message = await websocket.recv()
                        await self._process_message(str(message))
                    except ConnectionClosed:
                        logger.info("Conexão WebSocket fechada")
                        break

                self.websocket = None

        except Exception as e:
            logger.error(f"Erro WebSocket: {e}")

    async def _process_message(self, message_str: str) -> None:
        """Processa uma mensagem recebida do servidor"""
        try:
            message = json.loads(message_str)

            if not isinstance(message, dict):
                logger.warning(f"Formato de mensagem inválido: {message_str}")
                return

            message_type = message.get("type")
            data = message.get("data", {})

            # Atualiza o estado interno com base no tipo de mensagem
            if message_type == "game_start":
                await self._handle_game_start(data)
            elif message_type == "state_update":
                await self._handle_state_update(data)
            elif message_type == "bomb_placed":
                await self._handle_bomb_placed(data)
            elif message_type == "explosion":
                await self._handle_explosion(data)
            elif message_type == "powerup_collected":
                await self._handle_powerup_collected(data)
            elif message_type == "player_hit":
                await self._handle_player_hit(data)
            elif message_type == "game_end":
                await self._handle_game_end(data)

            # Notifica callbacks registrados
            if message_type in self.message_callbacks:
                for callback in self.message_callbacks[message_type]:
                    try:
                        callback(data)
                    except Exception as e:
                        logger.error(f"Erro em callback para mensagem {message_type}: {e}")

        except json.JSONDecodeError:
            logger.warning(f"JSON inválido: {message_str}")
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")

    # Manipuladores de mensagens do servidor - apenas para atualizar estado interno

    async def _handle_game_start(self, data: dict) -> None:
        """Atualiza estado interno com dados iniciais do jogo"""
        try:
            # Inicializa o mapa
            map_data = data.get("map", {})
            self.map = MapState(width=map_data.get("width", 15), height=map_data.get("height", 13))

            # Carrega os tiles do mapa
            tiles_data = map_data.get("tiles", [])
            self.map.tiles = []
            for row in tiles_data:
                tile_row = [TileType(tile) for tile in row]
                self.map.tiles.append(tile_row)

            # Inicializa jogadores
            self.players = {}
            for player_id, player_data in data.get("players", {}).items():
                pos_data = player_data.get("position", {})
                position = Position(pos_data.get("x", 0), pos_data.get("y", 0))

                direction_name = player_data.get("direction", "NONE")
                direction = Direction[direction_name] if direction_name else Direction.NONE

                self.players[player_id] = PlayerState(
                    id=player_id,
                    position=position,
                    direction=direction,
                    alive=player_data.get("alive", True),
                    bomb_count=player_data.get("bomb_count", 1),
                    bomb_limit=player_data.get("bomb_limit", 1),
                    bomb_range=player_data.get("bomb_range", 1),
                    speed=player_data.get("speed", 1.0),
                    score=player_data.get("score", 0),
                )

            # Inicializa bombas e power-ups
            self.bombs = {}
            self.powerups = {}
            self.explosions = []

            # Marca o jogo como iniciado
            self.game_started = True

            logger.info(f"Jogo {self.game_id} inicializado")

        except Exception as e:
            logger.error(f"Erro ao inicializar jogo: {e}")

    async def _handle_state_update(self, data: dict) -> None:
        """Atualiza estado interno com dados de atualização periódica"""
        if not self.game_started or self.game_ended:
            return

        try:
            # Atualiza jogadores
            for player_id, player_data in data.get("players", {}).items():
                if player_id in self.players:
                    player = self.players[player_id]

                    # Atualiza posição
                    pos_data = player_data.get("position", {})
                    player.position.x = pos_data.get("x", player.position.x)
                    player.position.y = pos_data.get("y", player.position.y)

                    # Atualiza direção
                    direction_name = player_data.get("direction", None)
                    if direction_name:
                        player.direction = Direction[direction_name]

                    # Atualiza status de vida
                    player.alive = player_data.get("alive", player.alive)

            # Atualiza bombas
            new_bombs = {}
            for bomb_id, bomb_data in data.get("bombs", {}).items():
                pos_data = bomb_data.get("position", {})
                position = Position(pos_data.get("x", 0), pos_data.get("y", 0))

                # Verifica se é uma bomba nova
                if bomb_id not in self.bombs:
                    player_id = None  # O servidor não envia o player_id na atualização de estado
                    for pid, player in self.players.items():
                        # Assume que a bomba é do jogador mais próximo da posição
                        if (
                            abs(player.position.x - position.x) < 1
                            and abs(player.position.y - position.y) < 1
                        ):
                            player_id = pid
                            break

                    bomb = BombState(
                        id=bomb_id,
                        position=position,
                        player_id=player_id or "",
                        timer=bomb_data.get("timer", 3.0),
                        range=1,  # Valor padrão, será atualizado em eventos específicos
                    )
                else:
                    # Atualiza bomba existente
                    bomb = self.bombs[bomb_id]
                    bomb.position = position
                    bomb.timer = bomb_data.get("timer", bomb.timer)

                new_bombs[bomb_id] = bomb

            # Substitui lista de bombas
            self.bombs = new_bombs

            # Atualiza power-ups
            new_powerups = {}
            for powerup_id, powerup_data in data.get("powerups", {}).items():
                pos_data = powerup_data.get("position", {})
                position = Position(pos_data.get("x", 0), pos_data.get("y", 0))

                type_name = powerup_data.get("type", "BOMB_COUNT")
                type_ = PowerUpType[type_name]

                powerup = PowerUpState(id=powerup_id, position=position, type=type_)

                new_powerups[powerup_id] = powerup

            # Substitui lista de power-ups
            self.powerups = new_powerups

        except Exception as e:
            logger.error(f"Erro ao processar atualização de estado: {e}")

    async def _handle_bomb_placed(self, data: dict) -> None:
        """Atualiza estado interno com dados de bomba colocada"""
        if not self.game_started or self.game_ended:
            return

        try:
            bomb_id = data.get("bomb_id", "")
            player_id = data.get("player_id", "")

            pos_data = data.get("position", {})
            position = Position(pos_data.get("x", 0), pos_data.get("y", 0))

            timer = data.get("timer", 3.0)
            bomb_range = data.get("range", 1)

            # Cria ou atualiza a bomba
            bomb = BombState(
                id=bomb_id, position=position, player_id=player_id, timer=timer, range=bomb_range
            )

            self.bombs[bomb_id] = bomb

        except Exception as e:
            logger.error(f"Erro ao processar colocação de bomba: {e}")

    async def _handle_explosion(self, data: dict) -> None:
        """Atualiza estado interno com dados de explosão"""
        if not self.game_started or self.game_ended:
            return

        try:
            bomb_id = data.get("bomb_id", "")

            # Processa posições afetadas
            affected_positions = []
            for pos_data in data.get("affected_positions", []):
                affected_positions.append(Position(pos_data.get("x", 0), pos_data.get("y", 0)))

            # Processa paredes destruídas
            for pos_data in data.get("destroyed_walls", []):
                # TODO: melhorar a inicialização do mapa para melhor tc
                if not self.map:
                    continue
                x, y = pos_data.get("x", 0), pos_data.get("y", 0)
                if 0 <= y < len(self.map.tiles) and 0 <= x < len(self.map.tiles[y]):
                    self.map.tiles[y][x] = TileType.EMPTY

            # Adiciona explosões ao estado local
            self.explosions.extend(affected_positions)

            # Remove a bomba da lista
            self.bombs.pop(bomb_id, None)

            # Agenda a remoção das explosões
            if self.ws_loop:
                asyncio.run_coroutine_threadsafe(
                    self._remove_explosions(affected_positions), self.ws_loop
                )

        except Exception as e:
            logger.error(f"Erro ao processar explosão: {e}")

    async def _remove_explosions(self, positions: list[Position]) -> None:
        """Remove explosões após um delay"""
        await asyncio.sleep(0.5)  # Duração da animação de explosão

        for pos in positions:
            if pos in self.explosions:
                self.explosions.remove(pos)

    async def _handle_powerup_collected(self, data: dict) -> None:
        """Atualiza estado interno com dados de power-up coletado"""
        if not self.game_started or self.game_ended:
            return

        try:
            powerup_id = data.get("powerup_id", "")
            player_id = data.get("player_id", "")
            powerup_type_name = data.get("powerup_type", "BOMB_COUNT")

            powerup_type = PowerUpType[powerup_type_name]

            # Atualiza stats do jogador
            if player_id in self.players:
                player = self.players[player_id]

                if powerup_type == PowerUpType.BOMB_COUNT:
                    player.bomb_limit += 1
                elif powerup_type == PowerUpType.BOMB_RANGE:
                    player.bomb_range += 1
                elif powerup_type == PowerUpType.SPEED:
                    player.speed += 0.3

            # Remove o power-up da lista
            self.powerups.pop(powerup_id, None)

        except Exception as e:
            logger.error(f"Erro ao processar coleta de power-up: {e}")

    async def _handle_player_hit(self, data: dict) -> None:
        """Atualiza estado interno quando um jogador é atingido"""
        if not self.game_started or self.game_ended:
            return

        try:
            player_id = data.get("player_id", "")

            # Marca o jogador como morto
            if player_id in self.players:
                self.players[player_id].alive = False

        except Exception as e:
            logger.error(f"Erro ao processar jogador atingido: {e}")

    async def _handle_game_end(self, data: dict) -> None:
        """Atualiza estado interno com dados de fim de jogo"""
        if not self.game_started or self.game_ended:
            return

        try:
            winner_id = data.get("winner_id")

            # Marca o jogo como terminado
            self.game_ended = True
            self.winner_id = winner_id

            # Desconecta do jogo após um delay
            if self.ws_loop:
                asyncio.run_coroutine_threadsafe(self._delayed_disconnect(), self.ws_loop)

        except Exception as e:
            logger.error(f"Erro ao processar fim de jogo: {e}")

    async def _delayed_disconnect(self) -> None:
        """Desconecta do jogo após um breve delay"""
        await asyncio.sleep(2.0)  # Aguarda para mostrar tela de fim de jogo
        self.disconnect_from_game()

    # Métodos para envio de ações

    def send_move_action(self, direction: Direction) -> None:
        """Envia ação de movimento para o servidor"""
        if not self.game_started or self.game_ended or not self.local_player_id:
            return

        action = {"type": "move", "data": {"direction": direction.name}, "timestamp": time.time()}

        if self.ws_loop and self.websocket:
            asyncio.run_coroutine_threadsafe(self._send_action(action), self.ws_loop)

    def send_place_bomb_action(self) -> None:
        """Envia ação de colocação de bomba para o servidor"""
        if not self.game_started or self.game_ended or not self.local_player_id:
            return

        if self.local_player_id in self.players:
            player = self.players[self.local_player_id]

            # Arredonda posição para a grade
            x = round(player.position.x)
            y = round(player.position.y)

            action = {
                "type": "place_bomb",
                "data": {"position": {"x": x, "y": y}},
                "timestamp": time.time(),
            }

            if self.ws_loop and self.websocket:
                asyncio.run_coroutine_threadsafe(self._send_action(action), self.ws_loop)

    async def _send_action(self, action: dict) -> None:
        """Envia uma ação para o servidor"""
        if not self.websocket or not self.running:
            return

        try:
            await self.websocket.send(json.dumps(action))
        except Exception as e:
            logger.error(f"Erro ao enviar ação: {e}")

    # Getters para acesso ao estado do jogo

    def get_local_player(self) -> PlayerState | None:
        """Retorna o estado do jogador local"""
        if not self.local_player_id:
            return None
        return self.players.get(self.local_player_id)

    def get_other_players(self) -> dict[str, PlayerState]:
        """Retorna um dicionário de jogadores exceto o local"""
        if not self.local_player_id:
            return self.players

        return {
            player_id: player
            for player_id, player in self.players.items()
            if player_id != self.local_player_id
        }

    def is_game_active(self) -> bool:
        """Verifica se o jogo está ativo (iniciado e não terminado)"""
        return self.game_started and not self.game_ended
