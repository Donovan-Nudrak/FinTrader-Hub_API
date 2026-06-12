from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class PortfolioValuePoint(BaseModel):
    date: date
    value: float


class DrawdownResponse(BaseModel):
    portfolio_id: int
    maximum_drawdown: float | None = None
    current_drawdown: float | None = None
    value_series: list[PortfolioValuePoint] = Field(default_factory=list)
    insufficient_data: bool = False


class SharpeRatioResponse(BaseModel):
    portfolio_id: int
    sharpe_ratio: float | None = None
    risk_free_rate: float
    periods: int = 0
    insufficient_data: bool = False


class SortinoRatioResponse(BaseModel):
    portfolio_id: int
    sortino_ratio: float | None = None
    risk_free_rate: float
    periods: int = 0
    insufficient_data: bool = False


class AssetExposureItem(BaseModel):
    asset_id: int
    symbol: str
    value: float
    weight_pct: float


class GroupExposureItem(BaseModel):
    group: str
    value: float
    weight_pct: float


class ExposureResponse(BaseModel):
    portfolio_id: int
    total_value: float
    by_asset: list[AssetExposureItem] = Field(default_factory=list)
    by_asset_type: list[GroupExposureItem] = Field(default_factory=list)
    by_market: list[GroupExposureItem] = Field(default_factory=list)
    hhi: float
    assets_without_price: list[str] = Field(default_factory=list)


class CorrelationAssetItem(BaseModel):
    asset_id: int
    symbol: str


class CorrelationResponse(BaseModel):
    portfolio_id: int
    assets: list[CorrelationAssetItem] = Field(default_factory=list)
    matrix: list[list[float | None]] = Field(default_factory=list)
    insufficient_data: bool = False


class KellyCriterionResponse(BaseModel):
    fraction: float
    win_rate: float
    avg_win: float
    avg_loss: float
    payoff_ratio: float
    assumptions: str


class FixedRiskResponse(BaseModel):
    quantity: float
    risk_amount: float
    risk_per_unit: float
    assumptions: str


class PositionSizingRequest(BaseModel):
    entry_price: Decimal
    stop_loss: Decimal
    capital: Decimal
    risk_pct: Decimal = Field(description="Risk fraction, e.g. 0.02 for 2%")


class PositionSizingResponse(BaseModel):
    portfolio_id: int
    kelly: KellyCriterionResponse | None = None
    fixed_risk: FixedRiskResponse | None = None


class RiskReportResponse(BaseModel):
    portfolio_id: int
    drawdown: DrawdownResponse
    sharpe: SharpeRatioResponse
    sortino: SortinoRatioResponse
    exposure: ExposureResponse
    correlation: CorrelationResponse
