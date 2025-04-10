from fastapi import APIRouter

router = APIRouter(tags=["API"])


@router.get("/")
async def root() -> dict:
    return {"message": "Hello World"}
