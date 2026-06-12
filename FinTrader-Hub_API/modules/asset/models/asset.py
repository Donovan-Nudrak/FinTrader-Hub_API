from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import AssetType, MarketType
from infrastructure.database.base import BaseModel


class Asset(BaseModel):
    __tablename__ = "assets"

    symbol: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    market: Mapped[MarketType] = mapped_column(Enum(MarketType, name="market_type"), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType, name="asset_type"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
