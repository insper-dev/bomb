import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prisma import Prisma

from core.abstract import App
from core.config import Settings

logger = logging.getLogger(__name__)
db = Prisma(auto_register=True)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    await db.connect()

    yield

    await db.disconnect()


class ServerApp(App):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

        self.app = FastAPI(
            title="BombInsper Online Server",
            description="Server for BombInsper Online",
            version="1.0.0",
            docs_url="/docs" if settings.server_debug else None,
            redoc_url="/redoc" if settings.server_debug else None,
            lifespan=lifespan,
        )

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        from .api.auth import router as auth_router
        from .api.match import router as match_router
        from .api.ws import router as ws_router

        self.app.include_router(auth_router, prefix="/api/auth")
        self.app.include_router(match_router, prefix="/api/match")
        self.app.include_router(ws_router, prefix="/ws")

    def run(self) -> None:
        uvicorn.run(
            self.app,
            host=self.settings.server_bind,
            port=self.settings.server_port or 8000,
        )
