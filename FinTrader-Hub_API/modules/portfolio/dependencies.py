from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.dependencies import get_db
from modules.portfolio.services import AnalyticsService, PortfolioService


def get_portfolio_service(db: Annotated[Session, Depends(get_db)]) -> PortfolioService:
    return PortfolioService(db)


def get_analytics_service(db: Annotated[Session, Depends(get_db)]) -> AnalyticsService:
    return AnalyticsService(db)
