from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from prisma.models import User

from core.config import get_settings

settings = get_settings()

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


class AuthService:
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verifies if the plain password matches the stored hash using Argon2.
        """
        try:
            ph.verify(hashed_password, plain_password)
            return True
        except VerifyMismatchError:
            return False

    async def authenticate_user(self, username: str, password: str) -> User | None:
        """
        Authenticates a user by verifying username and password.
        """
        user = await User.prisma().find_unique(where={"username": username})
        if not user or not self.verify_password(password, user.password):
            return None
        return user

    def create_access_token(self, data: dict) -> str:
        """
        Generates a JWT access token with the provided data and expiration time.
        """
        to_encode = data.copy()
        expire = (
            datetime.now(UTC) + timedelta(minutes=settings.server_access_token_expire_minutes)
        ).timestamp()
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.server_secret_key,
            algorithm=settings.server_algorithm,
        )
        return encoded_jwt

    def decode_access_token(self, token: str) -> dict | None:
        """
        Decodes the JWT access token and returns the contained data.
        """
        try:
            decoded_token = jwt.decode(
                token,
                settings.server_secret_key,
                algorithms=[settings.server_algorithm],
            )
            return (
                decoded_token
                if decoded_token.get("exp", 0) >= datetime.now(UTC).timestamp()
                else None
            )
        except JWTError:
            return None

    def hash_password(self, password: str) -> str:
        """
        Creates an Argon2 hash of the given password.
        """
        return ph.hash(password)

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> User:
        """
        Gets the current user from the access token.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        payload = self.decode_access_token(token)
        if payload is None:
            raise credentials_exception

        username: str = payload.get("sub")  # type: ignore
        if username is None:
            raise credentials_exception

        user = await User.prisma().find_unique(where={"username": username})
        if user is None:
            raise credentials_exception

        return user

    async def get_current_user_ws(self, websocket: WebSocket) -> User:
        """Authenticate user via WebSocket token parameter

        Args:
            websocket: The WebSocket connection

        Returns:
            User: The authenticated user

        Raises:
            Exception: If authentication fails
        """
        token = websocket.query_params.get("token")
        if not token:
            raise Exception("No token provided")

        try:
            return await self.get_current_user(token)
        except Exception as e:
            raise Exception("Authentication failed") from e
