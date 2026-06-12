from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.enums import ApiKeyProvider
from infrastructure.database.base import BaseModel


class ApiKey(BaseModel):
    __tablename__ = "api_keys"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    provider: Mapped[ApiKeyProvider] = mapped_column(
        Enum(ApiKeyProvider, name="api_key_provider"),
        nullable=False,
    )
    key_value: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="api_keys")
