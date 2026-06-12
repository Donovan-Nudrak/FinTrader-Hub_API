from typing import Annotated

from fastapi import APIRouter, Depends, status

from core.schemas import APIResponse
from modules.auth.dependencies import get_current_user
from modules.auth.models.user import User
from modules.trade.dependencies import get_trade_service
from modules.trade.schemas import RegisterTradeRequest, TradeResponse, UpdateTradeRequest
from modules.trade.services import TradeService

router = APIRouter(prefix="/portfolios/{portfolio_id}/trades", tags=["trades"])


@router.post(
    "",
    response_model=APIResponse[TradeResponse],
    status_code=status.HTTP_201_CREATED,
)
def register_trade(
    portfolio_id: int,
    request: RegisterTradeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    trade_service: Annotated[TradeService, Depends(get_trade_service)],
) -> APIResponse[TradeResponse]:
    trade = trade_service.register_trade(current_user.id, portfolio_id, request)
    return APIResponse(message="Trade registered successfully", data=trade)


@router.get("", response_model=APIResponse[list[TradeResponse]])
def list_trades(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    trade_service: Annotated[TradeService, Depends(get_trade_service)],
) -> APIResponse[list[TradeResponse]]:
    trades = trade_service.list_trades(current_user.id, portfolio_id)
    return APIResponse(message="Trades retrieved successfully", data=trades)


@router.get("/{trade_id}", response_model=APIResponse[TradeResponse])
def get_trade(
    portfolio_id: int,
    trade_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    trade_service: Annotated[TradeService, Depends(get_trade_service)],
) -> APIResponse[TradeResponse]:
    trade = trade_service.get_trade(current_user.id, portfolio_id, trade_id)
    return APIResponse(message="Trade retrieved successfully", data=trade)


@router.put("/{trade_id}", response_model=APIResponse[TradeResponse])
def update_trade(
    portfolio_id: int,
    trade_id: int,
    request: UpdateTradeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    trade_service: Annotated[TradeService, Depends(get_trade_service)],
) -> APIResponse[TradeResponse]:
    trade = trade_service.update_trade(current_user.id, portfolio_id, trade_id, request)
    return APIResponse(message="Trade updated successfully", data=trade)


@router.delete("/{trade_id}", response_model=APIResponse[None])
def delete_trade(
    portfolio_id: int,
    trade_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    trade_service: Annotated[TradeService, Depends(get_trade_service)],
) -> APIResponse[None]:
    trade_service.delete_trade(current_user.id, portfolio_id, trade_id)
    return APIResponse(message="Trade deleted successfully", data=None)
