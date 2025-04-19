import asyncio
import logging
from collections import Counter
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from prisma.models import Match, User
from prisma.partials import Opponent

from core.models.ws import GameEvent, MatchMakingEvent
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
                opponent1 = await Opponent.prisma().find_unique(where={"id": player_id1})
                opponent2 = await Opponent.prisma().find_unique(where={"id": player_id2})

                try:
                    await ws1.send_json(
                        MatchMakingEvent(match_id=match_id, opponent=opponent2).model_dump()
                    )
                    await ws2.send_json(
                        MatchMakingEvent(match_id=match_id, opponent=opponent1).model_dump()
                    )

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
async def game_ws(websocket: WebSocket, game_id: str) -> None:
    """WebSocket endpoint para o jogo."""
    user = await auth_service.get_current_user_ws(websocket)

    # aceita conexão
    await websocket.accept()
    if not user:
        await websocket.close(code=1008)
        return

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
            ev = GameEvent.validate_python(raw)
            if ev.event == "move":
                # move player
                dx, dy = {
                    "up": (0, -1),
                    "down": (0, 1),
                    "left": (-1, 0),
                    "right": (1, 0),
                }[ev.direction]
                game = game_service.get_game(game_id)
                game.move_player(user.id, dx, dy)
                await game_service.broadcast_state(game_id)
            elif ev.event == "place_bomb":
                # coloca bomba e agenda explosão
                await game_service.place_bomb(game_id, user.id, ev.x, ev.y, ev.radius)
    except WebSocketDisconnect:
        game_service.remove_connection(game_id, websocket)
        return


@router.websocket("/leaderboard")
async def leaderboard_ws(websocket: WebSocket) -> None:
    """
    WebSocket público que envia a cada 5s um JSON:
      { "leaderboard": [ {user_id, username, wins}, … ] }
    """
    await websocket.accept()
    try:
        while True:
            matches = await Match.prisma().find_many(where={"NOT": [{"winnerUserId": None}]})
            counts: Counter[str] = Counter()
            for m in matches:
                uid = m.winnerUserId
                if uid:
                    counts[uid] += 1

            # top10
            top10 = counts.most_common(10)
            board: list[dict] = []
            for user_id, wins in top10:
                u = await User.prisma().find_unique(where={"id": user_id})
                board.append(
                    {
                        "user_id": user_id,
                        "username": u.username if u else user_id,
                        "wins": wins,
                    }
                )

            await websocket.send_json({"leaderboard": board})
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info("Leaderboard client disconnected")
    except Exception as e:
        logger.error(f"Erro no leaderboard_ws: {e!s}")
