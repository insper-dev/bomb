from fastapi import APIRouter

from server.api.auth import router as auth_router

router = APIRouter(tags=["API"])


router.add_api_route("/auth", auth_router)


@router.get("/")
async def root() -> dict:
    return {"message": "Hello World"}
