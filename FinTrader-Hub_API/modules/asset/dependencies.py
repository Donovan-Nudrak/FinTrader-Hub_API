from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from core.dependencies import get_db
from modules.asset.services import AssetService


def get_asset_service(db: Annotated[Session, Depends(get_db)]) -> AssetService:
    return AssetService(db)
