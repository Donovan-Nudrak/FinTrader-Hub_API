from datetime import UTC, datetime

from sqlalchemy.orm import Session

from core.enums import TokenType
from core.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from core.security import (
    build_auth_subject,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from modules.auth.models.refresh_token import RefreshToken
from modules.auth.models.user import User
from modules.auth.repositories import RefreshTokenRepository, RoleRepository, UserRepository
from modules.auth.schemas import (
    AccessTokenResponse,
    RegisterUserRequest,
    TokenResponse,
    UserResponse,
)
from modules.auth.services.token_utils import hash_refresh_token

DEFAULT_ROLE_NAME = "user"


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repository = UserRepository(db)
        self.role_repository = RoleRepository(db)
        self.refresh_token_repository = RefreshTokenRepository(db)

    def register_user(self, request: RegisterUserRequest) -> UserResponse:
        if self.user_repository.email_exists(request.email):
            raise ConflictError("Email is already registered", code="EMAIL_EXISTS")

        if self.user_repository.username_exists(request.username):
            raise ConflictError("Username is already taken", code="USERNAME_EXISTS")

        role = self.role_repository.get_by_name(DEFAULT_ROLE_NAME)
        if role is None:
            raise NotFoundError("Default user role not found")

        user = User(
            email=request.email.lower(),
            username=request.username.lower(),
            hashed_password=hash_password(request.password),
            role_id=role.id,
            is_active=True,
        )
        created_user = self.user_repository.create(user)
        self.db.commit()
        persisted_user = self.user_repository.get_by_id(created_user.id)
        if persisted_user is None:
            raise NotFoundError("User not found after registration")
        return UserResponse.model_validate(persisted_user)

    def login_user(self, email: str, password: str) -> TokenResponse:
        if not password:
            raise ValidationError("Password is required")

        user = self.user_repository.get_by_email(email.lower())
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedError("User account is inactive")

        return self._issue_tokens(user)

    def refresh_access_token(self, refresh_token: str) -> AccessTokenResponse:
        payload = verify_token(refresh_token, TokenType.REFRESH)
        token_record = self.refresh_token_repository.get_by_token_hash(
            hash_refresh_token(refresh_token),
        )

        if token_record is None:
            raise UnauthorizedError("Refresh token not found")

        if token_record.is_revoked:
            raise UnauthorizedError("Refresh token has been revoked")

        if token_record.expires_at <= datetime.now(UTC):
            raise UnauthorizedError("Refresh token has expired")

        user = self.user_repository.get_by_id(int(payload["sub"]))
        if user is None or not user.is_active:
            raise UnauthorizedError("User account is inactive or not found")

        access_token = create_access_token(
            build_auth_subject(user.id),
            extra_claims={"role": user.role.name},
        )
        return AccessTokenResponse(access_token=access_token)

    def logout_user(self, refresh_token: str) -> None:
        verify_token(refresh_token, TokenType.REFRESH)
        token_record = self.refresh_token_repository.get_by_token_hash(
            hash_refresh_token(refresh_token),
        )

        if token_record is None:
            raise UnauthorizedError("Refresh token not found")

        if token_record.is_revoked:
            raise UnauthorizedError("Refresh token has already been revoked")

        self.refresh_token_repository.revoke(token_record)
        self.db.commit()

    def get_user_profile(self, user_id: int) -> UserResponse:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")

        if not user.is_active:
            raise UnauthorizedError("User account is inactive")

        return UserResponse.model_validate(user)

    def _issue_tokens(self, user: User) -> TokenResponse:
        subject = build_auth_subject(user.id)
        role = self.role_repository.get_by_id(user.role_id)
        role_name = role.name if role else DEFAULT_ROLE_NAME

        access_token = create_access_token(subject, extra_claims={"role": role_name})
        refresh_token = create_refresh_token(subject)

        payload = verify_token(refresh_token, TokenType.REFRESH)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)

        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at,
            is_revoked=False,
        )
        self.refresh_token_repository.create(refresh_token_record)
        self.db.commit()

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
