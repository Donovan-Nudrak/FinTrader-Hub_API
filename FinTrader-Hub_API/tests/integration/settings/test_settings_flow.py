import os
import uuid

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.factory import create_app
from core.config import get_settings


@pytest.fixture(autouse=True)
def configure_encryption_key() -> None:
    os.environ["API_KEY_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app_client() -> TestClient:
    get_settings.cache_clear()
    return TestClient(create_app())


def _unique_credentials() -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    return {
        "email": f"settings_user_{suffix}@example.com",
        "username": f"settings_user_{suffix}",
        "password": "SecurePass123!",
    }


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _register_login(client: TestClient) -> str:
    credentials = _unique_credentials()
    client.post("/auth/register", json=credentials)
    login = client.post(
        "/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    )
    return login.json()["data"]["access_token"]


def test_get_settings_creates_defaults(app_client: TestClient) -> None:
    token = _register_login(app_client)

    response = app_client.get("/settings", headers=_auth_headers(token))
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["base_currency"] == "USD"
    assert data["timezone"] == "UTC"
    assert data["dashboard_refresh_interval"] == 300
    assert data["alert_email"] is None


def test_put_settings_updates_base_currency(app_client: TestClient) -> None:
    token = _register_login(app_client)
    headers = _auth_headers(token)

    app_client.get("/settings", headers=headers)
    update = app_client.put("/settings", json={"base_currency": "eur"}, headers=headers)
    assert update.status_code == 200
    assert update.json()["data"]["base_currency"] == "EUR"

    get_response = app_client.get("/settings", headers=headers)
    assert get_response.json()["data"]["base_currency"] == "EUR"
    assert get_response.json()["data"]["timezone"] == "UTC"


def test_create_api_key_returns_masked_value(app_client: TestClient) -> None:
    token = _register_login(app_client)
    headers = _auth_headers(token)

    response = app_client.post(
        "/settings/api-keys",
        json={
            "name": "Mi Finnhub Key",
            "provider": "FINNHUB",
            "key_value": "finnhub-secret-key-12345",
            "is_active": True,
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]

    plain_key = "finnhub-secret-key-12345"
    masked = data["masked_key_value"]
    assert masked.startswith("finn")
    assert len(masked) == len(plain_key)
    assert masked[4:] == "*" * (len(plain_key) - 4)
    assert "finnhub-secret-key-12345" not in str(response.json())


def test_list_api_keys_never_returns_plaintext(app_client: TestClient) -> None:
    token = _register_login(app_client)
    headers = _auth_headers(token)
    secret = "coingecko-secret-abcdef"

    app_client.post(
        "/settings/api-keys",
        json={
            "name": "CoinGecko",
            "provider": "COINGECKO",
            "key_value": secret,
        },
        headers=headers,
    )

    response = app_client.get("/settings/api-keys", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert secret not in str(payload)
    assert payload["data"][0]["masked_key_value"].startswith("coin")


def test_delete_api_key_returns_not_found_afterwards(app_client: TestClient) -> None:
    token = _register_login(app_client)
    headers = _auth_headers(token)

    created = app_client.post(
        "/settings/api-keys",
        json={
            "name": "Temp Key",
            "provider": "ALPHA_VANTAGE",
            "key_value": "alpha-123456",
        },
        headers=headers,
    )
    api_key_id = created.json()["data"]["id"]

    delete_response = app_client.delete(f"/settings/api-keys/{api_key_id}", headers=headers)
    assert delete_response.status_code == 200

    delete_again = app_client.delete(f"/settings/api-keys/{api_key_id}", headers=headers)
    assert delete_again.status_code == 404


def test_users_only_access_their_own_settings(app_client: TestClient) -> None:
    token_a = _register_login(app_client)
    token_b = _register_login(app_client)

    app_client.put(
        "/settings",
        json={"base_currency": "GBP"},
        headers=_auth_headers(token_a),
    )

    response_b = app_client.get("/settings", headers=_auth_headers(token_b))
    assert response_b.status_code == 200
    assert response_b.json()["data"]["base_currency"] == "USD"
