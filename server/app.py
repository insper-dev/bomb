from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.abstract import App
from core.config import Settings

from .api import router as api_router
from .ws import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    # TODO: initialize prisma database.
    yield


class ServerApp(App):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

        self.app = FastAPI(
            title="Lara Bomb Online Server",
            description="Server for Lara Bomb Online",
            version="0.0.1",
            docs_url="/docs" if self.settings.debug else None,
            redoc_url="/redoc" if self.settings.debug else None,
            lifespan=lifespan,
        )

        self.app.add_middleware(
            CORSMiddleware,
            allow_credentials=True,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.app.include_router(api_router, prefix="/api")
        self.app.include_router(ws_router, prefix="/ws")

    def run(self) -> None:
        uvicorn.run(self.app, host=self.settings.host, port=self.settings.port or 8000)
