from typing import Annotated

from fastapi import Depends
from prisma.models import User

from server.api.services.auth import AuthService

auth_service = AuthService()


CurrentUserDep = Annotated[User, Depends(auth_service.get_current_user)]
