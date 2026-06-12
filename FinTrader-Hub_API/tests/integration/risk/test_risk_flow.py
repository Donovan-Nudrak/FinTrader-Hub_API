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
        "email": f"risk_user_{suffix}@example.com",
        "username": f"risk_user_{suffix}",
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
        json={"name": "Risk", "description": "Test", "base_currency": "USD"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _create_asset(client: TestClient, token: str, symbol: str | None = None) -> int:
    suffix = uuid.uuid4().hex[:6].upper()
    response = client.post(
        "/assets",
        json={
            "symbol": symbol or f"RISK{suffix}",
            "external_id": "bitcoin",
            "name": "Risk Asset",
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


def _save_market_price(asset_id: int, price: str, days_ago: int = 0) -> None:
    db = db_session.SessionLocal()
    try:
        db.add(
            MarketPrice(
                asset_id=asset_id,
                price=Decimal(price),
                source="test",
                timestamp=datetime.now(UTC) - timedelta(days=days_ago),
            )
        )
        db.commit()
    finally:
        db.close()


def test_exposure_endpoint_sums_one_hundred(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_a = _create_asset(app_client, token, f"EXA{uuid.uuid4().hex[:4].upper()}")
    asset_b = _create_asset(app_client, token, f"EXB{uuid.uuid4().hex[:4].upper()}")

    _register_trade(app_client, token, portfolio_id, asset_a, "BUY", "1", "100", 0)
    _register_trade(app_client, token, portfolio_id, asset_b, "BUY", "1", "100", 1)
    _save_market_price(asset_a, "300")
    _save_market_price(asset_b, "100")

    response = app_client.get(
        f"/portfolios/{portfolio_id}/risk/exposure",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()["data"]

    total_weight = sum(item["weight_pct"] for item in data["by_asset"])
    assert abs(total_weight - 100.0) < 0.01
    assert data["hhi"] > 0


def test_position_sizing_endpoint_returns_kelly_and_fixed_risk(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)

    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "1", "100", 0)
    _register_trade(app_client, token, portfolio_id, asset_id, "SELL", "1", "120", 1)
    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "1", "100", 2)
    _register_trade(app_client, token, portfolio_id, asset_id, "SELL", "1", "90", 3)

    response = app_client.post(
        f"/portfolios/{portfolio_id}/risk/position-sizing",
        json={
            "entry_price": "100",
            "stop_loss": "95",
            "capital": "10000",
            "risk_pct": "0.02",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["fixed_risk"] is not None
    assert float(data["fixed_risk"]["quantity"]) == 40.0
    assert data["kelly"] is not None


def test_drawdown_endpoint_with_price_history(app_client: TestClient) -> None:
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
            "executed_at": (datetime.now(UTC) - timedelta(days=20)).isoformat(),
        },
        headers=_auth_headers(token),
    )
    assert buy_response.status_code == 201

    for day, price in enumerate([100, 120, 90, 110]):
        _save_market_price(asset_id, str(price), days_ago=10 - day)

    response = app_client.get(
        f"/portfolios/{portfolio_id}/risk/drawdown",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()["data"]

    assert len(data["value_series"]) >= 2
    assert data["maximum_drawdown"] is not None
    assert abs(float(data["maximum_drawdown"]) - 0.25) < 0.01


def test_risk_report_aggregates_metrics(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)

    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "1", "100", 0)
    _save_market_price(asset_id, "110")

    response = app_client.get(
        f"/portfolios/{portfolio_id}/risk/report",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()["data"]

    assert "drawdown" in data
    assert "sharpe" in data
    assert "sortino" in data
    assert "exposure" in data
    assert "correlation" in data


def test_sharpe_insufficient_data_flag(app_client: TestClient) -> None:
    token = _register_login(app_client)
    portfolio_id = _create_portfolio(app_client, token)
    asset_id = _create_asset(app_client, token)

    _register_trade(app_client, token, portfolio_id, asset_id, "BUY", "1", "100", 0)
    _save_market_price(asset_id, "110")

    response = app_client.get(
        f"/portfolios/{portfolio_id}/risk/sharpe",
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["insufficient_data"] is True
    assert data["sharpe_ratio"] is None


def test_risk_requires_portfolio_ownership(app_client: TestClient) -> None:
    token_a = _register_login(app_client)
    portfolio_a = _create_portfolio(app_client, token_a)
    token_b = _register_login(app_client)

    response = app_client.get(
        f"/portfolios/{portfolio_a}/risk/exposure",
        headers=_auth_headers(token_b),
    )
    assert response.status_code == 404
