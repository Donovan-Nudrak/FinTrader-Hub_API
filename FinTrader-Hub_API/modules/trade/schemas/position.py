from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from core.enums import PositionStatus, PositionType


class PositionResponse(BaseModel):
    id: int
    portfolio_id: int
    asset_id: int
    position_type: PositionType
    quantity: Decimal
    average_price: Decimal
    total_cost: Decimal
    status: PositionStatus
    opened_at: datetime
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecalculatePositionRequest(BaseModel):
    asset_id: int
