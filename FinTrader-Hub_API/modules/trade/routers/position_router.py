from typing import Annotated

from fastapi import APIRouter, Depends

from core.schemas import APIResponse
from modules.auth.dependencies import get_current_user
from modules.auth.models.user import User
from modules.trade.dependencies import get_position_service
from modules.trade.schemas import PositionResponse, RecalculatePositionRequest
from modules.trade.services import PositionService

router = APIRouter(prefix="/portfolios/{portfolio_id}/positions", tags=["positions"])


@router.get("", response_model=APIResponse[list[PositionResponse]])
def list_portfolio_positions(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    position_service: Annotated[PositionService, Depends(get_position_service)],
) -> APIResponse[list[PositionResponse]]:
    positions = position_service.list_portfolio_positions(current_user.id, portfolio_id)
    return APIResponse(message="Positions retrieved successfully", data=positions)


@router.post("/recalculate", response_model=APIResponse[PositionResponse | None])
def recalculate_position(
    portfolio_id: int,
    request: RecalculatePositionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    position_service: Annotated[PositionService, Depends(get_position_service)],
) -> APIResponse[PositionResponse | None]:
    position = position_service.recalculate_position_for_user(
        current_user.id,
        portfolio_id,
        request.asset_id,
    )
    return APIResponse(message="Position recalculated successfully", data=position)


@router.get("/{position_id}", response_model=APIResponse[PositionResponse])
def get_position(
    portfolio_id: int,
    position_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    position_service: Annotated[PositionService, Depends(get_position_service)],
) -> APIResponse[PositionResponse]:
    position = position_service.get_position(current_user.id, portfolio_id, position_id)
    return APIResponse(message="Position retrieved successfully", data=position)
