from datetime import datetime

from pydantic import BaseModel, Field


class CreatePortfolioRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    base_currency: str = Field(default="USD", min_length=3, max_length=3)


class UpdatePortfolioRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    base_currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None


class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None
    base_currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
