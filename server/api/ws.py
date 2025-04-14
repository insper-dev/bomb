import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from prisma.models import User

from core.models.ws import WebSocketCloseCode
from server.api.dependencies import auth_service
from server.services.game import game_service
from server.services.matchmaking import matchmaking_queue

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Game WebSockets"])


@router.websocket("/game/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: str) -> None:
    user = None
    connection_accepted = False

    try:
        # Autentica o usuário primeiro
        user = await auth_service.get_current_user_ws(websocket)
        user_id = user.id

        game = game_service.get_game(game_id)

        if not game:
            logger.warning(f"Jogo {game_id} não encontrado")
            await websocket.close(code=WebSocketCloseCode.ERROR)
            return

        # Verifica se o usuário faz parte do jogo
        if user_id not in game.players:
            logger.warning(f"Usuário {user_id} não faz parte do jogo {game_id}")
            await websocket.close(code=WebSocketCloseCode.ERROR)
            return

        # Aceita a conexão e adiciona ao jogo
        await websocket.accept()
        connection_accepted = True

        success = await game_service.add_player_connection(user_id, game_id, websocket)
        if not success:
            await websocket.close(code=WebSocketCloseCode.ERROR)
            return

        # Atualiza o status do usuário para indicar que está em um jogo
        await User.prisma().update(where={"id": user_id}, data={"status": "IN_GAME"})

        # Processa mensagens enquanto a conexão estiver ativa
        while connection_accepted:
            try:
                message = await websocket.receive_json()

                # Processa ação do jogador
                await game_service.handle_player_action(user_id, message)

            except json.JSONDecodeError:
                logger.warning(f"JSON inválido do usuário {user_id}")
                continue
            except WebSocketDisconnect:
                logger.info(f"WebSocket desconectado para o usuário {user_id}")
                connection_accepted = False
                break
            except Exception as e:
                logger.error(f"Erro no websocket do jogo: {e}")
                if connection_accepted:
                    try:
                        await websocket.send_json(
                            {"type": "error", "message": "Erro ao processar mensagem"}
                        )
                    except Exception:
                        connection_accepted = False
                        break

    except WebSocketDisconnect:
        logger.info(
            f"WebSocket desconectado durante setup para o usuário "
            f"{getattr(user, 'username', 'DESCONHECIDO')} no jogo {game_id}"
        )
    except Exception as e:
        logger.error(f"Erro inesperado no websocket do jogo: {e}")
        if connection_accepted:
            try:
                await websocket.close(code=WebSocketCloseCode.ERROR)
            except Exception:
                pass

    finally:
        # Limpeza
        if user:
            # Atualiza o status do usuário de volta para ONLINE
            try:
                await User.prisma().update(where={"id": user.id}, data={"status": "ONLINE"})
            except Exception as status_err:
                logger.error(f"Erro ao atualizar status do usuário: {status_err}")

            # Remove do jogo
            await game_service.remove_player_connection(user.id)


@router.websocket("/matchmaking")
async def matchmaking_websocket(websocket: WebSocket) -> None:
    user = None
    connection_accepted = False
    in_queue = False

    try:
        # Authenticate user first
        user = await auth_service.get_current_user_ws(websocket)
        user_id = user.id

        await websocket.accept()
        connection_accepted = True
        logger.info(f"Matchmaking WebSocket connection established for user {user_id}")

        try:
            # Update user status to indicate they're online
            await User.prisma().update(where={"id": user_id}, data={"status": "ONLINE"})

            # Wait for the first message (join) before processing
            first_message = await websocket.receive_json()

            if not isinstance(first_message, dict) or first_message.get("action") != "join_queue":
                await websocket.send_json(
                    {"type": "error", "message": "First message must be join_queue"}
                )
                return

            # Add the player to the queue
            added = await matchmaking_queue.add_player(user_id, websocket)
            in_queue = added

            if not added:
                await websocket.send_json(
                    {"type": "error", "message": "Already in queue or other error"}
                )
                return

            # Send confirmation of queue join
            await websocket.send_json({"type": "success", "message": "Joined matchmaking queue"})

            # Update user status to indicate they're in matchmaking
            await User.prisma().update(where={"id": user_id}, data={"status": "MATCHMAKING"})

            # While the player is in the queue, process messages
            while connection_accepted and in_queue:
                try:
                    # Wait for messages from the client
                    message = await websocket.receive_json()

                    if not isinstance(message, dict):
                        logger.warning(f"Invalid message format from user {user_id}")
                        continue

                    action = message.get("action")

                    if not action:
                        logger.warning(f"Message without action from user {user_id}")
                        continue

                    if action == "leave_queue":
                        # Remove the player from the queue
                        if in_queue:
                            await matchmaking_queue.remove_player(user_id)
                            in_queue = False

                        # Update user status back to online
                        await User.prisma().update(where={"id": user_id}, data={"status": "ONLINE"})

                        await websocket.send_json(
                            {"type": "queue_left", "message": "Left matchmaking queue"}
                        )

                        await websocket.close(code=WebSocketCloseCode.LEAVE_QUEUE)
                        connection_accepted = False
                        return

                    elif action == "ping":
                        # Respond to pings to keep the connection alive
                        await websocket.send_json(
                            {"type": "pong", "timestamp": message.get("timestamp")}
                        )

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
                                {"type": "error", "message": "Error processing message"}
                            )
                        except Exception:
                            # If sending fails, connection may be closed
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
        # Already handled above
        pass
    except Exception as e:
        logger.error(f"Unexpected error in matchmaking websocket: {e}")
        if connection_accepted:
            try:
                await websocket.close(code=WebSocketCloseCode.ERROR)
            except Exception:
                pass

    finally:
        # Ensure the player is removed from the queue if the connection is closed
        if user and in_queue:
            await matchmaking_queue.remove_player(user.id)

        # Update user status back to ONLINE if we have a user
        if user:
            try:
                await User.prisma().update(where={"id": user.id}, data={"status": "ONLINE"})
            except Exception as status_err:
                logger.error(f"Error updating user status: {status_err}")
