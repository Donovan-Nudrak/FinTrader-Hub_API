from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import BaseModel


class UserSetting(BaseModel):
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    alert_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dashboard_refresh_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=300)

    user: Mapped["User"] = relationship("User", back_populates="settings")
