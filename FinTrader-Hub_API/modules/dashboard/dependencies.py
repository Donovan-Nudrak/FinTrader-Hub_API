from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.dependencies import get_db
from modules.dashboard.services import DashboardService


def get_dashboard_service(db: Annotated[Session, Depends(get_db)]) -> DashboardService:
    return DashboardService(db)
