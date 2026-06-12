from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.enums import AlertCondition, AlertType
from infrastructure.database.base import BaseModel


class Alert(BaseModel):
    __tablename__ = "alerts"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    portfolio_id: Mapped[int | None] = mapped_column(
        ForeignKey("portfolios.id"),
        nullable=True,
        index=True,
    )
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType, name="alert_type"), nullable=False)
    condition: Mapped[AlertCondition] = mapped_column(
        Enum(AlertCondition, name="alert_condition"),
        nullable=False,
    )
    threshold: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["AlertEvent"]] = relationship(
        "AlertEvent",
        back_populates="alert",
        cascade="all, delete-orphan",
    )
