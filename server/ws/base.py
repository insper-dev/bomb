from fastapi import APIRouter

router = APIRouter(tags=["WebSocket"])


@router.get("/")
async def root() -> dict:
    return {"message": "Hello World"}
