import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.models.ws import GameEvent
from server.api.dependencies import auth_service
from server.services.game import game_service

waiting_players: dict[str, WebSocket] = {}


async def matchmaking_loop() -> None:
    """Agrupa dois jogadores por vez e notifica ambos."""
    while True:
        try:
            waiting_player_ids = list(waiting_players)
            if len(waiting_players) >= 2:
                player_id1 = waiting_player_ids[0]
                player_id2 = waiting_player_ids[1]

                match_id = await game_service.create_game([player_id1, player_id2])

                ws1 = waiting_players[player_id1]
                ws2 = waiting_players[player_id2]

                payload = {
                    "type": "match_found",
                    "match_id": match_id,
                    "opponent_id": player_id2,
                }

                try:
                    await ws1.send_json(payload)

                    payload["opponent_id"] = player_id1
                    await ws2.send_json(payload)

                    del waiting_players[player_id1]
                    del waiting_players[player_id2]

                    logger.info(f"Match created: {match_id} between {player_id1} and {player_id2}")
                except Exception as e:
                    logger.error(f"Error sending match notification: {e!s}")
                    continue

        except Exception as e:
            logger.error(f"Error in matchmaking loop: {e!s}")

        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: APIRouter) -> AsyncGenerator:
    task = asyncio.create_task(matchmaking_loop())
    yield
    task.cancel()


logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSockets"], lifespan=lifespan)


@router.websocket("/matchmaking")
async def matchmaking_websocket(websocket: WebSocket) -> None:
    user = await auth_service.get_current_user_ws(websocket)
    if not user:
        await websocket.close(code=1008)
        return

    if user.id in waiting_players:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    waiting_players[user.id] = websocket

    try:
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        logger.info(f"Player {user.id} disconnected from matchmaking")
    except Exception as e:
        logger.error(f"Error in matchmaking websocket: {e!s}")
    finally:
        if user.id in waiting_players:
            del waiting_players[user.id]


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
            msg = GameEvent.validate_python(raw)
            if msg.event == "move":
                deltas = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
                dx, dy = deltas[msg.direction]
                game.move_player(player_id, dx, dy)

            await game_service.broadcast_state(game_id)
    except WebSocketDisconnect:
        game_service.remove_connection(game_id, websocket)
        return
