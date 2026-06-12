from datetime import timedelta

import pytest

from core.enums import TokenType
from core.exceptions import InvalidTokenError
from core.security import (
    create_access_token,
    create_refresh_token,
    extract_token_payload,
    verify_token,
)


def test_create_and_verify_access_token(test_settings) -> None:
    token = create_access_token("42", settings=test_settings)
    payload = verify_token(token, TokenType.ACCESS, settings=test_settings)

    assert payload["sub"] == "42"
    assert payload["type"] == TokenType.ACCESS.value


def test_create_and_verify_refresh_token(test_settings) -> None:
    token = create_refresh_token("99", settings=test_settings)
    payload = verify_token(token, TokenType.REFRESH, settings=test_settings)

    assert payload["sub"] == "99"
    assert payload["type"] == TokenType.REFRESH.value


def test_access_token_rejects_refresh_type(test_settings) -> None:
    token = create_refresh_token("1", settings=test_settings)

    with pytest.raises(InvalidTokenError):
        verify_token(token, TokenType.ACCESS, settings=test_settings)


def test_extract_token_payload(test_settings) -> None:
    token = create_access_token(
        "7",
        settings=test_settings,
        extra_claims={"role": "user"},
    )
    payload = extract_token_payload(token, TokenType.ACCESS, settings=test_settings)

    assert payload.sub == "7"
    assert payload.type == TokenType.ACCESS
    assert payload.extra["role"] == "user"


def test_expired_token_raises_invalid_token_error(test_settings) -> None:
    token = create_access_token(
        "1",
        settings=test_settings,
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(InvalidTokenError):
        verify_token(token, TokenType.ACCESS, settings=test_settings)
