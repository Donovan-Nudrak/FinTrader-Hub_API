from typing import Annotated

from fastapi import APIRouter, Depends, status

from core.schemas import APIResponse
from modules.auth.dependencies import get_current_user
from modules.auth.models.user import User
from modules.portfolio.dependencies import get_portfolio_service
from modules.portfolio.schemas import (
    CreatePortfolioRequest,
    PortfolioResponse,
    UpdatePortfolioRequest,
)
from modules.portfolio.services import PortfolioService

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post(
    "",
    response_model=APIResponse[PortfolioResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_portfolio(
    request: CreatePortfolioRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    portfolio_service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> APIResponse[PortfolioResponse]:
    portfolio = portfolio_service.create_portfolio(current_user.id, request)
    return APIResponse(message="Portfolio created successfully", data=portfolio)


@router.get("", response_model=APIResponse[list[PortfolioResponse]])
def list_portfolios(
    current_user: Annotated[User, Depends(get_current_user)],
    portfolio_service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> APIResponse[list[PortfolioResponse]]:
    portfolios = portfolio_service.list_portfolios(current_user.id)
    return APIResponse(message="Portfolios retrieved successfully", data=portfolios)


@router.get("/{portfolio_id}", response_model=APIResponse[PortfolioResponse])
def get_portfolio(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    portfolio_service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> APIResponse[PortfolioResponse]:
    portfolio = portfolio_service.get_portfolio(current_user.id, portfolio_id)
    return APIResponse(message="Portfolio retrieved successfully", data=portfolio)


@router.put("/{portfolio_id}", response_model=APIResponse[PortfolioResponse])
def update_portfolio(
    portfolio_id: int,
    request: UpdatePortfolioRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    portfolio_service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> APIResponse[PortfolioResponse]:
    portfolio = portfolio_service.update_portfolio(current_user.id, portfolio_id, request)
    return APIResponse(message="Portfolio updated successfully", data=portfolio)


@router.delete("/{portfolio_id}", response_model=APIResponse[None])
def delete_portfolio(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    portfolio_service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> APIResponse[None]:
    portfolio_service.delete_portfolio(current_user.id, portfolio_id)
    return APIResponse(message="Portfolio deleted successfully", data=None)
