from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from core.enums import PositionStatus, PositionType, TradeType
from core.exceptions import ValidationError
from modules.trade.models.trade import Trade
from modules.trade.services.position_engine import replay_trades


def _trade(
    trade_id: int,
    trade_type: TradeType,
    quantity: str,
    price: str,
    *,
    offset_minutes: int = 0,
) -> Trade:
    return Trade(
        id=trade_id,
        portfolio_id=1,
        asset_id=1,
        trade_type=trade_type,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fees=Decimal("0"),
        executed_at=datetime.now(UTC).replace(microsecond=0) + timedelta(minutes=offset_minutes),
    )


def test_replay_weighted_average() -> None:
    trades = [
        _trade(1, TradeType.BUY, "1", "100", offset_minutes=0),
        _trade(2, TradeType.BUY, "1", "110", offset_minutes=1),
    ]
    result = replay_trades(trades)

    assert result is not None
    assert result.position_type == PositionType.LONG
    assert result.quantity == Decimal("2")
    assert result.average_price == Decimal("105")
    assert result.total_cost == Decimal("210")


def test_replay_sell_without_position_raises() -> None:
    with pytest.raises(ValidationError):
        replay_trades([_trade(1, TradeType.SELL, "1", "100")])
