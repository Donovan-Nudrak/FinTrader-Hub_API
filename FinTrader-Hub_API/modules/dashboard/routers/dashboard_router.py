from typing import Annotated

from fastapi import APIRouter, Depends

from core.schemas import APIResponse
from modules.auth.dependencies import get_current_user
from modules.auth.models.user import User
from modules.dashboard.dependencies import get_dashboard_service
from modules.dashboard.schemas import (
    ActiveAlertsResponse,
    DailyPerformanceResponse,
    DashboardSummaryResponse,
    PortfolioSnapshotResponse,
    TopMoversResponse,
)
from modules.dashboard.services import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=APIResponse[DashboardSummaryResponse])
def get_dashboard_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> APIResponse[DashboardSummaryResponse]:
    summary = dashboard_service.get_dashboard_summary(current_user.id)
    return APIResponse(message="Dashboard summary generated successfully", data=summary)


@router.get("/portfolio-snapshot", response_model=APIResponse[PortfolioSnapshotResponse])
def get_portfolio_snapshot(
    current_user: Annotated[User, Depends(get_current_user)],
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> APIResponse[PortfolioSnapshotResponse]:
    snapshot = dashboard_service.get_portfolio_snapshot(current_user.id)
    return APIResponse(message="Portfolio snapshot generated successfully", data=snapshot)


@router.get("/daily-performance", response_model=APIResponse[DailyPerformanceResponse])
def get_daily_performance(
    current_user: Annotated[User, Depends(get_current_user)],
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> APIResponse[DailyPerformanceResponse]:
    performance = dashboard_service.get_daily_performance(current_user.id)
    return APIResponse(message="Daily performance generated successfully", data=performance)


@router.get("/alerts", response_model=APIResponse[ActiveAlertsResponse])
def get_active_alerts(
    current_user: Annotated[User, Depends(get_current_user)],
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> APIResponse[ActiveAlertsResponse]:
    alerts = dashboard_service.get_active_alerts(current_user.id)
    return APIResponse(message="Active alerts retrieved successfully", data=alerts)


@router.get("/top-movers", response_model=APIResponse[TopMoversResponse])
def get_top_movers(
    current_user: Annotated[User, Depends(get_current_user)],
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> APIResponse[TopMoversResponse]:
    movers = dashboard_service.get_top_movers(current_user.id)
    return APIResponse(message="Top movers retrieved successfully", data=movers)
