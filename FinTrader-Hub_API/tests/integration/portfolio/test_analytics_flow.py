import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.factory import create_app
from core.config import get_settings
from modules.market.models.market_price import MarketPrice
import infrastructure.database.session as db_session


@pytest.fixture
def app_client() -> TestClient:
    get_settings.cache_clear()
    return TestClient(create_app())


def _unique_credentials() -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    return {
        "email": f"analytics_user_{suffix}@example.com",
        "username": f"analytics_user_{suffix}",
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
        json={"name": "Analytics", "description": "Test", "base_currency": "USD"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _create_asset(client: TestClient, token: str, symbol: str | None = None) -> int:
    suffix = uuid.uuid4().hex[:6].upper()
    response = client.post(
        "/assets",
        json={
            "symbol": symbol or f"AST{suffix}",
            "external_id": "bitcoin",
            "name": "Test Asset",
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
        "fees": "0",
        "executed_at": (datetime.now(UTC) + timedelta(minutes=offset_minutes)).isoformat(),
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
) -> None:
    response = client.post(
        f"/portfolios/{portfolio_id}/trades",
        json=_trade_payload(asset_id, trade_type, quantity, price, offset_minutes),
        headers=_auth_headers(token),
    )
    assert response.status_code == 201


def _save_market_price(asset_id: int, price: str) -> None:
    db = db_session.SessionLocal()
    try:
        db.add(
            MarketPrice(
                asset_id=asset_id,
                price=Decimal(price),
                source="test",
                timestamp=datetime.now(UTC),
            )
        )
        db.commit()
    finally:
        db.close()


def _get_positions(client: TestClient, token: str, portfolio_id: int) -> list[dict]:
    response = client.get(
        f"/portfolios/{portfolio_id}/positions",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_portfolio_value_with_multiple_positions(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_a = _create_asset(app_client, token, f"BTC{uuid.uuid4().hex[:4].upper()}")
    asset_b = _create_asset(app_client, token, f"ETH{uuid.uuid4().hex[:4].upper()}")

    _register_trade(app_client, token, portfolio_id, asset_a, "BUY", "2", "100", 0)
    _register_trade(app_client, token, portfolio_id, asset_b, "BUY", "1", "200", 1)
    _save_market_price(asset_a, "120")
    _save_market_price(asset_b, "250")

    response = app_client.get(
        f"/portfolios/{portfolio_id}/analytics/value",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()["data"]

    assert float(data["portfolio_value"]) == 490
    assert float(data["total_cost"]) == 400
    assert float(data["unrealized_pnl"]) == 90
    assert float(data["unrealized_pnl_pct"]) == 22.5
    assert data["assets_without_price"] == []
    assert len(data["positions"]) == 2


def test_portfolio_value_excludes_asset_without_price(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    priced_asset = _create_asset(app_client, token, f"PRC{uuid.uuid4().hex[:4].upper()}")
    unpriced_asset = _create_asset(app_client, token, f"NOP{uuid.uuid4().hex[:4].upper()}")

    _register_trade(app_client, token, portfolio_id, priced_asset, "BUY", "1", "100", 0)
    _register_trade(app_client, token, portfolio_id, unpriced_asset, "BUY", "1", "50", 1)
    _save_market_price(priced_asset, "110")

    response = app_client.get(
        f"/portfolios/{portfolio_id}/analytics/value",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()["data"]

    assert float(data["portfolio_value"]) == 110
    assert float(data["total_cost"]) == 100
    assert len(data["positions"]) == 1
    assert len(data["assets_without_price"]) == 1


def test_position_pnl_open_gain(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)
    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "2", "100", 0)
    _save_market_price(asset_id, "130")

    position_id = _get_positions(app_client, token, portfolio_id)[0]["id"]
    response = app_client.get(
        f"/portfolios/{portfolio_id}/positions/{position_id}/pnl",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["status"] == "OPEN"
    assert float(data["unrealized_pnl"]) == 60
    assert float(data["unrealized_pnl_pct"]) == 30
    assert data["realized_pnl"] is None


def test_position_pnl_open_loss(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)
    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "2", "100", 0)
    _save_market_price(asset_id, "70")

    position_id = _get_positions(app_client, token, portfolio_id)[0]["id"]
    response = app_client.get(
        f"/portfolios/{portfolio_id}/positions/{position_id}/pnl",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()["data"]

    assert float(data["unrealized_pnl"]) == -60
    assert float(data["unrealized_pnl_pct"]) == -30


def test_asset_allocation_sums_to_one_hundred(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_a = _create_asset(app_client, token, f"AAA{uuid.uuid4().hex[:4].upper()}")
    asset_b = _create_asset(app_client, token, f"BBB{uuid.uuid4().hex[:4].upper()}")

    _register_trade(app_client, token, portfolio_id, asset_a, "BUY", "1", "100", 0)
    _register_trade(app_client, token, portfolio_id, asset_b, "BUY", "1", "100", 1)
    _save_market_price(asset_a, "300")
    _save_market_price(asset_b, "100")

    response = app_client.get(
        f"/portfolios/{portfolio_id}/analytics/allocation",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()["data"]

    total_weight = sum(float(item["weight_pct"]) for item in data["by_asset"])
    assert abs(total_weight - 100) < 0.01
    assert float(data["by_asset"][0]["weight_pct"]) == 75
    assert float(data["by_asset"][1]["weight_pct"]) == 25


def test_portfolio_performance_open_and_closed(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    open_asset = _create_asset(app_client, token, f"OPN{uuid.uuid4().hex[:4].upper()}")
    closed_asset = _create_asset(app_client, token, f"CLS{uuid.uuid4().hex[:4].upper()}")

    _register_trade(app_client, token, portfolio_id, open_asset, "BUY", "2", "100", 0)
    _register_trade(app_client, token, portfolio_id, closed_asset, "BUY", "1", "50", 1)
    _register_trade(app_client, token, portfolio_id, closed_asset, "SELL", "1", "70", 2)
    _save_market_price(open_asset, "120")

    response = app_client.get(
        f"/portfolios/{portfolio_id}/analytics/performance",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()["data"]

    assert float(data["total_invested"]) == 250
    assert float(data["total_current_value"]) == 240
    assert float(data["total_realized_pnl"]) == 20
    assert float(data["total_unrealized_pnl"]) == 40
    assert float(data["total_pnl"]) == 60
    assert float(data["total_return_pct"]) == 24


def test_analytics_requires_portfolio_ownership(app_client: TestClient) -> None:
    token_a = _register_login(app_client)
    portfolio_a = _create_portfolio(app_client, token_a)
    token_b = _register_login(app_client)

    response = app_client.get(
        f"/portfolios/{portfolio_a}/analytics/value",
        headers=_auth_headers(token_b),
    )
    assert response.status_code == 404
