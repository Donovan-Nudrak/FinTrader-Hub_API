from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.dependencies import get_db
from modules.alerts.services import AlertService


def get_alert_service(db: Annotated[Session, Depends(get_db)]) -> AlertService:
    return AlertService(db)
