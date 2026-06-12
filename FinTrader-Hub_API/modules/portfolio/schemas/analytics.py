from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from core.enums import AssetType, MarketType, PositionStatus, PositionType


class AssetWithoutPriceItem(BaseModel):
    asset_id: int
    symbol: str


class PositionValueItem(BaseModel):
    position_id: int
    asset_id: int
    symbol: str
    quantity: Decimal
    average_price: Decimal
    latest_price: Decimal
    current_value: Decimal


class PortfolioValueResponse(BaseModel):
    portfolio_id: int
    portfolio_value: Decimal
    total_cost: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal
    positions: list[PositionValueItem] = Field(default_factory=list)
    assets_without_price: list[AssetWithoutPriceItem] = Field(default_factory=list)


class PositionPnLResponse(BaseModel):
    position_id: int
    asset_id: int
    symbol: str
    status: PositionStatus
    position_type: PositionType
    quantity: Decimal
    average_price: Decimal
    latest_price: Decimal | None = None
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal
    realized_pnl: Decimal | None = None


class AllocationItem(BaseModel):
    asset_id: int
    symbol: str
    asset_type: AssetType
    market: MarketType
    value: Decimal
    weight_pct: Decimal


class AllocationGroupItem(BaseModel):
    group: str
    value: Decimal
    weight_pct: Decimal


class AssetAllocationResponse(BaseModel):
    portfolio_id: int
    total_value: Decimal
    by_asset: list[AllocationItem] = Field(default_factory=list)
    by_asset_type: list[AllocationGroupItem] = Field(default_factory=list)
    by_market: list[AllocationGroupItem] = Field(default_factory=list)
    assets_without_price: list[AssetWithoutPriceItem] = Field(default_factory=list)


class PortfolioPerformanceResponse(BaseModel):
    portfolio_id: int
    total_invested: Decimal
    total_current_value: Decimal
    total_realized_pnl: Decimal
    total_unrealized_pnl: Decimal
    total_pnl: Decimal
    total_return_pct: Decimal
    assets_without_price: list[AssetWithoutPriceItem] = Field(default_factory=list)
