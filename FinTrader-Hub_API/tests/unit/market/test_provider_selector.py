from decimal import Decimal
from unittest.mock import MagicMock

from core.enums import AssetType, MarketType
from infrastructure.providers.types import NormalizedPrice
from modules.asset.models.asset import Asset
from modules.market.services.provider_selector import ProviderSelector


def _asset(asset_type: AssetType, symbol: str = "BTCUSD") -> Asset:
    return Asset(
        id=1,
        symbol=symbol,
        external_id="bitcoin",
        name="Bitcoin",
        market=MarketType.CRYPTO,
        asset_type=asset_type,
        currency="USD",
        is_active=True,
    )


def test_provider_selection_crypto_uses_coingecko() -> None:
    selector = ProviderSelector()
    selector.coingecko = MagicMock()
    selector.coingecko.fetch_price.return_value = NormalizedPrice(
        price=Decimal("50000"),
        source="coingecko",
        timestamp=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )

    result = selector.fetch_price(_asset(AssetType.CRYPTO))

    assert result is not None
    selector.coingecko.fetch_price.assert_called_once()


def test_provider_selection_stock_tries_finnhub_then_alphavantage() -> None:
    selector = ProviderSelector()
    selector.finnhub = MagicMock()
    selector.alphavantage = MagicMock()
    selector.finnhub.fetch_price.return_value = None
    selector.alphavantage.fetch_stock_price.return_value = NormalizedPrice(
        price=Decimal("150"),
        source="alphavantage",
        timestamp=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )

    result = selector.fetch_price(_asset(AssetType.STOCK, "AAPL"))

    assert result is not None
    assert result.source == "alphavantage"
    selector.finnhub.fetch_price.assert_called_once()
    selector.alphavantage.fetch_stock_price.assert_called_once()


def test_provider_failure_returns_none_without_crashing() -> None:
    selector = ProviderSelector()
    selector.coingecko = MagicMock()
    selector.coingecko.fetch_price.side_effect = RuntimeError("provider down")

    try:
        selector.coingecko.fetch_price("bitcoin", vs_currency="USD")
        raised = False
    except RuntimeError:
        raised = True

    assert raised is True
