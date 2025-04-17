import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from prisma.models import User

from core.models.matchmaking import QueuedPlayer
from core.models.ws import WebSocketCloseCode, WSMessage
from server.api.dependencies import auth_service
from server.services.game import game_service
from server.services.matchmaking import matchmaking_queue

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Game WebSockets"])


@router.websocket("/game/{game_id}")
async def game_ws(
    websocket: WebSocket,
    game_id: str,
) -> None:
    """WebSocket endpoint para o jogo"""
    # autentica usuário
    user = await auth_service.get_current_user_ws(websocket)

    # aceita conexão
    await websocket.accept()
    if not user:
        await websocket.close(code=1008)
        return
    player_id = user.id

    # busca jogo
    try:
        game = game_service.get_game(game_id)
    except KeyError:
        await websocket.close(code=1003)
        return

    # adiciona conexão
    game_service.add_connection(game_id, websocket)

    try:
        # envia estado inicial para o novo jogador
        await websocket.send_json(game.model_dump())

        while True:
            raw = await websocket.receive_json()
            msg = WSMessage(**raw)
            # tradução de direção em (dx, dy)
            deltas = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
            dx, dy = deltas[msg.direction]
            game.move_player(player_id, dx, dy)
            # propaga estado atualizado para todos os jogadores
            await game_service.broadcast_state(game_id)
    except WebSocketDisconnect:
        # remove conexão quando jogador desconecta
        game_service.remove_connection(game_id, websocket)
        return


@router.websocket("/matchmaking")
async def matchmaking_websocket(websocket: WebSocket) -> None:
    user = None
    connection_accepted = False
    in_queue = False
    last_activity = time.time()

    try:
        # Autenticação do usuário
        user = await auth_service.get_current_user_ws(websocket)
        user_id = user.id

        await websocket.accept()
        connection_accepted = True
        logger.info(f"Matchmaking WebSocket connection established for user {user_id}")

        try:
            # Atualiza o status do usuário para online
            await User.prisma().update(where={"id": user_id}, data={"status": "ONLINE"})

            # Aguarda a primeira mensagem (join) antes do processamento
            first_message = await websocket.receive_json()

            if not isinstance(first_message, dict) or first_message.get("action") != "join_queue":
                await websocket.send_json(
                    {"type": "error", "message": "First message must be join_queue"}
                )
                return

            # Adiciona o jogador à fila
            added = await matchmaking_queue.add_player(user_id, websocket)
            in_queue = added
            last_activity = time.time()

            if not added:
                await websocket.send_json(
                    {"type": "error", "message": "Failed to join queue, try again later"}
                )
                return

            # Envia confirmação de entrada na fila
            await websocket.send_json(
                {"type": "success", "message": "Joined matchmaking queue", "timestamp": time.time()}
            )

            # Atualiza o status do usuário para indicar que está em matchmaking
            await User.prisma().update(where={"id": user_id}, data={"status": "MATCHMAKING"})

            # Enquanto o jogador estiver na fila, processa mensagens
            while connection_accepted and in_queue:
                try:
                    # Define um timeout para receber mensagens
                    message = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                    last_activity = time.time()

                    if not isinstance(message, dict):
                        logger.warning(f"Invalid message format from user {user_id}")
                        continue

                    action = message.get("action")

                    if not action:
                        logger.warning(f"Message without action from user {user_id}")
                        continue

                    if action == "leave_queue":
                        # Remove o jogador da fila
                        if in_queue:
                            await matchmaking_queue.remove_player(user_id)
                            in_queue = False

                        # Atualiza o status do usuário de volta para online
                        await User.prisma().update(where={"id": user_id}, data={"status": "ONLINE"})

                        await websocket.send_json(
                            {
                                "type": "queue_left",
                                "message": "Left matchmaking queue",
                                "timestamp": time.time(),
                            }
                        )

                        await websocket.close(code=WebSocketCloseCode.LEAVE_QUEUE)
                        connection_accepted = False
                        return

                    elif action == "ping":
                        # Responde a pings para manter a conexão viva
                        await websocket.send_json(
                            {"type": "pong", "timestamp": message.get("timestamp", time.time())}
                        )

                    elif action == "status":
                        # Consulta informações sobre a fila
                        await websocket.send_json(
                            {
                                "type": "queue_info",
                                "position": matchmaking_queue.queue.get(
                                    user_id, QueuedPlayer(user_id=user_id, joined_at=0)
                                ).position,
                                "wait_time": int(
                                    time.time()
                                    - matchmaking_queue.queue.get(
                                        user_id,
                                        QueuedPlayer(user_id=user_id, joined_at=time.time()),
                                    ).joined_at
                                ),
                                "queue_size": len(
                                    [
                                        p
                                        for p in matchmaking_queue.queue
                                        if p not in matchmaking_queue.matched_players
                                    ]
                                ),
                                "timestamp": time.time(),
                            }
                        )

                except TimeoutError:
                    # Nenhuma mensagem recebida no período de timeout, verifica se ainda ta connec
                    # Se o último ping foi há muito tempo, encerre a conexão
                    if time.time() - last_activity > 60:  # 1 minuto sem atividade
                        logger.info(
                            f"No activity for user {user_id} for 60 seconds, closing connection"
                        )
                        connection_accepted = False
                        break

                    try:
                        # Envia um ping para verificar a conexão
                        await websocket.send_json({"type": "ping", "timestamp": time.time()})
                    except Exception:
                        logger.info(f"Connection lost for user {user_id}")
                        connection_accepted = False
                        break

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from user {user_id}")
                    continue
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected for user {user_id}")
                    connection_accepted = False
                    break
                except Exception as e:
                    logger.error(f"Error processing matchmaking message: {e}")
                    if connection_accepted:
                        try:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "message": "Error processing message",
                                    "timestamp": time.time(),
                                }
                            )
                        except Exception:
                            # Se o envio falhar, a conexão pode estar fechada
                            connection_accepted = False
                            break
                    else:
                        break

        except json.JSONDecodeError:
            logger.warning(f"Invalid initial JSON from user {user_id}")
            if connection_accepted:
                await websocket.send_json({"type": "error", "message": "Invalid initial message"})
            return
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected during setup for user {user_id}")
            connection_accepted = False

    except WebSocketDisconnect:
        # Já tratado acima
        pass
    except Exception as e:
        logger.error(f"Unexpected error in matchmaking websocket: {e}")
        if connection_accepted:
            try:
                await websocket.close(code=WebSocketCloseCode.ERROR)
            except Exception:
                pass

    finally:
        if user:
            try:
                async with asyncio.timeout(2.0):
                    # Set a timeout for database operations during cleanup
                    try:
                        await asyncio.wait_for(
                            User.prisma().update(where={"id": user.id}, data={"status": "ONLINE"}),
                            timeout=1.0,
                        )
                    except Exception as status_err:
                        logger.error(f"Error updating user status: {status_err}")

                    # For matchmaking connections
                    try:
                        if user.id in matchmaking_queue.connections:
                            # Direct cleanup without locks
                            for collection in [
                                matchmaking_queue.connections,
                                matchmaking_queue.queue,
                                matchmaking_queue.connection_status,
                            ]:
                                collection.pop(user.id, None)
                            matchmaking_queue.matched_players.discard(user.id)

                            # Force close the connection if still open
                            try:
                                await websocket.close(code=WebSocketCloseCode.ERROR)
                            except Exception:
                                pass
                    except Exception as e:
                        logger.error(f"Error removing player from matchmaking: {e}")

            except (TimeoutError, asyncio.CancelledError):
                logger.warning(f"Timeout during matchmaking cleanup for user {user.id}")
                # Force cleanup even during timeout
                for collection in [
                    matchmaking_queue.connections,
                    matchmaking_queue.queue,
                    matchmaking_queue.connection_status,
                ]:
                    collection.pop(user.id, None)
                matchmaking_queue.matched_players.discard(user.id)
