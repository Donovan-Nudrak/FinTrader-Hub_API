from core.dependencies.auth import get_token_from_header
from core.enums import TokenType
from core.exceptions import UnauthorizedError
from core.security import build_auth_subject, create_access_token


def test_build_auth_subject() -> None:
    assert build_auth_subject(10) == "10"


def test_get_token_from_header_missing_credentials() -> None:
    try:
        get_token_from_header(None)
        raised = False
    except UnauthorizedError:
        raised = True

    assert raised is True


def test_get_access_token_payload_dependency(test_settings, monkeypatch) -> None:
    from fastapi.security import HTTPAuthorizationCredentials

    from core.config import get_settings
    from core.security.auth_utils import extract_token_payload

    get_settings.cache_clear()
    monkeypatch.setenv("JWT_SECRET_KEY", test_settings.jwt_secret_key)
    get_settings.cache_clear()

    token = create_access_token("55", settings=get_settings())
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    payload = extract_token_payload(
        get_token_from_header(credentials),
        TokenType.ACCESS,
        settings=get_settings(),
    )

    assert payload.sub == "55"
    assert payload.type == TokenType.ACCESS
