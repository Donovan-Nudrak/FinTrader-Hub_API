from unittest.mock import MagicMock, patch

from infrastructure.cache.price_cache import PriceCache


def test_price_cache_get_and_set() -> None:
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    with patch("infrastructure.cache.price_cache.get_redis_client", return_value=mock_redis):
        cache = PriceCache(ttl_seconds=60)
        payload = {"asset_id": 1, "price": "100.5", "source": "test"}
        cache.set_latest(1, payload)

    mock_redis.setex.assert_called_once()
    args = mock_redis.setex.call_args[0]
    assert args[0] == "market:latest_price:1"
    assert args[1] == 60


def test_price_cache_returns_cached_payload() -> None:
    mock_redis = MagicMock()
    mock_redis.get.return_value = '{"asset_id": 1, "price": "42"}'

    with patch("infrastructure.cache.price_cache.get_redis_client", return_value=mock_redis):
        cache = PriceCache()
        result = cache.get_latest(1)

    assert result == {"asset_id": 1, "price": "42"}
