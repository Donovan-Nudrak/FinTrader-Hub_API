from typing import Annotated

from fastapi import APIRouter, Depends

from core.schemas import APIResponse
from modules.auth.dependencies import get_current_user
from modules.auth.models.user import User
from modules.risk.dependencies import get_risk_service
from modules.risk.schemas import (
    CorrelationResponse,
    DrawdownResponse,
    ExposureResponse,
    PositionSizingRequest,
    PositionSizingResponse,
    RiskReportResponse,
    SharpeRatioResponse,
    SortinoRatioResponse,
)
from modules.risk.services import RiskService

router = APIRouter(prefix="/portfolios/{portfolio_id}/risk", tags=["risk"])


@router.get("/drawdown", response_model=APIResponse[DrawdownResponse])
def get_drawdown(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    risk_service: Annotated[RiskService, Depends(get_risk_service)],
) -> APIResponse[DrawdownResponse]:
    drawdown = risk_service.calculate_drawdown(current_user.id, portfolio_id)
    return APIResponse(message="Drawdown calculated successfully", data=drawdown)


@router.get("/sharpe", response_model=APIResponse[SharpeRatioResponse])
def get_sharpe_ratio(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    risk_service: Annotated[RiskService, Depends(get_risk_service)],
) -> APIResponse[SharpeRatioResponse]:
    sharpe = risk_service.calculate_sharpe_ratio(current_user.id, portfolio_id)
    return APIResponse(message="Sharpe ratio calculated successfully", data=sharpe)


@router.get("/sortino", response_model=APIResponse[SortinoRatioResponse])
def get_sortino_ratio(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    risk_service: Annotated[RiskService, Depends(get_risk_service)],
) -> APIResponse[SortinoRatioResponse]:
    sortino = risk_service.calculate_sortino_ratio(current_user.id, portfolio_id)
    return APIResponse(message="Sortino ratio calculated successfully", data=sortino)


@router.get("/exposure", response_model=APIResponse[ExposureResponse])
def get_exposure(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    risk_service: Annotated[RiskService, Depends(get_risk_service)],
) -> APIResponse[ExposureResponse]:
    exposure = risk_service.calculate_exposure(current_user.id, portfolio_id)
    return APIResponse(message="Portfolio exposure calculated successfully", data=exposure)


@router.get("/correlation", response_model=APIResponse[CorrelationResponse])
def get_correlation(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    risk_service: Annotated[RiskService, Depends(get_risk_service)],
) -> APIResponse[CorrelationResponse]:
    correlation = risk_service.calculate_correlation(current_user.id, portfolio_id)
    return APIResponse(message="Correlation matrix calculated successfully", data=correlation)


@router.post("/position-sizing", response_model=APIResponse[PositionSizingResponse])
def get_position_sizing(
    portfolio_id: int,
    request: PositionSizingRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    risk_service: Annotated[RiskService, Depends(get_risk_service)],
) -> APIResponse[PositionSizingResponse]:
    sizing = risk_service.calculate_position_sizing(current_user.id, portfolio_id, request)
    return APIResponse(message="Position sizing calculated successfully", data=sizing)


@router.get("/report", response_model=APIResponse[RiskReportResponse])
def get_risk_report(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    risk_service: Annotated[RiskService, Depends(get_risk_service)],
) -> APIResponse[RiskReportResponse]:
    report = risk_service.generate_risk_report(current_user.id, portfolio_id)
    return APIResponse(message="Risk report generated successfully", data=report)
