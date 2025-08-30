import asyncio
import logging
from collections import Counter, deque
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from prisma.models import Match, User
from prisma.partials import Opponent

from core.models.ws import (
    CollectPowerUpEvent,
    GameEvent,
    GameEventType,
    MatchMakingEvent,
    MovimentEvent,
    PlaceBombEvent,
    WebSocketCloseCode,
)
from server.api.dependencies import auth_service
from server.services.game import game_service

waiting_players: dict[str, WebSocket] = {}


async def matchmaking_loop() -> None:
    """Agrupa dois jogadores por vez e notifica ambos."""
    get_match = False
    count = 0
    while True:
        try:
            waiting_player_ids = list(waiting_players)
            if len(waiting_players) >= 2:
                get_match = True
                while count < 5:
                    if len(waiting_players) >= 4:
                        count = 5  # skip wait if we have 4 players
                    count += 1
                    print(count)
                    await asyncio.sleep(1)
                    waiting_player_ids = list(waiting_players)
            if get_match:
                get_match = False
                count = 0
                player_id1 = waiting_player_ids[0]
                player_id2 = waiting_player_ids[1]
                player_id3 = waiting_player_ids[2] if len(waiting_player_ids) > 2 else None
                player_id4 = waiting_player_ids[3] if len(waiting_player_ids) > 3 else None

                players = [
                    p for p in [player_id1, player_id2, player_id3, player_id4] if p is not None
                ]

                match_id = await game_service.create_game(players)

                wss = [waiting_players[pid] for pid in players if pid is not None]

                opponents = []
                for ws in wss:
                    pid = next(k for k, v in waiting_players.items() if v == ws and k in players)
                    opponent = await Opponent.prisma().find_unique(where={"id": pid})
                    opponents.append(opponent)
                try:
                    for opponent_ws, opponent in zip(wss, opponents, strict=False):
                        await opponent_ws.send_json(
                            MatchMakingEvent(match_id=match_id, opponent=opponent).model_dump()
                        )

                    for player_id in players:
                        if player_id and player_id in waiting_players:
                            del waiting_players[player_id]

                    if len(players) > 2:
                        logging.info(f"Match created: {match_id} between {players}")
                    else:
                        logger.info(
                            f"Match created: {match_id} between {player_id1} and {player_id2}"
                        )
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


async def _process_event_queues(
    game_id: str, user_id: str, high_priority_queue: deque, normal_queue: deque
) -> None:
    """Process event queues with prioritization."""
    last_movement_time = 0
    movement_throttle = 0.05  # 20 FPS max for movements

    try:
        while True:
            current_time = asyncio.get_event_loop().time()

            # Process up to 3 high priority events per cycle
            high_priority_processed = 0
            while high_priority_queue and high_priority_processed < 3:
                ev = high_priority_queue.popleft()
                await _process_single_event(game_id, user_id, ev)
                high_priority_processed += 1

            # Process normal priority events with throttling
            if normal_queue and (current_time - last_movement_time) >= movement_throttle:
                # Process only the most recent movement to reduce lag
                latest_movement = None
                movements_skipped = 0

                # Find the latest movement and count skipped ones
                while normal_queue:
                    ev = normal_queue.popleft()
                    if isinstance(ev, MovimentEvent):
                        if latest_movement is not None:
                            movements_skipped += 1
                        latest_movement = ev
                    else:
                        # Non-movement events are processed immediately
                        await _process_single_event(game_id, user_id, ev)

                # Process the latest movement if any
                if latest_movement:
                    await _process_single_event(game_id, user_id, latest_movement)
                    last_movement_time = current_time

                    if movements_skipped > 0:
                        logger.debug(
                            f"Skipped {movements_skipped} redundant movements for user {user_id}"
                        )

            # Small delay to prevent excessive CPU usage
            await asyncio.sleep(0.01)  # 100 FPS processing loop

    except asyncio.CancelledError:
        logger.debug(f"Event processing cancelled for user {user_id} in game {game_id}")
        raise  # Re-raise to ensure proper cancellation
    except Exception as e:
        logger.error(f"Error in event processing for user {user_id}: {e}")
        raise


async def _process_single_event(game_id: str, user_id: str, ev: GameEventType) -> None:
    """Process a single game event."""
    try:
        game = game_service.games.get(game_id)
        if not game:
            return

        if isinstance(ev, MovimentEvent):
            # Movement event
            dx, dy = MovimentEvent.dxdy(ev.direction)
            game.move_player(user_id, dx, dy, ev.direction)
            await game_service.broadcast_state(game_id)

        elif isinstance(ev, PlaceBombEvent):
            # Place bomb at x, y (server assigns timing)
            await game_service.place_bomb(game_id, user_id, ev.x, ev.y)

        elif isinstance(ev, CollectPowerUpEvent):
            # Collect power-up at x, y
            game.collect_powerup(user_id, ev.x, ev.y)

        else:
            logger.warning(f"Unknown event type: {type(ev).__name__}")

    except Exception as e:
        logger.error(f"Error processing event {type(ev).__name__} for user {user_id}: {e}")


@router.websocket("/game/{game_id}")
async def game_ws(websocket: WebSocket, game_id: str) -> None:
    """WebSocket endpoint for real-time game play with event prioritization."""
    logger.info(f"Game WebSocket connection attempt for game {game_id}")
    logger.info(f"Query params: {websocket.query_params}")

    # Accept connection first, then authenticate
    await websocket.accept()
    logger.info(f"WebSocket accepted for game {game_id}")

    # Authenticate via WS
    try:
        user = await auth_service.get_current_user_ws(websocket)
    except Exception:
        await websocket.close(code=WebSocketCloseCode.UNAUTHORIZED)
        return

    game = game_service.games.get(game_id)
    if game is None:
        await websocket.close(code=WebSocketCloseCode.MATCH_FOUND)
        return

    # Register connection
    game_service.add_connection(game_id, websocket)

    # Send initial state
    await websocket.send_json(game.model_dump())

    # Event prioritization queues
    high_priority_queue: deque = deque(maxlen=50)
    normal_queue: deque = deque(maxlen=100)

    # Event processing task
    processing_task = asyncio.create_task(
        _process_event_queues(game_id, user.id, high_priority_queue, normal_queue)
    )

    # Add task to game service tracking (assuming this gets added to the server service)
    try:
        game_service.background_tasks.add(processing_task)
        processing_task.add_done_callback(game_service.background_tasks.discard)
    except AttributeError:
        # Fallback if background_tasks not available
        pass

    try:
        while True:
            raw = await websocket.receive_json()
            ev = GameEvent.validate_python(raw)

            # Classify events by priority
            if isinstance(ev, PlaceBombEvent):
                # Critical events: bombs, explosions - highest priority
                high_priority_queue.append(ev)
                logger.debug(f"High priority event queued: {type(ev).__name__}")
            elif isinstance(ev, MovimentEvent):
                # Movement events - normal priority but frequent
                normal_queue.append(ev)
            else:
                # Unknown events - normal priority
                normal_queue.append(ev)

    except WebSocketDisconnect:
        game_service.remove_connection(game_id, websocket)
        processing_task.cancel()
        try:
            await processing_task
        except asyncio.CancelledError:
            pass  # Expected when cancelling
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id} in game {game_id}: {e}")
        await websocket.close(code=WebSocketCloseCode.ERROR)
        game_service.remove_connection(game_id, websocket)
        processing_task.cancel()
        try:
            await processing_task
        except asyncio.CancelledError:
            pass  # Expected when cancelling


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
