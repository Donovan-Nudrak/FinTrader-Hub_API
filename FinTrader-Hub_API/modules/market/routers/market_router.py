from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.schemas import APIResponse
from modules.auth.dependencies import get_current_user
from modules.auth.models.user import User
from modules.market.dependencies import get_market_service
from modules.market.schemas import (
    FetchMarketPriceRequest,
    FetchNewsRequest,
    MarketPriceResponse,
    NewsResponse,
)
from modules.market.services import MarketService

router = APIRouter(prefix="/market", tags=["market"])


@router.post("/prices/fetch", response_model=APIResponse[MarketPriceResponse])
def fetch_market_price(
    request: FetchMarketPriceRequest,
    _current_user: Annotated[User, Depends(get_current_user)],
    market_service: Annotated[MarketService, Depends(get_market_service)],
) -> APIResponse[MarketPriceResponse]:
    price = market_service.fetch_market_price(request.asset_id)
    return APIResponse(message="Market price fetched successfully", data=price)


@router.get("/prices/{asset_id}/latest", response_model=APIResponse[MarketPriceResponse])
def get_asset_price(
    asset_id: int,
    market_service: Annotated[MarketService, Depends(get_market_service)],
) -> APIResponse[MarketPriceResponse]:
    price = market_service.get_asset_price(asset_id)
    return APIResponse(message="Latest market price retrieved successfully", data=price)


@router.get("/prices/{asset_id}/historical", response_model=APIResponse[list[MarketPriceResponse]])
def get_historical_prices(
    asset_id: int,
    market_service: Annotated[MarketService, Depends(get_market_service)],
    from_date: Annotated[datetime, Query()],
    to_date: Annotated[datetime, Query()],
) -> APIResponse[list[MarketPriceResponse]]:
    prices = market_service.get_historical_prices(asset_id, from_date=from_date, to_date=to_date)
    return APIResponse(message="Historical prices retrieved successfully", data=prices)


@router.post("/news/fetch", response_model=APIResponse[list[NewsResponse]])
def fetch_news(
    request: FetchNewsRequest,
    _current_user: Annotated[User, Depends(get_current_user)],
    market_service: Annotated[MarketService, Depends(get_market_service)],
) -> APIResponse[list[NewsResponse]]:
    news_items = market_service.fetch_news(request.asset_id)
    return APIResponse(message="News fetched successfully", data=news_items)


@router.get("/news/{asset_id}", response_model=APIResponse[list[NewsResponse]])
def get_asset_news(
    asset_id: int,
    market_service: Annotated[MarketService, Depends(get_market_service)],
) -> APIResponse[list[NewsResponse]]:
    news_items = market_service.get_asset_news(asset_id)
    return APIResponse(message="Asset news retrieved successfully", data=news_items)
