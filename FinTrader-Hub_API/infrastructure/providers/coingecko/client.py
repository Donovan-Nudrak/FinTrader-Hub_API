import logging
from datetime import UTC, datetime
from decimal import Decimal

import httpx

from core.config import get_settings
from infrastructure.providers.base import request_with_retries
from infrastructure.providers.types import NormalizedPrice

logger = logging.getLogger(__name__)

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"


class CoinGeckoClient:
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.coingecko_api_key

    def fetch_price(self, coin_id: str, vs_currency: str = "usd") -> NormalizedPrice | None:
        if not coin_id:
            logger.warning("CoinGecko coin id is missing")
            return None

        normalized_coin_id = coin_id.strip().lower()
        normalized_currency = vs_currency.lower()

        params: dict[str, str] = {
            "ids": normalized_coin_id,
            "vs_currencies": normalized_currency,
        }
        if self.api_key:
            params["x_cg_demo_api_key"] = self.api_key

        try:
            response = request_with_retries(
                lambda: httpx.get(
                    f"{COINGECKO_BASE_URL}/simple/price",
                    params=params,
                    timeout=15.0,
                )
            )
            payload = response.json()
            coin_data = payload.get(normalized_coin_id)
            if not coin_data:
                logger.warning("CoinGecko response missing data for coin id %s", normalized_coin_id)
                return None

            price_value = coin_data.get(normalized_currency)
            if price_value is None:
                logger.warning(
                    "CoinGecko response missing %s price for coin id %s",
                    normalized_currency,
                    normalized_coin_id,
                )
                return None

            return NormalizedPrice(
                price=Decimal(str(price_value)),
                source="coingecko",
                timestamp=datetime.now(UTC),
            )
        except Exception as exc:
            logger.error("CoinGecko price fetch failed for %s: %s", normalized_coin_id, exc)
            return None
