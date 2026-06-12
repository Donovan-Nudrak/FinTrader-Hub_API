import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

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
        "email": f"alerts_user_{suffix}@example.com",
        "username": f"alerts_user_{suffix}",
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
        json={"name": "Alerts", "description": "Test", "base_currency": "USD"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _create_asset(client: TestClient, token: str, symbol: str | None = None) -> int:
    suffix = uuid.uuid4().hex[:6].upper()
    response = client.post(
        "/assets",
        json={
            "symbol": symbol or f"ALT{suffix}",
            "external_id": "bitcoin",
            "name": "Alert Asset",
            "market": "CRYPTO",
            "asset_type": "CRYPTO",
            "currency": "USD",
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


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


def test_create_and_get_alert(app_client: TestClient) -> None:
    token = _register_login(app_client)
    asset_id = _create_asset(app_client, token)

    create_response = app_client.post(
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
    assert create_response.status_code == 201
    alert_id = create_response.json()["data"]["id"]

    get_response = app_client.get(f"/alerts/{alert_id}", headers=_auth_headers(token))
    assert get_response.status_code == 200
    assert get_response.json()["data"]["alert_type"] == "PRICE"


def test_evaluate_price_alert_triggers_event(app_client: TestClient) -> None:
    token = _register_login(app_client)
    asset_id = _create_asset(app_client, token)
    _save_market_price(asset_id, "150")

    create_response = app_client.post(
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
    alert_id = create_response.json()["data"]["id"]

    with patch(
        "infrastructure.notifications.email.resend_client.ResendClient.send_alert_email",
        return_value=True,
    ):
        evaluate_response = app_client.post(
            f"/alerts/{alert_id}/evaluate",
            headers=_auth_headers(token),
        )

    assert evaluate_response.status_code == 200
    data = evaluate_response.json()["data"]
    assert data["triggered"] is True
    assert data["alert_event_id"] is not None


def test_cooldown_prevents_retrigger(app_client: TestClient) -> None:
    token = _register_login(app_client)
    asset_id = _create_asset(app_client, token)
    _save_market_price(asset_id, "150")

    create_response = app_client.post(
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
    alert_id = create_response.json()["data"]["id"]

    with patch(
        "infrastructure.notifications.email.resend_client.ResendClient.send_alert_email",
        return_value=True,
    ):
        app_client.post(f"/alerts/{alert_id}/evaluate", headers=_auth_headers(token))
        second = app_client.post(f"/alerts/{alert_id}/evaluate", headers=_auth_headers(token))

    assert second.json()["data"]["cooldown_active"] is True
    assert second.json()["data"]["triggered"] is False


def test_alert_history_returns_events(app_client: TestClient) -> None:
    token = _register_login(app_client)
    asset_id = _create_asset(app_client, token)
    _save_market_price(asset_id, "200")

    create_response = app_client.post(
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
    alert_id = create_response.json()["data"]["id"]

    with patch(
        "infrastructure.notifications.email.resend_client.ResendClient.send_alert_email",
        return_value=True,
    ):
        app_client.post(f"/alerts/{alert_id}/evaluate", headers=_auth_headers(token))

    history_response = app_client.get(
        f"/alerts/{alert_id}/history",
        headers=_auth_headers(token),
    )
    assert history_response.status_code == 200
    history = history_response.json()["data"]
    assert len(history) == 1
    assert history[0]["notification"]["status"] == "SENT"
    assert history[0]["notification"]["channel"] == "EMAIL"


def test_evaluate_alerts_celery_task(app_client: TestClient) -> None:
    token = _register_login(app_client)
    asset_id = _create_asset(app_client, token)
    _save_market_price(asset_id, "180")

    create_response = app_client.post(
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
    assert create_response.status_code == 201

    with patch(
        "infrastructure.notifications.email.resend_client.ResendClient.send_alert_email",
        return_value=True,
    ):
        from infrastructure.tasks.alert_tasks import evaluate_alerts

        result = evaluate_alerts()

    assert result["evaluated"] >= 1
