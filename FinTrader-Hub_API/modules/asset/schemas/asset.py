from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from core.enums import AssetType, MarketType


class CreateAssetRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=50)
    external_id: str | None = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    market: MarketType
    asset_type: AssetType
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("symbol", "name")
    @classmethod
    def validate_non_empty_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be empty or whitespace")
        return normalized

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3:
            raise ValueError("Currency must be a 3-letter code")
        return normalized


class UpdateAssetRequest(BaseModel):
    symbol: str | None = Field(default=None, min_length=1, max_length=50)
    external_id: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    market: MarketType | None = None
    asset_type: AssetType | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None


class AssetResponse(BaseModel):
    id: int
    symbol: str
    external_id: str | None
    name: str
    market: MarketType
    asset_type: AssetType
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
