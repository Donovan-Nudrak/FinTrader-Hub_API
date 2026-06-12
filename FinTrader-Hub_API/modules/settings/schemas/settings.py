from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from core.enums import ApiKeyProvider


class UserSettingResponse(BaseModel):
    id: int
    user_id: int
    base_currency: str
    timezone: str
    alert_email: EmailStr | None = None
    dashboard_refresh_interval: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdateUserSettingRequest(BaseModel):
    base_currency: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    alert_email: EmailStr | None = None
    dashboard_refresh_interval: int | None = Field(default=None, ge=30)


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    provider: ApiKeyProvider
    key_value: str = Field(min_length=1)
    is_active: bool = True


class UpdateApiKeyRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    key_value: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class ApiKeyResponse(BaseModel):
    id: int
    user_id: int
    name: str
    provider: ApiKeyProvider
    masked_key_value: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime
