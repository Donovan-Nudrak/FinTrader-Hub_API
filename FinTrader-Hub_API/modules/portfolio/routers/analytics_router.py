from typing import Annotated

from fastapi import APIRouter, Depends

from core.schemas import APIResponse
from modules.auth.dependencies import get_current_user
from modules.auth.models.user import User
from modules.portfolio.dependencies import get_analytics_service
from modules.portfolio.schemas.analytics import (
    AssetAllocationResponse,
    PortfolioPerformanceResponse,
    PortfolioValueResponse,
    PositionPnLResponse,
)
from modules.portfolio.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/portfolios/{portfolio_id}", tags=["portfolio-analytics"])


@router.get("/analytics/value", response_model=APIResponse[PortfolioValueResponse])
def get_portfolio_value(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> APIResponse[PortfolioValueResponse]:
    value = analytics_service.calculate_portfolio_value(current_user.id, portfolio_id)
    return APIResponse(message="Portfolio value calculated successfully", data=value)


@router.get("/analytics/allocation", response_model=APIResponse[AssetAllocationResponse])
def get_asset_allocation(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> APIResponse[AssetAllocationResponse]:
    allocation = analytics_service.calculate_asset_allocation(current_user.id, portfolio_id)
    return APIResponse(message="Asset allocation calculated successfully", data=allocation)


@router.get("/analytics/performance", response_model=APIResponse[PortfolioPerformanceResponse])
def get_portfolio_performance(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> APIResponse[PortfolioPerformanceResponse]:
    performance = analytics_service.calculate_portfolio_performance(current_user.id, portfolio_id)
    return APIResponse(message="Portfolio performance calculated successfully", data=performance)


@router.get("/positions/{position_id}/pnl", response_model=APIResponse[PositionPnLResponse])
def get_position_pnl(
    portfolio_id: int,
    position_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> APIResponse[PositionPnLResponse]:
    pnl = analytics_service.calculate_position_pnl(current_user.id, portfolio_id, position_id)
    return APIResponse(message="Position PnL calculated successfully", data=pnl)
