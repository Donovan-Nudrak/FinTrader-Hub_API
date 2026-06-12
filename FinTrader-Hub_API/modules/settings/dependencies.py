from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.dependencies import get_db
from modules.settings.services import SettingsService


def get_settings_service(db: Annotated[Session, Depends(get_db)]) -> SettingsService:
    return SettingsService(db)
