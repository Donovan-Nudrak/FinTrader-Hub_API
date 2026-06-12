import logging
from datetime import UTC, datetime
from decimal import Decimal

import httpx

from core.config import get_settings
from infrastructure.providers.base import request_with_retries
from infrastructure.providers.types import NormalizedPrice

logger = logging.getLogger(__name__)

ALPHAVANTAGE_BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageClient:
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.alpha_vantage_api_key

    def fetch_stock_price(self, symbol: str) -> NormalizedPrice | None:
        if not self.api_key:
            logger.warning("AlphaVantage API key is not configured")
            return None

        try:
            response = request_with_retries(
                lambda: httpx.get(
                    ALPHAVANTAGE_BASE_URL,
                    params={
                        "function": "GLOBAL_QUOTE",
                        "symbol": symbol,
                        "apikey": self.api_key,
                    },
                    timeout=20.0,
                )
            )
            payload = response.json()
            quote = payload.get("Global Quote", {})
            price_value = quote.get("05. price")
            if not price_value:
                return None

            latest_day = quote.get("07. latest trading day")
            timestamp = (
                datetime.strptime(latest_day, "%Y-%m-%d").replace(tzinfo=UTC)
                if latest_day
                else datetime.now(UTC)
            )
            return NormalizedPrice(
                price=Decimal(str(price_value)),
                source="alphavantage",
                timestamp=timestamp,
            )
        except Exception as exc:
            logger.error("AlphaVantage stock fetch failed for %s: %s", symbol, exc)
            return None

    def fetch_forex_price(self, from_currency: str, to_currency: str) -> NormalizedPrice | None:
        if not self.api_key:
            logger.warning("AlphaVantage API key is not configured")
            return None

        try:
            response = request_with_retries(
                lambda: httpx.get(
                    ALPHAVANTAGE_BASE_URL,
                    params={
                        "function": "CURRENCY_EXCHANGE_RATE",
                        "from_currency": from_currency.upper(),
                        "to_currency": to_currency.upper(),
                        "apikey": self.api_key,
                    },
                    timeout=20.0,
                )
            )
            payload = response.json()
            rate_data = payload.get("Realtime Currency Exchange Rate", {})
            price_value = rate_data.get("5. Exchange Rate")
            if not price_value:
                return None

            last_refreshed = rate_data.get("6. Last Refreshed")
            timestamp = (
                datetime.strptime(last_refreshed, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
                if last_refreshed
                else datetime.now(UTC)
            )
            return NormalizedPrice(
                price=Decimal(str(price_value)),
                source="alphavantage",
                timestamp=timestamp,
            )
        except Exception as exc:
            logger.error(
                "AlphaVantage forex fetch failed for %s/%s: %s",
                from_currency,
                to_currency,
                exc,
            )
            return None
