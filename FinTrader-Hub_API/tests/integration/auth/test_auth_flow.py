import uuid

import pytest
from fastapi.testclient import TestClient

from app.factory import create_app
from core.config import get_settings
from core.enums import TokenType
from core.security import verify_token
from modules.auth.services.token_utils import hash_refresh_token


@pytest.fixture
def app_client() -> TestClient:
    get_settings.cache_clear()
    return TestClient(create_app())


def _unique_credentials() -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    return {
        "email": f"user_{suffix}@example.com",
        "username": f"user_{suffix}",
        "password": "SecurePass123!",
    }


def _register_user(client: TestClient, credentials: dict[str, str] | None = None) -> dict:
    payload = credentials or _unique_credentials()
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    return payload


def _login_user(client: TestClient, email: str, password: str) -> dict:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_register_user_success(app_client: TestClient) -> None:
    credentials = _unique_credentials()
    response = app_client.post("/auth/register", json=credentials)

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == credentials["email"]
    assert body["data"]["username"] == credentials["username"]
    assert body["data"]["role"]["name"] == "user"
    assert body["data"]["is_active"] is True


def test_register_user_duplicate_email(app_client: TestClient) -> None:
    credentials = _unique_credentials()
    app_client.post("/auth/register", json=credentials)
    duplicate = {
        "email": credentials["email"],
        "username": f"other_{uuid.uuid4().hex[:8]}",
        "password": credentials["password"],
    }

    response = app_client.post("/auth/register", json=duplicate)

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_EXISTS"


def test_register_user_duplicate_username(app_client: TestClient) -> None:
    credentials = _unique_credentials()
    app_client.post("/auth/register", json=credentials)
    duplicate = {
        "email": f"other_{uuid.uuid4().hex[:8]}@example.com",
        "username": credentials["username"],
        "password": credentials["password"],
    }

    response = app_client.post("/auth/register", json=duplicate)

    assert response.status_code == 409
    assert response.json()["code"] == "USERNAME_EXISTS"


def test_login_user_success(app_client: TestClient) -> None:
    credentials = _register_user(app_client)
    tokens = _login_user(app_client, credentials["email"], credentials["password"])

    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


def test_login_user_invalid_password(app_client: TestClient) -> None:
    credentials = _register_user(app_client)
    response = app_client.post(
        "/auth/login",
        json={"email": credentials["email"], "password": "WrongPassword!"},
    )

    assert response.status_code == 401


def test_refresh_access_token_success(app_client: TestClient) -> None:
    credentials = _register_user(app_client)
    login_data = _login_user(app_client, credentials["email"], credentials["password"])

    response = app_client.post(
        "/auth/refresh",
        json={"refresh_token": login_data["refresh_token"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]

    access_payload = verify_token(body["data"]["access_token"], TokenType.ACCESS)
    refresh_payload = verify_token(login_data["refresh_token"], TokenType.REFRESH)
    assert access_payload["sub"] == refresh_payload["sub"]


def test_logout_user_invalidates_refresh_token(app_client: TestClient) -> None:
    credentials = _register_user(app_client)
    login_data = _login_user(app_client, credentials["email"], credentials["password"])

    logout_response = app_client.post(
        "/auth/logout",
        json={"refresh_token": login_data["refresh_token"]},
    )
    assert logout_response.status_code == 200

    refresh_response = app_client.post(
        "/auth/refresh",
        json={"refresh_token": login_data["refresh_token"]},
    )
    assert refresh_response.status_code == 401
    assert "revoked" in refresh_response.json()["message"].lower()


def test_get_user_profile_protected_route(app_client: TestClient) -> None:
    credentials = _register_user(app_client)
    login_data = _login_user(app_client, credentials["email"], credentials["password"])

    unauthorized_response = app_client.get("/auth/profile")
    assert unauthorized_response.status_code == 401

    profile_response = app_client.get(
        "/auth/profile",
        headers={"Authorization": f"Bearer {login_data['access_token']}"},
    )
    assert profile_response.status_code == 200
    profile = profile_response.json()["data"]
    assert profile["email"] == credentials["email"]
    assert profile["username"] == credentials["username"]


def test_jwt_and_password_integration(app_client: TestClient) -> None:
    credentials = _register_user(app_client)
    login_data = _login_user(app_client, credentials["email"], credentials["password"])

    access_payload = verify_token(login_data["access_token"], TokenType.ACCESS)
    refresh_payload = verify_token(login_data["refresh_token"], TokenType.REFRESH)

    assert access_payload["type"] == TokenType.ACCESS.value
    assert refresh_payload["type"] == TokenType.REFRESH.value
    assert access_payload["role"] == "user"
    assert hash_refresh_token(login_data["refresh_token"])
