from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from core.enums import AlertCondition, AlertType


class DashboardMoverItem(BaseModel):
    asset_id: int
    symbol: str
    portfolio_id: int | None = None
    change_pct: Decimal
    current_price: Decimal
    previous_price: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None


class DashboardSummaryResponse(BaseModel):
    portfolio_total_value: Decimal | None = None
    total_unrealized_pnl: Decimal | None = None
    total_unrealized_pnl_pct: Decimal | None = None
    total_realized_pnl: Decimal | None = None
    open_positions_count: int = 0
    active_alerts_count: int = 0
    top_gainers: list[DashboardMoverItem] = Field(default_factory=list)
    top_losers: list[DashboardMoverItem] = Field(default_factory=list)
    current_drawdown: Decimal | None = None
    last_price_update: datetime | None = None


class PortfolioSnapshotItem(BaseModel):
    portfolio_id: int
    portfolio_name: str
    current_value: Decimal | None = None
    total_cost: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None
    open_positions_count: int = 0
    asset_type_allocation: list[dict[str, Decimal | str]] = Field(default_factory=list)


class PortfolioSnapshotResponse(BaseModel):
    portfolios: list[PortfolioSnapshotItem] = Field(default_factory=list)


class DailyPerformanceAssetItem(BaseModel):
    asset_id: int
    symbol: str
    change_value: Decimal
    change_pct: Decimal


class DailyPerformanceResponse(BaseModel):
    start_of_day_value: Decimal | None = None
    current_value: Decimal | None = None
    change_value: Decimal | None = None
    change_pct: Decimal | None = None
    top_gainer: DailyPerformanceAssetItem | None = None
    top_loser: DailyPerformanceAssetItem | None = None
    trades_executed_today: int = 0


class ActiveAlertItem(BaseModel):
    alert_id: int
    alert_type: AlertType
    condition: AlertCondition
    threshold: Decimal
    portfolio_id: int | None = None
    asset_id: int | None = None
    last_triggered_at: datetime | None = None
    total_triggers: int = 0


class ActiveAlertsResponse(BaseModel):
    alerts: list[ActiveAlertItem] = Field(default_factory=list)
    total_active: int = 0


class TopMoversResponse(BaseModel):
    top_gainers: list[DashboardMoverItem] = Field(default_factory=list)
    top_losers: list[DashboardMoverItem] = Field(default_factory=list)
