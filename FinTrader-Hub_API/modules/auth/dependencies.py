from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.dependencies import get_access_token_payload, get_db
from core.exceptions import UnauthorizedError
from core.security.auth_utils import TokenPayload
from modules.auth.models.user import User
from modules.auth.repositories.user_repository import UserRepository
from modules.auth.services import AuthService


def get_auth_service(db: Annotated[Session, Depends(get_db)]) -> AuthService:
    return AuthService(db)


def get_current_user(
    token_payload: Annotated[TokenPayload, Depends(get_access_token_payload)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    user_repository = UserRepository(db)
    user = user_repository.get_by_id(int(token_payload.sub))

    if user is None:
        raise UnauthorizedError("User not found")

    if not user.is_active:
        raise UnauthorizedError("User account is inactive")

    return user
