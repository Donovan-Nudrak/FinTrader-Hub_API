import uuid

import pytest
from fastapi.testclient import TestClient

from app.factory import create_app
from core.config import get_settings


@pytest.fixture
def app_client() -> TestClient:
    get_settings.cache_clear()
    return TestClient(create_app())


def _unique_credentials() -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    return {
        "email": f"portfolio_user_{suffix}@example.com",
        "username": f"portfolio_user_{suffix}",
        "password": "SecurePass123!",
    }


def _register_and_login(client: TestClient, credentials: dict[str, str] | None = None) -> tuple[dict, str]:
    creds = credentials or _unique_credentials()
    register_response = client.post("/auth/register", json=creds)
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["data"]["access_token"]
    return creds, access_token


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _create_portfolio(client: TestClient, access_token: str, name: str = "Trading Portfolio") -> dict:
    response = client.post(
        "/portfolios",
        json={
            "name": name,
            "description": "Main trading account",
            "base_currency": "usd",
        },
        headers=_auth_headers(access_token),
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_create_portfolio_success(app_client: TestClient) -> None:
    _, access_token = _register_and_login(app_client)
    portfolio = _create_portfolio(app_client, access_token)

    assert portfolio["name"] == "Trading Portfolio"
    assert portfolio["description"] == "Main trading account"
    assert portfolio["base_currency"] == "USD"
    assert portfolio["is_active"] is True
    assert "user_id" in portfolio


def test_list_portfolios_success(app_client: TestClient) -> None:
    _, access_token = _register_and_login(app_client)
    _create_portfolio(app_client, access_token, name="Portfolio A")
    _create_portfolio(app_client, access_token, name="Portfolio B")

    response = app_client.get("/portfolios", headers=_auth_headers(access_token))

    assert response.status_code == 200
    portfolios = response.json()["data"]
    assert len(portfolios) == 2
    names = {portfolio["name"] for portfolio in portfolios}
    assert names == {"Portfolio A", "Portfolio B"}


def test_get_portfolio_success(app_client: TestClient) -> None:
    _, access_token = _register_and_login(app_client)
    created = _create_portfolio(app_client, access_token)

    response = app_client.get(
        f"/portfolios/{created['id']}",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["id"] == created["id"]
    assert response.json()["data"]["name"] == created["name"]


def test_update_portfolio_success(app_client: TestClient) -> None:
    _, access_token = _register_and_login(app_client)
    created = _create_portfolio(app_client, access_token)

    response = app_client.put(
        f"/portfolios/{created['id']}",
        json={
            "name": "Updated Portfolio",
            "description": "Updated description",
            "base_currency": "eur",
            "is_active": True,
        },
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    updated = response.json()["data"]
    assert updated["name"] == "Updated Portfolio"
    assert updated["description"] == "Updated description"
    assert updated["base_currency"] == "EUR"


def test_delete_portfolio_success(app_client: TestClient) -> None:
    _, access_token = _register_and_login(app_client)
    created = _create_portfolio(app_client, access_token)

    delete_response = app_client.delete(
        f"/portfolios/{created['id']}",
        headers=_auth_headers(access_token),
    )
    assert delete_response.status_code == 200

    get_response = app_client.get(
        f"/portfolios/{created['id']}",
        headers=_auth_headers(access_token),
    )
    assert get_response.status_code == 404


def test_portfolio_routes_require_authentication(app_client: TestClient) -> None:
    response = app_client.get("/portfolios")
    assert response.status_code == 401


def test_user_cannot_access_other_users_portfolio(app_client: TestClient) -> None:
    _, user_a_token = _register_and_login(app_client)
    portfolio = _create_portfolio(app_client, user_a_token)

    _, user_b_token = _register_and_login(app_client)

    get_response = app_client.get(
        f"/portfolios/{portfolio['id']}",
        headers=_auth_headers(user_b_token),
    )
    assert get_response.status_code == 404

    update_response = app_client.put(
        f"/portfolios/{portfolio['id']}",
        json={"name": "Hacked"},
        headers=_auth_headers(user_b_token),
    )
    assert update_response.status_code == 404

    delete_response = app_client.delete(
        f"/portfolios/{portfolio['id']}",
        headers=_auth_headers(user_b_token),
    )
    assert delete_response.status_code == 404

    owner_response = app_client.get(
        f"/portfolios/{portfolio['id']}",
        headers=_auth_headers(user_a_token),
    )
    assert owner_response.status_code == 200


def test_user_portfolio_list_is_isolated(app_client: TestClient) -> None:
    _, user_a_token = _register_and_login(app_client)
    _create_portfolio(app_client, user_a_token, name="User A Portfolio")

    _, user_b_token = _register_and_login(app_client)

    list_response = app_client.get("/portfolios", headers=_auth_headers(user_b_token))
    assert list_response.status_code == 200
    assert list_response.json()["data"] == []
