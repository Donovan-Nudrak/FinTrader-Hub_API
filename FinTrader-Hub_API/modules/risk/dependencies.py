from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.dependencies import get_db
from modules.risk.services import RiskService


def get_risk_service(db: Annotated[Session, Depends(get_db)]) -> RiskService:
    return RiskService(db)
