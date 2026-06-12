from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str | None = None
    data: T | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    code: str
    request_id: str | None = None
    details: dict | list | None = None


class PaginationMeta(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str | None = None
    data: list[T] = Field(default_factory=list)
    meta: PaginationMeta
