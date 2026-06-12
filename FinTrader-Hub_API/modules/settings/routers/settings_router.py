from typing import Annotated

from fastapi import APIRouter, Depends, status

from core.schemas import APIResponse
from modules.auth.dependencies import get_current_user
from modules.auth.models.user import User
from modules.settings.dependencies import get_settings_service
from modules.settings.schemas import (
    ApiKeyResponse,
    CreateApiKeyRequest,
    UpdateApiKeyRequest,
    UpdateUserSettingRequest,
    UserSettingResponse,
)
from modules.settings.services import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=APIResponse[UserSettingResponse])
def get_user_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> APIResponse[UserSettingResponse]:
    settings = settings_service.get_user_settings(current_user.id)
    return APIResponse(message="User settings retrieved successfully", data=settings)


@router.put("", response_model=APIResponse[UserSettingResponse])
def update_user_settings(
    request: UpdateUserSettingRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> APIResponse[UserSettingResponse]:
    settings = settings_service.update_user_settings(current_user.id, request)
    return APIResponse(message="User settings updated successfully", data=settings)


@router.get("/api-keys", response_model=APIResponse[list[ApiKeyResponse]])
def list_api_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> APIResponse[list[ApiKeyResponse]]:
    api_keys = settings_service.list_api_keys(current_user.id)
    return APIResponse(message="API keys retrieved successfully", data=api_keys)


@router.post(
    "/api-keys",
    response_model=APIResponse[ApiKeyResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    request: CreateApiKeyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> APIResponse[ApiKeyResponse]:
    api_key = settings_service.create_api_key(current_user.id, request)
    return APIResponse(message="API key created successfully", data=api_key)


@router.put("/api-keys/{api_key_id}", response_model=APIResponse[ApiKeyResponse])
def update_api_key(
    api_key_id: int,
    request: UpdateApiKeyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> APIResponse[ApiKeyResponse]:
    api_key = settings_service.update_api_key(current_user.id, api_key_id, request)
    return APIResponse(message="API key updated successfully", data=api_key)


@router.delete("/api-keys/{api_key_id}", response_model=APIResponse[None])
def delete_api_key(
    api_key_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> APIResponse[None]:
    settings_service.delete_api_key(current_user.id, api_key_id)
    return APIResponse(message="API key deleted successfully", data=None)
