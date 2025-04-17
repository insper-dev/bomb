import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prisma import Prisma

from core.abstract import App
from core.config import Settings
from server.services.matchmaking import matchmaking_queue

logger = logging.getLogger(__name__)
db = Prisma(auto_register=True)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    # Store tasks to be cleaned up later
    background_tasks = []

    try:
        await db.connect()
        # Start the matchmaking queue and store its tasks
        # Initialize empty list for background tasks
        background_tasks.extend(await matchmaking_queue.start() or [])

        yield
    finally:
        logger.info("Shutting down server...")
        try:
            async with asyncio.timeout(5.0):
                # Cancel all running tasks first
                for task in background_tasks:
                    if not task.done():
                        task.cancel()
                        try:
                            await asyncio.wait_for(task, timeout=1.0)
                        except (TimeoutError, asyncio.CancelledError):
                            pass

                # Force cleanup games first (they might hold locks)
                # await game_service.force_cleanup()

                # Then force-stop the matchmaking queue
                await matchmaking_queue.stop(force=True)

                # Finally disconnect from the database with timeout
                try:
                    await asyncio.wait_for(db.disconnect(), timeout=2.0)
                except (TimeoutError, Exception) as e:
                    logger.error(f"Error disconnecting from database: {e}")
                    # Force disconnect if timeout
                    db.client = None  # type: ignore

        except (TimeoutError, asyncio.CancelledError):
            logger.warning("Timeout during shutdown, forcing cleanup")
            # Force cleanup everything
            # game_service.games.clear()
            # game_service.player_game_map.clear()
            matchmaking_queue.queue.clear()
            matchmaking_queue.connections.clear()
            matchmaking_queue.matched_players.clear()
            db.client = None  # type: ignore

        logger.info("Server shutdown complete")


class ServerApp(App):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

        self.app = FastAPI(
            title="Lara Bomb Online Server",
            description="Server for Lara Bomb Online",
            version="0.0.3",
            docs_url="/docs" if self.settings.server_debug else None,
            redoc_url="/redoc" if self.settings.server_debug else None,
            lifespan=lifespan,
        )

        self.app.add_middleware(
            CORSMiddleware,
            allow_credentials=True,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        from .api.auth import router as auth_router
        from .api.ws import router as ws_router

        self.app.include_router(auth_router, prefix="/api/auth")
        self.app.include_router(ws_router, prefix="/ws")

    def run(self) -> None:
        uvicorn.run(
            self.app, host=self.settings.server_bind, port=self.settings.server_port or 8000
        )
