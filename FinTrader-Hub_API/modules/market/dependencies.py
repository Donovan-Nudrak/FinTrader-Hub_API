from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.dependencies import get_db
from modules.market.services import MarketService


def get_market_service(db: Annotated[Session, Depends(get_db)]) -> MarketService:
    return MarketService(db)
