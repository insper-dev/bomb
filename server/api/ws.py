import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.models.ws import GameEvent
from server.api.dependencies import auth_service
from server.services.game import game_service
from server.services.matchmaking import matchmaking_service

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
            msg = GameEvent.validate_python(raw)
            if msg.event == "move":
                deltas = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
                dx, dy = deltas[msg.direction]
                game.move_player(player_id, dx, dy)

            await game_service.broadcast_state(game_id)
    except WebSocketDisconnect:
        game_service.remove_connection(game_id, websocket)
        return


@router.websocket("/matchmaking")
async def matchmaking_websocket(websocket: WebSocket) -> None:
    user = await auth_service.get_current_user_ws(websocket)
    if not user:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    await matchmaking_service.join(user.id, websocket)
