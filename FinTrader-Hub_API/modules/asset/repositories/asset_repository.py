from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from modules.asset.models.asset import Asset


class AssetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, asset: Asset) -> Asset:
        self.db.add(asset)
        self.db.flush()
        self.db.refresh(asset)
        return asset

    def get_by_id(self, asset_id: int) -> Asset | None:
        return self.db.get(Asset, asset_id)

    def get_by_symbol(self, symbol: str) -> Asset | None:
        statement = select(Asset).where(Asset.symbol == symbol)
        return self.db.scalar(statement)

    def symbol_exists(self, symbol: str, *, exclude_id: int | None = None) -> bool:
        statement = select(Asset.id).where(Asset.symbol == symbol)
        if exclude_id is not None:
            statement = statement.where(Asset.id != exclude_id)
        return self.db.scalar(statement) is not None

    def update(self, asset: Asset) -> Asset:
        self.db.add(asset)
        self.db.flush()
        self.db.refresh(asset)
        return asset

    def list_all(self) -> list[Asset]:
        statement = select(Asset).order_by(Asset.symbol.asc())
        return list(self.db.scalars(statement).all())

    def search(self, *, symbol: str | None = None, name: str | None = None) -> list[Asset]:
        statement = select(Asset)
        filters = []

        if symbol:
            filters.append(Asset.symbol.ilike(f"%{symbol.upper()}%"))

        if name:
            filters.append(Asset.name.ilike(f"%{name}%"))

        if filters:
            statement = statement.where(or_(*filters) if len(filters) > 1 else filters[0])

        statement = statement.order_by(Asset.symbol.asc())
        return list(self.db.scalars(statement).all())
