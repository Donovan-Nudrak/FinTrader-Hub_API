from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.dependencies import get_db
from modules.trade.services import PositionService, TradeService


def get_trade_service(db: Annotated[Session, Depends(get_db)]) -> TradeService:
    return TradeService(db)


def get_position_service(db: Annotated[Session, Depends(get_db)]) -> PositionService:
    return PositionService(db)
