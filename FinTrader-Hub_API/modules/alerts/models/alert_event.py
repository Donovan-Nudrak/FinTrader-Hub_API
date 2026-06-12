from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import BaseModel


class AlertEvent(BaseModel):
    __tablename__ = "alert_events"

    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), nullable=False, index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    trigger_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    alert: Mapped["Alert"] = relationship("Alert", back_populates="events")
    notification: Mapped["Notification | None"] = relationship(
        "Notification",
        back_populates="alert_event",
        uselist=False,
        cascade="all, delete-orphan",
    )
