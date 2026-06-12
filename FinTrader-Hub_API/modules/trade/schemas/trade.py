from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from core.enums import TradeType


class RegisterTradeRequest(BaseModel):
    asset_id: int = Field(gt=0)
    trade_type: TradeType
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    fees: Decimal = Field(ge=0, default=Decimal("0"))
    executed_at: datetime
    notes: str | None = None


class UpdateTradeRequest(BaseModel):
    asset_id: int | None = None
    trade_type: TradeType | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    fees: Decimal | None = Field(default=None, ge=0)
    executed_at: datetime | None = None
    notes: str | None = None


class TradeResponse(BaseModel):
    id: int
    portfolio_id: int
    position_id: int | None
    asset_id: int
    trade_type: TradeType
    quantity: Decimal
    price: Decimal
    fees: Decimal
    executed_at: datetime
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
