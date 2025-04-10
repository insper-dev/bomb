from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from prisma.models import User

from core.models.auth import Token, UserLogin, UserRegister
from server.api.dependencies import CurrentUserDep, auth_service

router = APIRouter(tags=["Authentication"])


@router.post("/register", response_model=Token)
async def register(user_data: UserRegister) -> dict:
    existing_user = await User.prisma().find_unique(where={"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    existing_username = await User.prisma().find_unique(where={"username": user_data.username})
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    hashed_password = auth_service.hash_password(user_data.password)
    user = await User.prisma().create(
        {
            "username": user_data.username,
            "email": user_data.email,
            "password": hashed_password,
            "status": "OFFLINE",
        }
    )

    access_token = auth_service.create_access_token({"sub": user.email})

    return {"access_token": access_token}


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin) -> dict:
    user = await auth_service.authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await User.prisma().update(
        where={"id": user.id}, data={"lastLoginAt": datetime.now(UTC), "status": "ONLINE"}
    )

    access_token = auth_service.create_access_token({"sub": user.email})

    return {"access_token": access_token}


@router.post("/logout")
async def logout(user: CurrentUserDep) -> dict:
    await User.prisma().update(where={"id": user.id}, data={"status": "OFFLINE"})
    return {"message": "Successfully logged out"}
