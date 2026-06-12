from datetime import UTC, datetime
from decimal import Decimal

from core.enums import TradeType
from modules.portfolio.services.analytics_service import (
    calculate_realized_pnl,
    calculate_total_invested,
    calculate_unrealized_pnl,
)
from modules.trade.models.trade import Trade


def _trade(trade_type: TradeType, quantity: str, price: str, trade_id: int = 1) -> Trade:
    return Trade(
        id=trade_id,
        portfolio_id=1,
        asset_id=1,
        trade_type=trade_type,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fees=Decimal("0"),
        executed_at=datetime(2026, 1, trade_id, tzinfo=UTC),
    )


def test_calculate_unrealized_pnl_gain() -> None:
    pnl = calculate_unrealized_pnl(Decimal("2"), Decimal("100"), Decimal("120"))
    assert pnl == Decimal("40")


def test_calculate_unrealized_pnl_loss() -> None:
    pnl = calculate_unrealized_pnl(Decimal("2"), Decimal("100"), Decimal("80"))
    assert pnl == Decimal("-40")


def test_calculate_realized_pnl_closed_long() -> None:
    trades = [
        _trade(TradeType.BUY, "1", "100", 1),
        _trade(TradeType.SELL, "1", "120", 2),
    ]
    assert calculate_realized_pnl(trades) == Decimal("20")


def test_calculate_realized_pnl_closed_short() -> None:
    trades = [
        _trade(TradeType.SHORT, "2", "50", 1),
        _trade(TradeType.COVER, "2", "45", 2),
    ]
    assert calculate_realized_pnl(trades) == Decimal("10")


def test_calculate_total_invested_from_entry_trades() -> None:
    trades = [
        _trade(TradeType.BUY, "1", "100", 1),
        _trade(TradeType.SELL, "1", "120", 2),
        _trade(TradeType.BUY, "2", "50", 3),
        _trade(TradeType.SHORT, "1", "30", 4),
    ]
    assert calculate_total_invested(trades) == Decimal("230")
