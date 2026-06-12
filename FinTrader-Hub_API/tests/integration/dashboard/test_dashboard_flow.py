import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.factory import create_app
from core.config import get_settings
import infrastructure.database.session as db_session
from modules.market.models.market_price import MarketPrice


@pytest.fixture
def app_client() -> TestClient:
    get_settings.cache_clear()
    return TestClient(create_app())


def _unique_credentials() -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    return {
        "email": f"dash_user_{suffix}@example.com",
        "username": f"dash_user_{suffix}",
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


def _create_portfolio(client: TestClient, token: str, name: str = "Dashboard") -> int:
    response = client.post(
        "/portfolios",
        json={"name": name, "description": "Test", "base_currency": "USD"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _create_asset(client: TestClient, token: str, symbol: str | None = None) -> int:
    suffix = uuid.uuid4().hex[:6].upper()
    response = client.post(
        "/assets",
        json={
            "symbol": symbol or f"DASH{suffix}",
            "external_id": "bitcoin",
            "name": "Dashboard Asset",
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


def _save_market_price(asset_id: int, price: str, *, hours_ago: float = 0) -> None:
    db = db_session.SessionLocal()
    try:
        db.add(
            MarketPrice(
                asset_id=asset_id,
                price=Decimal(price),
                source="test",
                timestamp=datetime.now(UTC) - timedelta(hours=hours_ago),
            )
        )
        db.commit()
    finally:
        db.close()


def test_dashboard_summary_with_positions_and_prices(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_a = _create_asset(app_client, token, f"DSA{uuid.uuid4().hex[:4].upper()}")
    asset_b = _create_asset(app_client, token, f"DSB{uuid.uuid4().hex[:4].upper()}")

    _register_trade(app_client, token, portfolio_id, asset_a, "BUY", "2", "100", 0)
    _register_trade(app_client, token, portfolio_id, asset_b, "BUY", "1", "200", 1)
    _save_market_price(asset_a, "120")
    _save_market_price(asset_b, "250")

    response = app_client.get("/dashboard/summary", headers=_auth_headers(token))
    assert response.status_code == 200
    data = response.json()["data"]

    assert float(data["portfolio_total_value"]) == 490
    assert data["open_positions_count"] == 2
    assert len(data["top_gainers"]) <= 3
    assert data["last_price_update"] is not None


def test_dashboard_summary_empty_portfolio(app_client: TestClient) -> None:
    token = _register_login(app_client)
    _create_portfolio(app_client, token, name="Empty")

    response = app_client.get("/dashboard/summary", headers=_auth_headers(token))
    assert response.status_code == 200
    data = response.json()["data"]

    assert float(data["portfolio_total_value"]) == 0
    assert data["open_positions_count"] == 0
    assert data["top_gainers"] == []
    assert data["top_losers"] == []


def test_top_movers_with_24h_history(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)

    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "1", "100", 0)
    _save_market_price(asset_id, "100", hours_ago=24)
    _save_market_price(asset_id, "130")

    response = app_client.get("/dashboard/top-movers", headers=_auth_headers(token))
    assert response.status_code == 200
    data = response.json()["data"]

    assert len(data["top_gainers"]) == 1
    assert float(data["top_gainers"][0]["change_pct"]) == 30


def test_top_movers_without_24h_history_returns_empty(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)

    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "1", "100", 0)
    _save_market_price(asset_id, "100")

    response = app_client.get("/dashboard/top-movers", headers=_auth_headers(token))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["top_gainers"] == []
    assert data["top_losers"] == []


def test_active_alerts_returns_only_active(app_client: TestClient) -> None:
    token = _register_login(app_client)
    asset_id = _create_asset(app_client, token)

    active = app_client.post(
        "/alerts",
        json={
            "asset_id": asset_id,
            "alert_type": "PRICE",
            "condition": "ABOVE",
            "threshold": "100",
            "is_active": True,
        },
        headers=_auth_headers(token),
    )
    assert active.status_code == 201

    inactive = app_client.post(
        "/alerts",
        json={
            "asset_id": asset_id,
            "alert_type": "PRICE",
            "condition": "BELOW",
            "threshold": "50",
            "is_active": False,
        },
        headers=_auth_headers(token),
    )
    assert inactive.status_code == 201

    response = app_client.get("/dashboard/alerts", headers=_auth_headers(token))
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["total_active"] == 1
    assert len(data["alerts"]) == 1
    assert data["alerts"][0]["alert_type"] == "PRICE"


def test_daily_performance_without_trades_uses_prices_only(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)

    buy_response = app_client.post(
        f"/portfolios/{portfolio_id}/trades",
        json={
            "asset_id": asset_id,
            "trade_type": "BUY",
            "quantity": "1",
            "price": "100",
            "fees": "0",
            "executed_at": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
        },
        headers=_auth_headers(token),
    )
    assert buy_response.status_code == 201
    day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    hours_since_day_start = (datetime.now(UTC) - day_start).total_seconds() / 3600
    _save_market_price(asset_id, "100", hours_ago=hours_since_day_start + 1)
    _save_market_price(asset_id, "110")

    response = app_client.get("/dashboard/daily-performance", headers=_auth_headers(token))
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["trades_executed_today"] == 0
    assert float(data["current_value"]) == 110
    assert float(data["change_value"]) == 10


def test_portfolio_snapshot_consistent_with_analytics(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token, name="Main")
    asset_id = _create_asset(app_client, token)
    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "2", "100", 0)
    _save_market_price(asset_id, "120")

    analytics = app_client.get(
        f"/portfolios/{portfolio_id}/analytics/value",
        headers=_auth_headers(token),
    )
    snapshot = app_client.get("/dashboard/portfolio-snapshot", headers=_auth_headers(token))

    analytics_data = analytics.json()["data"]
    snapshot_item = snapshot.json()["data"]["portfolios"][0]

    assert float(snapshot_item["current_value"]) == float(analytics_data["portfolio_value"])
    assert float(snapshot_item["total_cost"]) == float(analytics_data["total_cost"])
    assert float(snapshot_item["unrealized_pnl"]) == float(analytics_data["unrealized_pnl"])
