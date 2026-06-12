from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.market.models.market_price import MarketPrice


class MarketPriceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, market_price: MarketPrice) -> MarketPrice:
        self.db.add(market_price)
        self.db.flush()
        self.db.refresh(market_price)
        return market_price

    def get_latest_by_asset_id(self, asset_id: int) -> MarketPrice | None:
        statement = (
            select(MarketPrice)
            .where(MarketPrice.asset_id == asset_id)
            .order_by(MarketPrice.timestamp.desc(), MarketPrice.id.desc())
            .limit(1)
        )
        return self.db.scalar(statement)

    def list_by_asset_and_range(
        self,
        asset_id: int,
        *,
        from_date: datetime,
        to_date: datetime,
    ) -> list[MarketPrice]:
        statement = (
            select(MarketPrice)
            .where(
                MarketPrice.asset_id == asset_id,
                MarketPrice.timestamp >= from_date,
                MarketPrice.timestamp <= to_date,
            )
            .order_by(MarketPrice.timestamp.asc())
        )
        return list(self.db.scalars(statement).all())
