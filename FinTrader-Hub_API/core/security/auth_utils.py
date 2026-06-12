from typing import Any

from pydantic import BaseModel, Field

from core.config import Settings
from core.enums import TokenType
from core.security.jwt import verify_token


class TokenPayload(BaseModel):
    sub: str = Field(description="Subject identifier (e.g. user id)")
    type: TokenType
    exp: int | None = None
    iat: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


def extract_token_payload(
    token: str,
    expected_type: TokenType,
    *,
    settings: Settings | None = None,
) -> TokenPayload:
    raw_payload = verify_token(token, expected_type, settings=settings)

    known_claims = {"sub", "type", "exp", "iat"}
    extra = {key: value for key, value in raw_payload.items() if key not in known_claims}

    return TokenPayload(
        sub=str(raw_payload["sub"]),
        type=TokenType(raw_payload["type"]),
        exp=raw_payload.get("exp"),
        iat=raw_payload.get("iat"),
        extra=extra,
    )


def build_auth_subject(user_id: int | str) -> str:
    return str(user_id)
