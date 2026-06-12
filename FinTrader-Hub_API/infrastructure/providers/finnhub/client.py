import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx

from core.config import get_settings
from infrastructure.providers.base import request_with_retries
from infrastructure.providers.types import NormalizedNewsItem, NormalizedPrice

logger = logging.getLogger(__name__)

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


class FinnhubClient:
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.finnhub_api_key

    def fetch_price(self, symbol: str) -> NormalizedPrice | None:
        if not self.api_key:
            logger.warning("Finnhub API key is not configured")
            return None

        try:
            response = request_with_retries(
                lambda: httpx.get(
                    f"{FINNHUB_BASE_URL}/quote",
                    params={"symbol": symbol, "token": self.api_key},
                    timeout=15.0,
                )
            )
            payload = response.json()
            current_price = payload.get("c")
            if current_price in (None, 0):
                return None

            timestamp = payload.get("t")
            price_timestamp = (
                datetime.fromtimestamp(timestamp, tz=UTC)
                if timestamp
                else datetime.now(UTC)
            )
            return NormalizedPrice(
                price=Decimal(str(current_price)),
                source="finnhub",
                timestamp=price_timestamp,
            )
        except Exception as exc:
            logger.error("Finnhub price fetch failed for %s: %s", symbol, exc)
            return None

    def fetch_news(self, symbol: str, *, days: int = 7) -> list[NormalizedNewsItem]:
        if not self.api_key:
            logger.warning("Finnhub API key is not configured")
            return []

        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=days)

        try:
            response = request_with_retries(
                lambda: httpx.get(
                    f"{FINNHUB_BASE_URL}/company-news",
                    params={
                        "symbol": symbol,
                        "from": start_date.isoformat(),
                        "to": end_date.isoformat(),
                        "token": self.api_key,
                    },
                    timeout=15.0,
                )
            )
            payload = response.json()
            if not isinstance(payload, list):
                return []

            news_items: list[NormalizedNewsItem] = []
            for item in payload:
                published_ts = item.get("datetime")
                if not published_ts:
                    continue
                news_items.append(
                    NormalizedNewsItem(
                        title=item.get("headline", "").strip(),
                        summary=item.get("summary"),
                        source=item.get("source", "finnhub"),
                        url=item.get("url", "").strip(),
                        published_at=datetime.fromtimestamp(published_ts, tz=UTC),
                    )
                )
            return [item for item in news_items if item.title and item.url]
        except Exception as exc:
            logger.error("Finnhub news fetch failed for %s: %s", symbol, exc)
            return []
