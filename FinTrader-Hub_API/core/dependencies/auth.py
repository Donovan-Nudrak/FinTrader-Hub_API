from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.enums import TokenType
from core.exceptions import UnauthorizedError
from core.security.auth_utils import TokenPayload, extract_token_payload

bearer_scheme = HTTPBearer(auto_error=False)


def get_token_from_header(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Missing or invalid authorization header")
    return credentials.credentials


def get_access_token_payload(
    token: Annotated[str, Depends(get_token_from_header)],
) -> TokenPayload:
    return extract_token_payload(token, TokenType.ACCESS)


def get_refresh_token_payload(
    token: Annotated[str, Depends(get_token_from_header)],
) -> TokenPayload:
    return extract_token_payload(token, TokenType.REFRESH)
