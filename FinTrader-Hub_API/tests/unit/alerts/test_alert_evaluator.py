from datetime import UTC, datetime, timedelta

from core.enums import AlertCondition, AlertType
from modules.alerts.services.alert_evaluator import (
    evaluate_alert_condition,
    is_within_cooldown,
)


def test_price_above_condition_met() -> None:
    result = evaluate_alert_condition(
        AlertType.PRICE,
        AlertCondition.ABOVE,
        threshold=100.0,
        current_value=120.0,
    )
    assert result.triggered is True


def test_price_above_condition_not_met() -> None:
    result = evaluate_alert_condition(
        AlertType.PRICE,
        AlertCondition.ABOVE,
        threshold=100.0,
        current_value=90.0,
    )
    assert result.triggered is False


def test_drawdown_above_threshold() -> None:
    result = evaluate_alert_condition(
        AlertType.DRAWDOWN,
        AlertCondition.ABOVE,
        threshold=0.10,
        current_value=0.25,
    )
    assert result.triggered is True


def test_cooldown_blocks_recent_trigger() -> None:
    now = datetime.now(UTC)
    last_triggered = now - timedelta(hours=1)
    assert is_within_cooldown(last_triggered, now) is True


def test_cooldown_allows_trigger_after_25_hours() -> None:
    now = datetime.now(UTC)
    last_triggered = now - timedelta(hours=25)
    assert is_within_cooldown(last_triggered, now) is False
