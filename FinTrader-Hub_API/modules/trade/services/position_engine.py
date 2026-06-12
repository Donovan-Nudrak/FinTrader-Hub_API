from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from core.enums import PositionStatus, PositionType, TradeType
from core.exceptions import ValidationError
from modules.trade.models.trade import Trade


@dataclass
class CalculatedPositionState:
    position_type: PositionType
    quantity: Decimal
    average_price: Decimal
    total_cost: Decimal
    status: PositionStatus
    opened_at: datetime
    closed_at: datetime | None


def replay_trades(trades: list[Trade]) -> CalculatedPositionState | None:
    if not trades:
        return None

    position_type: PositionType | None = None
    quantity = Decimal("0")
    total_cost = Decimal("0")
    average_price = Decimal("0")
    status = PositionStatus.OPEN
    opened_at: datetime | None = None
    closed_at: datetime | None = None

    ordered_trades = sorted(trades, key=lambda trade: (trade.executed_at, trade.id))

    for trade in ordered_trades:
        trade_quantity = Decimal(str(trade.quantity))
        trade_price = Decimal(str(trade.price))

        if trade.trade_type == TradeType.BUY:
            if position_type is None or (status == PositionStatus.CLOSED and quantity == 0):
                position_type = PositionType.LONG
                status = PositionStatus.OPEN
                opened_at = trade.executed_at
                closed_at = None
                quantity = Decimal("0")
                total_cost = Decimal("0")
                average_price = Decimal("0")
            elif position_type != PositionType.LONG:
                raise ValidationError("Cannot BUY while a SHORT position is active")

            total_cost += trade_quantity * trade_price
            quantity += trade_quantity
            average_price = total_cost / quantity

        elif trade.trade_type == TradeType.SELL:
            if position_type != PositionType.LONG or quantity <= 0 or status != PositionStatus.OPEN:
                raise ValidationError("No open LONG position available for SELL")

            if trade_quantity > quantity:
                raise ValidationError("SELL quantity exceeds available position quantity")

            total_cost -= trade_quantity * average_price
            quantity -= trade_quantity

            if quantity == 0:
                status = PositionStatus.CLOSED
                closed_at = trade.executed_at
                total_cost = Decimal("0")
                average_price = Decimal("0")

        elif trade.trade_type == TradeType.SHORT:
            if position_type is None or (status == PositionStatus.CLOSED and quantity == 0):
                position_type = PositionType.SHORT
                status = PositionStatus.OPEN
                opened_at = trade.executed_at
                closed_at = None
                quantity = Decimal("0")
                total_cost = Decimal("0")
                average_price = Decimal("0")
            elif position_type != PositionType.SHORT:
                raise ValidationError("Cannot SHORT while a LONG position is active")

            total_cost += trade_quantity * trade_price
            quantity += trade_quantity
            average_price = total_cost / quantity

        elif trade.trade_type == TradeType.COVER:
            if position_type != PositionType.SHORT or quantity <= 0 or status != PositionStatus.OPEN:
                raise ValidationError("No open SHORT position available for COVER")

            if trade_quantity > quantity:
                raise ValidationError("COVER quantity exceeds available position quantity")

            total_cost -= trade_quantity * average_price
            quantity -= trade_quantity

            if quantity == 0:
                status = PositionStatus.CLOSED
                closed_at = trade.executed_at
                total_cost = Decimal("0")
                average_price = Decimal("0")

    if position_type is None or opened_at is None:
        return None

    return CalculatedPositionState(
        position_type=position_type,
        quantity=quantity,
        average_price=average_price,
        total_cost=total_cost,
        status=status,
        opened_at=opened_at,
        closed_at=closed_at,
    )
