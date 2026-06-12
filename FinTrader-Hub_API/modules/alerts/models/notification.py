from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.enums import NotificationChannel, NotificationStatus
from infrastructure.database.base import BaseModel


class Notification(BaseModel):
    __tablename__ = "notifications"

    alert_event_id: Mapped[int] = mapped_column(
        ForeignKey("alert_events.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel"),
        nullable=False,
        default=NotificationChannel.EMAIL,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        nullable=False,
        default=NotificationStatus.PENDING,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    alert_event: Mapped["AlertEvent"] = relationship("AlertEvent", back_populates="notification")
