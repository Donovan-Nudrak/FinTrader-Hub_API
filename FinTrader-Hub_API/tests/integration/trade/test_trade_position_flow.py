import uuid
from datetime import UTC, datetime, timedelta

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
        "email": f"trade_user_{suffix}@example.com",
        "username": f"trade_user_{suffix}",
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


def _create_portfolio(client: TestClient, token: str) -> int:
    response = client.post(
        "/portfolios",
        json={"name": "Trading", "description": "Test", "base_currency": "USD"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _create_asset(client: TestClient, token: str, symbol: str | None = None) -> int:
    suffix = uuid.uuid4().hex[:6].upper()
    response = client.post(
        "/assets",
        json={
            "symbol": symbol or f"BTC{suffix}",
            "external_id": "bitcoin",
            "name": "Bitcoin",
            "market": "CRYPTO",
            "asset_type": "CRYPTO",
            "currency": "USD",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _trade_payload(asset_id: int, trade_type: str, quantity: str, price: str, offset_minutes: int = 0) -> dict:
    return {
        "asset_id": asset_id,
        "trade_type": trade_type,
        "quantity": quantity,
        "price": price,
        "fees": "1.00",
        "executed_at": (datetime.now(UTC) + timedelta(minutes=offset_minutes)).isoformat(),
        "notes": "test trade",
    }


def _register_trade(
    client: TestClient,
    token: str,
    portfolio_id: int,
    asset_id: int,
    trade_type: str,
    quantity: str,
    price: str,
    offset_minutes: int = 0,
) -> dict:
    response = client.post(
        f"/portfolios/{portfolio_id}/trades",
        json=_trade_payload(asset_id, trade_type, quantity, price, offset_minutes),
        headers=_auth_headers(token),
    )
    return response


def _get_positions(client: TestClient, token: str, portfolio_id: int) -> list[dict]:
    response = client.get(
        f"/portfolios/{portfolio_id}/positions",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_register_trade_buy_opens_long_position(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)

    response = _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "1", "100000")
    assert response.status_code == 201

    positions = _get_positions(app_client, token, portfolio_id)
    assert len(positions) == 1
    assert positions[0]["position_type"] == "LONG"
    assert positions[0]["status"] == "OPEN"
    assert float(positions[0]["quantity"]) == 1
    assert float(positions[0]["average_price"]) == 100000


def test_weighted_average_after_second_buy(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)

    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "1", "100", 0)
    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "1", "110", 1)

    positions = _get_positions(app_client, token, portfolio_id)
    assert float(positions[0]["quantity"]) == 2
    assert float(positions[0]["average_price"]) == 105
    assert float(positions[0]["total_cost"]) == 210


def test_partial_sell_keeps_position_open(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)

    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "2", "100", 0)
    response = _register_trade(app_client, token, portfolio_id, asset_id, "SELL", "1", "120", 1)
    assert response.status_code == 201

    positions = _get_positions(app_client, token, portfolio_id)
    assert positions[0]["status"] == "OPEN"
    assert float(positions[0]["quantity"]) == 1
    assert float(positions[0]["average_price"]) == 100


def test_full_sell_closes_position(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)

    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "1", "100", 0)
    _register_trade(app_client, token, portfolio_id, asset_id, "SELL", "1", "120", 1)

    positions = _get_positions(app_client, token, portfolio_id)
    assert positions[0]["status"] == "CLOSED"
    assert float(positions[0]["quantity"]) == 0


def test_short_and_cover_flow(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)

    _register_trade(app_client, token, portfolio_id, asset_id, "SHORT", "2", "50", 0)
    positions = _get_positions(app_client, token, portfolio_id)
    assert positions[0]["position_type"] == "SHORT"
    assert positions[0]["status"] == "OPEN"
    assert float(positions[0]["quantity"]) == 2

    _register_trade(app_client, token, portfolio_id, asset_id, "COVER", "2", "45", 1)
    positions = _get_positions(app_client, token, portfolio_id)
    assert positions[0]["status"] == "CLOSED"
    assert float(positions[0]["quantity"]) == 0


def test_sell_without_open_position_returns_error(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)

    response = _register_trade(app_client, token, portfolio_id, asset_id, "SELL", "1", "100", 0)
    assert response.status_code == 422
    assert "LONG" in response.json()["message"]


def test_sell_exceeding_quantity_returns_error(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)

    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "1", "100", 0)
    response = _register_trade(app_client, token, portfolio_id, asset_id, "SELL", "2", "100", 1)

    assert response.status_code == 422
    assert "exceeds" in response.json()["message"].lower()


def test_trade_authorization_by_portfolio(app_client: TestClient) -> None:
    token_a = _register_login(app_client)
    portfolio_a = _create_portfolio(app_client, token_a)
    asset_id = _create_asset(app_client, token_a)
    _register_trade(app_client, token_a, portfolio_a, asset_id, "BUY", "1", "100", 0)

    token_b = _register_login(app_client)
    portfolio_b = _create_portfolio(app_client, token_b)

    list_response = app_client.get(
        f"/portfolios/{portfolio_a}/trades",
        headers=_auth_headers(token_b),
    )
    assert list_response.status_code == 404

    trade_response = app_client.post(
        f"/portfolios/{portfolio_a}/trades",
        json=_trade_payload(asset_id, "BUY", "1", "100"),
        headers=_auth_headers(token_b),
    )
    assert trade_response.status_code == 404

    own_response = app_client.get(
        f"/portfolios/{portfolio_b}/trades",
        headers=_auth_headers(token_b),
    )
    assert own_response.status_code == 200
    assert own_response.json()["data"] == []
