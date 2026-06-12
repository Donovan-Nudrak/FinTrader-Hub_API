from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from core.config import Settings, get_settings
from core.constants.security import EXPIRATION_CLAIM, ISSUED_AT_CLAIM, SUBJECT_CLAIM, TOKEN_TYPE_CLAIM
from core.enums import TokenType
from core.exceptions import InvalidTokenError


def _build_expiration(expires_delta: timedelta) -> datetime:
    return datetime.now(UTC) + expires_delta


def create_access_token(
    subject: str,
    *,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = settings or get_settings()
    expire = _build_expiration(
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes),
    )

    payload: dict[str, Any] = {
        SUBJECT_CLAIM: subject,
        TOKEN_TYPE_CLAIM: TokenType.ACCESS.value,
        ISSUED_AT_CLAIM: datetime.now(UTC),
        EXPIRATION_CLAIM: expire,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    subject: str,
    *,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = settings or get_settings()
    expire = _build_expiration(
        expires_delta or timedelta(days=settings.refresh_token_expire_days),
    )

    payload: dict[str, Any] = {
        SUBJECT_CLAIM: subject,
        TOKEN_TYPE_CLAIM: TokenType.REFRESH.value,
        ISSUED_AT_CLAIM: datetime.now(UTC),
        EXPIRATION_CLAIM: expire,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(
    token: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()

    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Invalid token") from exc


def verify_token(
    token: str,
    expected_type: TokenType,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    payload = decode_token(token, settings=settings)
    token_type = payload.get(TOKEN_TYPE_CLAIM)

    if token_type != expected_type.value:
        raise InvalidTokenError(f"Expected {expected_type.value} token")

    if SUBJECT_CLAIM not in payload:
        raise InvalidTokenError("Token subject is missing")

    return payload
