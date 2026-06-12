from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.enums import PositionStatus, PositionType
from infrastructure.database.base import BaseModel


class Position(BaseModel):
    __tablename__ = "positions"

    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)
    position_type: Mapped[PositionType] = mapped_column(
        Enum(PositionType, name="position_type"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    average_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    status: Mapped[PositionStatus] = mapped_column(
        Enum(PositionStatus, name="position_status"),
        nullable=False,
        default=PositionStatus.OPEN,
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="position")
