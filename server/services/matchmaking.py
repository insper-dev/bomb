# Credits: The idea was made by the ClaudeAI.
# The thread-safe, modeling and singleton instance implementation was mabe by @felipeadeildo.
import asyncio
import logging
import time
from datetime import datetime

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

        # Fila de matchmaking para jogadores aguardando
        self.queue: dict[str, QueuedPlayer] = {}
        # Conexões websocket para cada jogador
        self.connections: dict[str, WebSocket] = {}
        # Status de conexão para cada jogador (timestamp da última atividade)
        self.connection_status: dict[str, float] = {}
        # Contador de tentativas falhas de match
        self.failed_attempts: dict[str, int] = {}
        # Jogadores que já foram pareados (para evitar processamento duplicado)
        self.matched_players: set[str] = set()
        # Lock thread-safe para acessar a fila de matchmaking
        self.lock = asyncio.Lock()
        # Flag de execução
        self.running = False

        # Task para processamento da fila de matchmaking
        self.matchmaking_task = None
        # Task para limpeza de conexões mortas
        self.cleanup_task = None
        # Task para envio de heartbeats
        self.heartbeat_task = None
        # Intervalo de processamento em segundos
        self.processing_interval = 1.0
        # Intervalo de limpeza em segundos
        self.cleanup_interval = 5.0
        # Intervalo de heartbeat em segundos
        self.heartbeat_interval = 15.0
        # Tempo máximo de espera em segundos (1 minuto por padrão)
        self.max_wait_time = 60.0
        # Timeout de conexão em segundos (10 segundos por padrão)
        self.connection_timeout = 10.0
        # Máximo de tentativas falhas antes do timeout
        self.max_failed_attempts = 3

        self._initialized = True
        logger.info("Matchmaking queue initialized")

    async def start(self) -> list[asyncio.Task]:
        """Starts the queue processing and returns the created tasks for cleanup"""
        if self.running:
            return []

        self.running = True
        tasks = []

        self.matchmaking_task = asyncio.create_task(self._process_queue_loop())
        tasks.append(self.matchmaking_task)

        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        tasks.append(self.cleanup_task)

        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        tasks.append(self.heartbeat_task)

        logger.info("Matchmaking queue processing started")
        return tasks

    async def stop(self, force: bool = False) -> None:
        """Stops the queue processing.

        Args:
            force: If True, cancel tasks immediately without waiting
        """
        if not self.running:
            return

        self.running = False
        tasks = []

        if self.matchmaking_task:
            self.matchmaking_task.cancel()
            tasks.append(self.matchmaking_task)
            self.matchmaking_task = None

        if self.cleanup_task:
            self.cleanup_task.cancel()
            tasks.append(self.cleanup_task)
            self.cleanup_task = None

        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            tasks.append(self.heartbeat_task)
            self.heartbeat_task = None

        # Only wait for tasks to complete if not forcing
        if tasks and not force:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except asyncio.CancelledError:
                pass

        # Clear internal state to avoid recurring cleanup attempts
        if force:
            self.queue.clear()
            self.connections.clear()
            self.matched_players.clear()
            self.connection_status.clear()
            self.failed_attempts.clear()

        logger.info("Matchmaking queue processing stopped")

    async def add_player(self, user_id: str, websocket: WebSocket) -> bool:
        """
        Adiciona um jogador à fila de matchmaking.

        Args:
            user_id: ID do usuário
            websocket: Conexão WebSocket

        Returns:
            bool: True se o jogador foi adicionado, False caso contrário
        """
        async with self.lock:
            # Verifica se o jogador já foi pareado
            if user_id in self.matched_players:
                logger.warning(
                    f"Player {user_id} já foi pareado e não pode ser readicionado à fila"
                )
                return False

            # Verifica se o jogador já está na fila
            if user_id in self.queue:
                # Se o jogador já está na fila, atualiza a conexão
                self.connections[user_id] = websocket
                self.connection_status[user_id] = time.time()
                logger.info(f"Updated connection for player {user_id} in matchmaking queue")

                # Notifica o jogador do seu status atual
                player = self.queue[user_id]
                await self._notify_player(
                    user_id,
                    {
                        "type": "queue_update",
                        "position": player.position,
                        "wait_time": int(player.wait_duration),
                        "estimated_wait": player.estimated_wait,
                        "queue_size": len(self.queue),
                    },
                )
                return True

            # Reseta o contador de tentativas falhas se existir
            self.failed_attempts.pop(user_id, None)

            # Adiciona o jogador à fila
            # Garante uma posição inicial baseada no tamanho atual da fila
            position = len(self.queue) + 1
            self.queue[user_id] = QueuedPlayer(
                user_id=user_id,
                joined_at=time.time(),
                position=position,
                estimated_wait=self._estimate_wait_time(position),
            )

            # Registra a conexão WebSocket e o status
            self.connections[user_id] = websocket
            self.connection_status[user_id] = time.time()

            logger.info(f"Player {user_id} added to matchmaking queue at position {position}")

            # Notifica o jogador que ele entrou na fila
            await self._notify_player(
                user_id,
                {
                    "type": "queue_joined",
                    "position": position,
                    "wait_time": 0,
                    "estimated_wait": self._estimate_wait_time(position),
                    "queue_size": len(self.queue),
                    "timestamp": time.time(),
                },
            )

            return True

    async def remove_player(self, user_id: str) -> bool:
        """
        Remove um jogador da fila de matchmaking.

        Args:
            user_id: ID do usuário

        Returns:
            bool: True se o jogador foi removido, False caso contrário
        """
        try:
            async with asyncio.timeout(2.0):
                async with self.lock:
                    if user_id not in self.queue:
                        logger.warning(f"Player {user_id} not in queue")
                        return False

                    # Remove o jogador da fila
                    self.queue.pop(user_id, None)

                    # Remove a conexão WebSocket e o status
                    self.connections.pop(user_id, None)
                    self.connection_status.pop(user_id, None)
                    self.failed_attempts.pop(user_id, None)

                    # Remove da lista de matched se estiver lá
                    self.matched_players.discard(user_id)

                    logger.info(f"Player {user_id} removed from matchmaking queue")
                    return True
        except (TimeoutError, asyncio.CancelledError):
            logger.warning(
                f"Timeout or cancellation removing player {user_id} from matchmaking queue"
            )
            # Do minimal cleanup outside lock
            self.connections.pop(user_id, None)
            self.connection_status.pop(user_id, None)
            return False

    async def _heartbeat_loop(self) -> None:
        """Envia heartbeats periódicos para manter as conexões vivas."""
        while self.running:
            try:
                async with self.lock:
                    # Envia um heartbeat para cada jogador na fila
                    current_time = time.time()
                    timestamp_str = datetime.fromtimestamp(current_time).strftime("%H:%M:%S")

                    for user_id, websocket in list(self.connections.items()):
                        if user_id in self.queue:
                            try:
                                await websocket.send_json(
                                    {
                                        "type": "heartbeat",
                                        "timestamp": current_time,
                                        "server_time": timestamp_str,
                                    }
                                )
                                logger.debug(f"Heartbeat sent to player {user_id}")
                            except Exception as e:
                                logger.warning(f"Failed to send heartbeat to player {user_id}: {e}")
                                # Não remova o jogador aqui, deixe o cleanup_loop fazer isso

                # Aguarda o próximo heartbeat
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                # Task cancelada, saia educadamente
                return
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(
                    self.heartbeat_interval
                )  # Continue esperando mesmo em caso de erro

    async def _cleanup_loop(self) -> None:
        """Limpa periodicamente conexões mortas e jogadores em timeout."""
        while self.running:
            try:
                await self._cleanup_connections()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                # Task cancelada, saia educadamente
                return
            except Exception as e:
                logger.error(f"Error in matchmaking cleanup loop: {e}")
                await asyncio.sleep(
                    self.cleanup_interval
                )  # Continue esperando mesmo em caso de erro

    async def _cleanup_connections(self) -> None:
        """Limpa conexões mortas e jogadores em timeout."""
        async with self.lock:
            current_time = time.time()

            # Identifica jogadores para remover
            to_remove = []

            for user_id, player in list(self.queue.items()):
                # Se o jogador já foi pareado, não faça nada
                if user_id in self.matched_players:
                    continue

                # Verifica se a conexão está ativa
                last_active = self.connection_status.get(user_id, 0)

                # Se a conexão está muito velha, marque para remoção
                if current_time - last_active > self.connection_timeout:
                    logger.warning(
                        f"Connection timeout for player {user_id}, last active: "
                        f"{datetime.fromtimestamp(last_active):%H:%M:%S}"
                    )
                    to_remove.append(user_id)
                    continue

                # Verifica jogadores esperando há muito tempo
                wait_time = player.wait_duration
                if wait_time > self.max_wait_time:
                    # Verifica se já tentamos parear muitas vezes
                    failed_count = self.failed_attempts.get(user_id, 0)
                    if failed_count >= self.max_failed_attempts:
                        logger.warning(
                            f"Player {user_id} timed out after {failed_count} failed match attempts"
                        )
                        to_remove.append(user_id)

                        # Notifica o jogador que foi removido por timeout
                        try:
                            if user_id in self.connections:
                                await self.connections[user_id].send_json(
                                    {
                                        "type": "queue_timeout",
                                        "message": "You have been removed from queue due to timeout",  # noqa: E501
                                        "wait_time": int(wait_time),
                                        "timestamp": current_time,
                                    }
                                )
                        except Exception as e:
                            logger.error(f"Error notifying player {user_id} about timeout: {e}")

            # Remove os jogadores identificados
            for user_id in to_remove:
                await self.remove_player(user_id)

    async def _process_queue_loop(self) -> None:
        """Loop principal para processamento da fila de matchmaking."""
        while self.running:
            try:
                # Processa a fila
                await self._process_queue()

                # Atualiza os tempos estimados de espera para jogadores na fila
                await self._update_queue_status()

                # Aguarda o intervalo de processamento
                await asyncio.sleep(self.processing_interval)

            except asyncio.CancelledError:
                # Task cancelada, saia educadamente
                return
            except Exception as e:
                logger.error(f"Error processing matchmaking queue: {e}")
                await asyncio.sleep(
                    self.processing_interval
                )  # Continue esperando mesmo em caso de erro

    async def _process_queue(self) -> None:
        """Processes the matchmaking queue to find matches."""
        async with self.lock:
            # Clear the matched players set at the start of each cycle
            self.matched_players.clear()

            # If there aren't enough players in the queue, don't do anything
            if len(self.queue) < 2:
                return

            # Get players in the queue, ordered by wait time
            # IMPORTANT: Only process players that are still in QUEUED status
            all_players = [
                user_id
                for user_id, player in self.queue.items()
                if player.status == PlayerStatus.QUEUED
            ]
            all_players.sort(key=lambda user_id: self.queue[user_id].joined_at)

            # Log for debugging
            logger.debug(f"Processing queue with {len(all_players)} active players")

            # Process players in pairs
            i = 0
            while i < len(all_players) - 1:
                player1 = all_players[i]
                player2 = all_players[i + 1]

                # Skip if either player has already been matched
                if player1 in self.matched_players or player2 in self.matched_players:
                    i += 1
                    continue

                # Tenta criar uma partida para os dois jogadores
                try:
                    logger.info(f"Attempting to create match for players {player1} and {player2}")
                    match_id = await self._create_match([player1, player2])

                    # Se a partida foi criada com sucesso, adicione os jogadores aos pareados
                    if match_id:
                        # Atualize o status do jogador
                        if player1 in self.queue:
                            self.queue[player1].status = PlayerStatus.MATCHED
                            self.queue[player1].match_id = match_id
                            self.queue[player1].opponent_id = player2
                            self.matched_players.add(player1)

                        if player2 in self.queue:
                            self.queue[player2].status = PlayerStatus.MATCHED
                            self.queue[player2].match_id = match_id
                            self.queue[player2].opponent_id = player1
                            self.matched_players.add(player2)

                        # Notifica os jogadores sobre a partida
                        await self._notify_match_found(player1, player2, match_id)
                        logger.info(f"Match created: {player1} vs {player2} (match_id: {match_id})")

                        # Reseta os contadores de tentativas falhas
                        self.failed_attempts.pop(player1, None)
                        self.failed_attempts.pop(player2, None)
                    else:
                        # Incrementa o contador de tentativas falhas
                        self.failed_attempts[player1] = self.failed_attempts.get(player1, 0) + 1
                        self.failed_attempts[player2] = self.failed_attempts.get(player2, 0) + 1
                        logger.warning(
                            f"Failed to create match for players {player1} and {player2}"
                        )
                except Exception as e:
                    logger.error(f"Error creating match: {e}")
                    # Incrementa o contador de tentativas falhas
                    self.failed_attempts[player1] = self.failed_attempts.get(player1, 0) + 1
                    self.failed_attempts[player2] = self.failed_attempts.get(player2, 0) + 1

                # Avança para o próximo par
                i += 2

            # Remove jogadores que foram pareados da fila
            for player_id in list(self.matched_players):
                await self.remove_player(player_id)
                logger.info(f"Player {player_id} removed from queue after matching")

    async def _create_match(self, player_ids: list[str]) -> str | None:
        """
        Cria uma partida para os jogadores especificados.

        Args:
            player_ids: Lista de IDs de jogadores

        Returns:
            str: ID da partida criada ou None em caso de erro
        """
        try:
            match_id = await game_service.create_game(player_ids)
            return match_id
        except Exception as e:
            logger.error(f"Error creating match: {e}")
            return None

    async def _notify_match_found(self, player1_id: str, player2_id: str, match_id: str) -> None:
        """
        Notifica os jogadores que uma partida foi encontrada.

        Args:
            player1_id: ID do primeiro jogador
            player2_id: ID do segundo jogador
            match_id: ID da partida criada
        """
        # Dados da notificação
        timestamp = time.time()
        timestamp_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

        match_data = {
            "type": "match_found",
            "match_id": match_id,
            "opponent_id": None,  # Será personalizado para cada jogador
            "timestamp": timestamp,
            "server_time": timestamp_str,
        }

        # Notifica o primeiro jogador
        match_data_1 = match_data.copy()
        match_data_1["opponent_id"] = player2_id
        await self._notify_player(player1_id, match_data_1)

        # Notifica o segundo jogador
        match_data_2 = match_data.copy()
        match_data_2["opponent_id"] = player1_id
        await self._notify_player(player2_id, match_data_2)

    async def _notify_player(self, player_id: str, data: dict) -> None:
        """
        Envia uma notificação para um jogador via WebSocket.

        Args:
            player_id: ID do jogador
            data: Dados a serem enviados
        """
        if player_id not in self.connections:
            logger.warning(f"No connection for player {player_id}")
            return

        try:
            # Envia os dados via WebSocket
            websocket = self.connections[player_id]
            await websocket.send_json(data)

            # Atualiza o status da conexão
            self.connection_status[player_id] = time.time()

            # Se esta é uma notificação de partida encontrada, feche a conexão adequadamente
            if data.get("type") == "match_found":
                try:
                    # Remove da conexão antes de fechar para evitar novas tentativas de envio
                    self.connections.pop(player_id, None)
                    self.connection_status.pop(player_id, None)
                    await websocket.close(code=4000)  # código MATCH_FOUND
                except Exception as close_error:
                    logger.error(f"Error closing WebSocket for player {player_id}: {close_error}")

        except Exception as e:
            logger.error(f"Error notifying player {player_id}: {e}")
            # Remove a conexão em caso de erro
            self.connections.pop(player_id, None)
            self.connection_status.pop(player_id, None)

    async def _update_queue_status(self) -> None:
        """Atualiza o status da fila para todos os jogadores."""
        async with self.lock:
            # Filtra jogadores que não foram pareados
            active_players = [p for p in self.queue.keys() if p not in self.matched_players]

            # Se não houver jogadores ativos na fila, não faça nada
            if not active_players:
                return

            # Ordena jogadores por tempo de espera
            active_players = sorted(
                active_players, key=lambda user_id: self.queue[user_id].joined_at
            )

            # Atualiza cada jogador
            for i, player_id in enumerate(active_players):
                # Só atualiza se o jogador ainda estiver na fila e tiver uma conexão
                if player_id in self.queue and player_id in self.connections:
                    # Calcula tempo de espera e posição
                    position = i + 1
                    wait_time = time.time() - self.queue[player_id].joined_at
                    estimated_wait = self._estimate_wait_time(position)

                    # Atualiza dados do jogador
                    self.queue[player_id].position = position
                    self.queue[player_id].wait_time = int(wait_time)
                    self.queue[player_id].estimated_wait = estimated_wait

                    # Notifica o jogador
                    timestamp = time.time()
                    timestamp_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

                    await self._notify_player(
                        player_id,
                        {
                            "type": "queue_update",
                            "position": position,
                            "wait_time": int(wait_time),
                            "estimated_wait": estimated_wait,
                            "queue_size": len(active_players),
                            "timestamp": timestamp,
                            "server_time": timestamp_str,
                        },
                    )

    def _estimate_wait_time(self, position: int) -> int:
        """
        Estima o tempo de espera com base na posição na fila.

        Args:
            position: Posição na fila

        Returns:
            int: Tempo estimado em segundos
        """
        # Implementação básica para tempos de espera estimados
        base_time = 5  # Tempo base em segundos
        return max(0, (position // 2) * base_time)


# Inicializa a instância singleton
matchmaking_queue = MatchmakingQueue()
