from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class FetchMarketPriceRequest(BaseModel):
    asset_id: int


class HistoricalPricesQuery(BaseModel):
    from_date: datetime
    to_date: datetime


class MarketPriceResponse(BaseModel):
    id: int
    asset_id: int
    price: Decimal
    source: str
    timestamp: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class FetchNewsRequest(BaseModel):
    asset_id: int


class NewsResponse(BaseModel):
    id: int
    asset_id: int
    title: str
    summary: str | None
    source: str
    url: str
    published_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MarketTaskResultResponse(BaseModel):
    updated: int | None = None
    saved: int | None = None
    failed: int = 0
    deleted: int | None = None
    total: int = 0
