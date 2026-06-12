from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from core.schemas import APIResponse
from modules.auth.dependencies import get_current_user
from modules.auth.models.user import User
from modules.asset.dependencies import get_asset_service
from modules.asset.schemas import AssetResponse, CreateAssetRequest, UpdateAssetRequest
from modules.asset.services import AssetService

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post(
    "",
    response_model=APIResponse[AssetResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_asset(
    request: CreateAssetRequest,
    _current_user: Annotated[User, Depends(get_current_user)],
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
) -> APIResponse[AssetResponse]:
    asset = asset_service.create_asset(request)
    return APIResponse(message="Asset created successfully", data=asset)


@router.put("/{asset_id}", response_model=APIResponse[AssetResponse])
def update_asset(
    asset_id: int,
    request: UpdateAssetRequest,
    _current_user: Annotated[User, Depends(get_current_user)],
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
) -> APIResponse[AssetResponse]:
    asset = asset_service.update_asset(asset_id, request)
    return APIResponse(message="Asset updated successfully", data=asset)


@router.get("/search", response_model=APIResponse[list[AssetResponse]])
def search_assets(
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
    symbol: Annotated[str | None, Query()] = None,
    name: Annotated[str | None, Query()] = None,
) -> APIResponse[list[AssetResponse]]:
    assets = asset_service.search_assets(symbol=symbol, name=name)
    return APIResponse(message="Assets found successfully", data=assets)


@router.get("", response_model=APIResponse[list[AssetResponse]])
def list_assets(
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
) -> APIResponse[list[AssetResponse]]:
    assets = asset_service.list_assets()
    return APIResponse(message="Assets retrieved successfully", data=assets)
