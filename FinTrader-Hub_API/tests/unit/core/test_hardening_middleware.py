import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.factory import create_app
from core.config import get_settings
from core.middleware import _rate_limiter
from core.middleware.setup import REQUEST_ID_HEADER


@pytest.fixture(autouse=True)
def clear_rate_limiter() -> None:
    _rate_limiter._requests.clear()


@pytest.fixture
def hardened_client() -> TestClient:
    get_settings.cache_clear()
    with patch.dict(
        os.environ,
        {"SKIP_STARTUP_VALIDATION": "true", "SKIP_AUTO_MIGRATIONS": "true"},
        clear=False,
    ):
        get_settings.cache_clear()
        return TestClient(create_app(), raise_server_exceptions=False)


def test_request_id_header_is_returned(hardened_client: TestClient) -> None:
    response = hardened_client.get("/health")
    assert REQUEST_ID_HEADER in response.headers
    assert len(response.headers[REQUEST_ID_HEADER]) > 0


def test_security_headers_present(hardened_client: TestClient) -> None:
    response = hardened_client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")


def test_internal_error_hides_stack_trace(hardened_client: TestClient) -> None:
    app = hardened_client.app

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("sensitive internal detail")

    response = hardened_client.get("/boom")
    body = response.json()
    assert response.status_code == 500
    assert body["code"] == "INTERNAL_ERROR"
    assert body["message"] == "Internal server error"
    assert "sensitive internal detail" not in str(body)
    assert body.get("request_id")


def test_auth_rate_limit_returns_429() -> None:
    _rate_limiter._requests.clear()
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "SKIP_STARTUP_VALIDATION": "true",
            "SKIP_AUTO_MIGRATIONS": "true",
        },
        clear=False,
    ):
        get_settings.cache_clear()
        client = TestClient(create_app(), raise_server_exceptions=False)
        try:
            for _ in range(10):
                response = client.post(
                    "/auth/login",
                    json={"email": "nobody@example.com", "password": "wrong-password"},
                )
                assert response.status_code in {401, 422}

            blocked = client.post(
                "/auth/login",
                json={"email": "nobody@example.com", "password": "wrong-password"},
            )
            assert blocked.status_code == 429
            assert blocked.json()["code"] == "RATE_LIMIT_EXCEEDED"
        finally:
            get_settings.cache_clear()
