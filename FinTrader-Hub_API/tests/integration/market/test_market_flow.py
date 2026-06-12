import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from core.enums import AssetType, MarketType
from infrastructure.providers.types import NormalizedNewsItem, NormalizedPrice
from modules.asset.models.asset import Asset
from modules.market.services.market_service import MarketService
import infrastructure.database.session as db_session


def _create_asset(
    client: TestClient,
    headers: dict[str, str],
    asset_type: str = "CRYPTO",
    symbol: str | None = None,
) -> int:
    suffix = uuid.uuid4().hex[:6].upper()
    response = client.post(
        "/assets",
        json={
            "symbol": symbol or f"BTC{suffix}",
            "external_id": "bitcoin",
            "name": "Bitcoin",
            "market": "CRYPTO" if asset_type == "CRYPTO" else "NASDAQ",
            "asset_type": asset_type,
            "currency": "USD",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _normalized_price(value: str = "42000") -> NormalizedPrice:
    return NormalizedPrice(
        price=Decimal(value),
        source="coingecko",
        timestamp=datetime.now(UTC),
    )


def _normalized_news() -> list[NormalizedNewsItem]:
    return [
        NormalizedNewsItem(
            title="Bitcoin hits new milestone",
            summary="Markets react positively",
            source="finnhub",
            url=f"https://news.example.com/{uuid.uuid4().hex}",
            published_at=datetime.now(UTC),
        )
    ]


def test_save_market_price_and_get_latest(app_client: TestClient, auth_headers: dict[str, str]) -> None:
    asset_id = _create_asset(app_client, auth_headers)

    with patch(
        "modules.market.services.provider_selector.ProviderSelector.fetch_price",
        return_value=_normalized_price("43000"),
    ):
        fetch_response = app_client.post(
            "/market/prices/fetch",
            json={"asset_id": asset_id},
            headers=auth_headers,
        )

    assert fetch_response.status_code == 200
    assert float(fetch_response.json()["data"]["price"]) == 43000

    latest_response = app_client.get(f"/market/prices/{asset_id}/latest")
    assert latest_response.status_code == 200
    assert float(latest_response.json()["data"]["price"]) == 43000


def test_fetch_market_price_requires_authentication(app_client: TestClient, auth_headers: dict[str, str]) -> None:
    asset_id = _create_asset(app_client, auth_headers)

    response = app_client.post("/market/prices/fetch", json={"asset_id": asset_id})

    assert response.status_code == 401


def test_historical_prices_range(app_client: TestClient, auth_headers: dict[str, str]) -> None:
    asset_id = _create_asset(app_client, auth_headers)
    now = datetime.now(UTC)

    with patch(
        "modules.market.services.provider_selector.ProviderSelector.fetch_price",
        side_effect=[_normalized_price("100"), _normalized_price("110"), _normalized_price("120")],
    ):
        app_client.post(
            "/market/prices/fetch",
            json={"asset_id": asset_id},
            headers=auth_headers,
        )
        app_client.post(
            "/market/prices/fetch",
            json={"asset_id": asset_id},
            headers=auth_headers,
        )
        app_client.post(
            "/market/prices/fetch",
            json={"asset_id": asset_id},
            headers=auth_headers,
        )

    response = app_client.get(
        f"/market/prices/{asset_id}/historical",
        params={
            "from_date": (now - timedelta(days=1)).isoformat(),
            "to_date": (now + timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 200
    assert len(response.json()["data"]) == 3


def test_save_news_without_duplicates(app_client: TestClient, auth_headers: dict[str, str]) -> None:
    asset_id = _create_asset(app_client, auth_headers, asset_type="STOCK")

    fixed_news = _normalized_news()

    with patch(
        "modules.market.services.provider_selector.ProviderSelector.fetch_news",
        return_value=fixed_news,
    ):
        first = app_client.post(
            "/market/news/fetch",
            json={"asset_id": asset_id},
            headers=auth_headers,
        )
        second = app_client.post(
            "/market/news/fetch",
            json={"asset_id": asset_id},
            headers=auth_headers,
        )

    assert first.status_code == 200
    assert len(first.json()["data"]) == 1
    assert second.status_code == 200
    assert len(second.json()["data"]) == 0

    news_response = app_client.get(f"/market/news/{asset_id}")
    assert news_response.status_code == 200
    assert len(news_response.json()["data"]) == 1


def test_fetch_news_requires_authentication(app_client: TestClient, auth_headers: dict[str, str]) -> None:
    asset_id = _create_asset(app_client, auth_headers, asset_type="STOCK")

    response = app_client.post("/market/news/fetch", json={"asset_id": asset_id})

    assert response.status_code == 401


def test_provider_failure_does_not_break_update_task() -> None:
    db = db_session.SessionLocal()
    try:
        suffix = uuid.uuid4().hex[:6].upper()
        asset = Asset(
            symbol=f"TST{suffix}",
            external_id="bitcoin",
            name="Test Asset",
            market=MarketType.CRYPTO,
            asset_type=AssetType.CRYPTO,
            currency="USD",
            is_active=True,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)

        service = MarketService(db)
        with patch.object(MarketService, "_list_active_assets", return_value=[asset]):
            with patch(
                "modules.market.services.provider_selector.ProviderSelector.fetch_price",
                return_value=None,
            ):
                result = service.update_market_prices()

        assert result == {"updated": 0, "failed": 1, "total": 1}
    finally:
        db.close()


def test_celery_beat_schedule_configuration() -> None:
    from infrastructure.tasks.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    assert "update-market-prices" in schedule
    assert "update-news-feed" in schedule
    assert schedule["update-market-prices"]["schedule"] == 300.0
    assert schedule["update-news-feed"]["schedule"] == 1800.0


def test_celery_market_tasks_execute() -> None:
    from infrastructure.tasks.market_tasks import update_market_prices, update_news_feed

    with patch.object(MarketService, "update_market_prices", return_value={"updated": 0, "failed": 0, "total": 0}):
        assert update_market_prices() == {"updated": 0, "failed": 0, "total": 0}

    with patch.object(
        MarketService,
        "update_news_feed",
        return_value={"saved": 0, "failed": 0, "deleted": 0, "total": 0},
    ):
        assert update_news_feed() == {"saved": 0, "failed": 0, "deleted": 0, "total": 0}
