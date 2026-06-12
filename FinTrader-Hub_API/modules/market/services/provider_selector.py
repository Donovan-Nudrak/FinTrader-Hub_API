import logging

from core.enums import AssetType
from modules.asset.models.asset import Asset
from infrastructure.providers.alphavantage import AlphaVantageClient
from infrastructure.providers.coingecko import CoinGeckoClient
from infrastructure.providers.finnhub import FinnhubClient
from infrastructure.providers.types import NormalizedNewsItem, NormalizedPrice

logger = logging.getLogger(__name__)


class ProviderSelector:
    def __init__(self) -> None:
        self.finnhub = FinnhubClient()
        self.coingecko = CoinGeckoClient()
        self.alphavantage = AlphaVantageClient()

    def fetch_price(self, asset: Asset) -> NormalizedPrice | None:
        if asset.asset_type == AssetType.CRYPTO:
            coin_id = asset.external_id or asset.symbol.lower()
            return self.coingecko.fetch_price(coin_id, vs_currency=asset.currency)

        if asset.asset_type in {AssetType.STOCK, AssetType.ETF}:
            price = self.finnhub.fetch_price(asset.symbol)
            if price is not None:
                return price
            logger.warning("Finnhub failed for %s, falling back to AlphaVantage", asset.symbol)
            return self.alphavantage.fetch_stock_price(asset.symbol)

        if asset.asset_type == AssetType.FOREX:
            symbol = asset.symbol.upper()
            if len(symbol) >= 6:
                from_currency = symbol[:3]
                to_currency = symbol[3:6]
                return self.alphavantage.fetch_forex_price(from_currency, to_currency)
            return self.alphavantage.fetch_forex_price(symbol[:3], asset.currency)

        logger.warning("No price provider configured for asset type %s", asset.asset_type)
        return None

    def fetch_news(self, asset: Asset) -> list[NormalizedNewsItem]:
        if asset.asset_type in {AssetType.STOCK, AssetType.ETF}:
            return self.finnhub.fetch_news(asset.symbol)

        logger.info("News provider not configured for asset type %s", asset.asset_type)
        return []
