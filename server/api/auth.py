from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from prisma.models import User
from prisma.partials import CurrentUser

from core.models.auth import Token, UserSignup
from server.api.dependencies import CurrentUserDep, auth_service

router = APIRouter(tags=["Authentication"])


@router.post("/signup", response_model=Token)
async def signup(user_data: UserSignup):  # noqa: ANN201
    existing_username = await User.prisma().find_unique(where={"username": user_data.username})
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    hashed_password = auth_service.hash_password(user_data.password)
    user = await User.prisma().create(
        {
            "username": user_data.username,
            "password": hashed_password,
            "status": "OFFLINE",
        }
    )

    access_token = auth_service.create_access_token({"sub": user.username})

    return {"access_token": access_token}


@router.post("/login", response_model=Token)
async def login(credentials: Annotated[OAuth2PasswordRequestForm, Depends()]):  # noqa: ANN201
    user = await auth_service.authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await User.prisma().update(
        where={"id": user.id}, data={"lastLoginAt": datetime.now(UTC), "status": "ONLINE"}
    )

    access_token = auth_service.create_access_token({"sub": user.username})

    return {"access_token": access_token}


@router.post("/logout")
async def logout(user: CurrentUserDep) -> dict:
    await User.prisma().update(where={"id": user.id}, data={"status": "OFFLINE"})
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=CurrentUser)
async def me(user: CurrentUserDep) -> User:
    return user
