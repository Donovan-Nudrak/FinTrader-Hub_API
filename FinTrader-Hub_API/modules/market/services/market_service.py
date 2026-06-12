import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from core.config import get_settings
from core.exceptions import NotFoundError, ValidationError
from modules.asset.models.asset import Asset
from modules.asset.repositories.asset_repository import AssetRepository
from modules.market.models.market_price import MarketPrice
from modules.market.models.news import News
from modules.market.repositories import MarketPriceRepository, NewsRepository
from modules.market.schemas import MarketPriceResponse, NewsResponse
from infrastructure.cache.price_cache import PriceCache
from modules.market.services.provider_selector import ProviderSelector

logger = logging.getLogger(__name__)


class MarketService:
    def __init__(self, db: Session, price_cache: PriceCache | None = None) -> None:
        self.db = db
        self.asset_repository = AssetRepository(db)
        self.market_price_repository = MarketPriceRepository(db)
        self.news_repository = NewsRepository(db)
        self.provider_selector = ProviderSelector()
        self.settings = get_settings()
        self.price_cache = price_cache or PriceCache(
            ttl_seconds=self.settings.market_price_cache_ttl_seconds,
        )

    def fetch_market_price(self, asset_id: int) -> MarketPriceResponse:
        asset = self._get_active_asset(asset_id)
        normalized_price = self.provider_selector.fetch_price(asset)
        if normalized_price is None:
            raise ValidationError("Unable to fetch market price from providers")

        market_price = MarketPrice(
            asset_id=asset.id,
            price=normalized_price.price,
            source=normalized_price.source,
            timestamp=normalized_price.timestamp,
        )
        saved = self.market_price_repository.create(market_price)
        self.db.commit()
        response = MarketPriceResponse.model_validate(saved)
        self.price_cache.set_latest(asset_id, response.model_dump(mode="json"))
        return response

    def get_asset_price(self, asset_id: int) -> MarketPriceResponse:
        self._ensure_asset_exists(asset_id)
        cached = self.price_cache.get_latest(asset_id)
        if cached is not None:
            return MarketPriceResponse.model_validate(cached)

        latest = self.market_price_repository.get_latest_by_asset_id(asset_id)
        if latest is None:
            raise NotFoundError("No market price found for asset")
        response = MarketPriceResponse.model_validate(latest)
        self.price_cache.set_latest(asset_id, response.model_dump(mode="json"))
        return response

    def get_historical_prices(
        self,
        asset_id: int,
        *,
        from_date: datetime,
        to_date: datetime,
    ) -> list[MarketPriceResponse]:
        self._ensure_asset_exists(asset_id)
        if from_date > to_date:
            raise ValidationError("from_date must be before or equal to to_date")

        prices = self.market_price_repository.list_by_asset_and_range(
            asset_id,
            from_date=from_date,
            to_date=to_date,
        )
        return [MarketPriceResponse.model_validate(price) for price in prices]

    def fetch_news(self, asset_id: int) -> list[NewsResponse]:
        asset = self._get_active_asset(asset_id)
        news_items = self.provider_selector.fetch_news(asset)
        saved_items: list[NewsResponse] = []

        for item in news_items:
            if self._is_duplicate_news(asset.id, item.title, item.url, item.published_at):
                continue

            news = News(
                asset_id=asset.id,
                title=item.title,
                summary=item.summary,
                source=item.source,
                url=item.url,
                published_at=item.published_at,
            )
            created = self.news_repository.create(news)
            saved_items.append(NewsResponse.model_validate(created))

        self.db.commit()
        return saved_items

    def get_asset_news(self, asset_id: int) -> list[NewsResponse]:
        self._ensure_asset_exists(asset_id)
        news_items = self.news_repository.list_by_asset_id(asset_id)
        return [NewsResponse.model_validate(item) for item in news_items]

    def update_market_prices(self) -> dict[str, int]:
        assets = self._list_active_assets()
        updated = 0
        failed = 0

        for asset in assets:
            try:
                self.fetch_market_price(asset.id)
                updated += 1
            except Exception as exc:
                failed += 1
                logger.error("Failed to update market price for asset %s: %s", asset.symbol, exc)
                self.db.rollback()

        return {"updated": updated, "failed": failed, "total": len(assets)}

    def update_news_feed(self) -> dict[str, int]:
        assets = self._list_active_assets()
        saved = 0
        failed = 0

        for asset in assets:
            try:
                items = self.fetch_news(asset.id)
                saved += len(items)
            except Exception as exc:
                failed += 1
                logger.error("Failed to update news feed for asset %s: %s", asset.symbol, exc)
                self.db.rollback()

        deleted = self.delete_expired_news()
        return {"saved": saved, "failed": failed, "deleted": deleted, "total": len(assets)}

    def delete_expired_news(self) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=self.settings.news_expiration_days)
        deleted = self.news_repository.delete_expired(cutoff)
        self.db.commit()
        return deleted

    def _list_active_assets(self) -> list[Asset]:
        return [asset for asset in self.asset_repository.list_all() if asset.is_active]

    def _get_active_asset(self, asset_id: int) -> Asset:
        asset = self._ensure_asset_exists(asset_id)
        if not asset.is_active:
            raise ValidationError("Asset is not active")
        return asset

    def _ensure_asset_exists(self, asset_id: int) -> Asset:
        asset = self.asset_repository.get_by_id(asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")
        return asset

    def _is_duplicate_news(
        self,
        asset_id: int,
        title: str,
        url: str,
        published_at: datetime,
    ) -> bool:
        if self.news_repository.exists_by_url(url):
            return True
        return self.news_repository.exists_by_asset_title_published_at(
            asset_id,
            title,
            published_at,
        )
