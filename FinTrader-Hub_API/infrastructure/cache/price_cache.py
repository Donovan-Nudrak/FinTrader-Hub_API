import json
import logging
from typing import Any

from infrastructure.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class PriceCache:
    KEY_PREFIX = "market:latest_price:"

    def __init__(self, ttl_seconds: int = 60) -> None:
        self.ttl_seconds = ttl_seconds
        self._redis = get_redis_client()

    def _key(self, asset_id: int) -> str:
        return f"{self.KEY_PREFIX}{asset_id}"

    def get_latest(self, asset_id: int) -> dict[str, Any] | None:
        try:
            raw = self._redis.get(self._key(asset_id))
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("Failed to read price cache for asset %s: %s", asset_id, exc)
            return None

    def set_latest(self, asset_id: int, payload: dict[str, Any]) -> None:
        try:
            self._redis.setex(
                self._key(asset_id),
                self.ttl_seconds,
                json.dumps(payload, default=str),
            )
        except Exception as exc:
            logger.warning("Failed to write price cache for asset %s: %s", asset_id, exc)

    def invalidate(self, asset_id: int) -> None:
        try:
            self._redis.delete(self._key(asset_id))
        except Exception as exc:
            logger.warning("Failed to invalidate price cache for asset %s: %s", asset_id, exc)
