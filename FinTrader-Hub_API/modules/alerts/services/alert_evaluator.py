from dataclasses import dataclass
from datetime import datetime, timedelta

from core.enums import AlertCondition, AlertType

COOLDOWN_HOURS = 24


@dataclass(frozen=True)
class EvaluationResult:
    triggered: bool
    trigger_value: float
    message: str


def is_within_cooldown(
    last_triggered_at: datetime | None,
    now: datetime,
    *,
    cooldown_hours: int = COOLDOWN_HOURS,
) -> bool:
    if last_triggered_at is None:
        return False
    return now - last_triggered_at < timedelta(hours=cooldown_hours)


def evaluate_alert_condition(
    alert_type: AlertType,
    condition: AlertCondition,
    threshold: float,
    current_value: float,
    *,
    base_value: float | None = None,
) -> EvaluationResult:
    triggered = _condition_met(
        alert_type=alert_type,
        condition=condition,
        threshold=threshold,
        current_value=current_value,
        base_value=base_value,
    )
    message = _build_message(
        alert_type=alert_type,
        condition=condition,
        threshold=threshold,
        current_value=current_value,
        base_value=base_value,
        triggered=triggered,
    )
    return EvaluationResult(
        triggered=triggered,
        trigger_value=current_value,
        message=message,
    )


def _condition_met(
    *,
    alert_type: AlertType,
    condition: AlertCondition,
    threshold: float,
    current_value: float,
    base_value: float | None,
) -> bool:
    if alert_type == AlertType.PRICE:
        if condition == AlertCondition.ABOVE:
            return current_value > threshold
        if condition == AlertCondition.BELOW:
            return current_value < threshold
        if condition == AlertCondition.PERCENT_CHANGE:
            if base_value is None or base_value == 0:
                return False
            percent_change = abs((current_value - base_value) / base_value) * 100
            return percent_change > threshold

    if alert_type == AlertType.PORTFOLIO_VALUE:
        if condition == AlertCondition.ABOVE:
            return current_value > threshold
        if condition == AlertCondition.BELOW:
            return current_value < threshold

    if alert_type == AlertType.PORTFOLIO_PNL:
        if condition == AlertCondition.ABOVE:
            return current_value > threshold
        if condition == AlertCondition.BELOW:
            return current_value < threshold

    if alert_type == AlertType.DRAWDOWN and condition == AlertCondition.ABOVE:
        return current_value > threshold

    if alert_type == AlertType.CONCENTRATION and condition == AlertCondition.ABOVE:
        return current_value > threshold

    return False


def _build_message(
    *,
    alert_type: AlertType,
    condition: AlertCondition,
    threshold: float,
    current_value: float,
    base_value: float | None,
    triggered: bool,
) -> str:
    status = "triggered" if triggered else "not triggered"
    if alert_type == AlertType.PRICE and condition == AlertCondition.PERCENT_CHANGE and base_value is not None:
        percent_change = ((current_value - base_value) / base_value) * 100 if base_value else 0
        return (
            f"Price alert {status}: current price {current_value:.4f}, "
            f"base price {base_value:.4f}, change {percent_change:.2f}%, threshold {threshold:.4f}"
        )

    return (
        f"{alert_type.value} alert {status}: current value {current_value:.4f}, "
        f"condition {condition.value}, threshold {threshold:.4f}"
    )
