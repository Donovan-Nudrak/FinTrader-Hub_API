from dataclasses import dataclass


@dataclass(frozen=True)
class KellyCriterionResult:
    fraction: float
    win_rate: float
    avg_win: float
    avg_loss: float
    payoff_ratio: float
    assumptions: str


@dataclass(frozen=True)
class FixedRiskResult:
    quantity: float
    risk_amount: float
    risk_per_unit: float
    assumptions: str


@dataclass(frozen=True)
class PositionSizingResult:
    kelly: KellyCriterionResult | None
    fixed_risk: FixedRiskResult | None


def calculate_kelly_criterion(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
) -> KellyCriterionResult | None:
    if avg_loss <= 0 or avg_win <= 0:
        return None
    if win_rate < 0 or win_rate > 1:
        return None

    loss_rate = 1 - win_rate
    payoff_ratio = avg_win / avg_loss
    fraction = (win_rate * payoff_ratio - loss_rate) / payoff_ratio

    return KellyCriterionResult(
        fraction=fraction,
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        payoff_ratio=payoff_ratio,
        assumptions="Kelly derived from historical realized trade outcomes in the portfolio.",
    )


def calculate_fixed_risk(
    capital: float,
    risk_pct: float,
    entry_price: float,
    stop_loss: float,
) -> FixedRiskResult | None:
    if capital <= 0 or risk_pct <= 0 or entry_price <= 0:
        return None

    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit == 0:
        return None

    risk_amount = capital * risk_pct
    quantity = risk_amount / risk_per_unit

    return FixedRiskResult(
        quantity=quantity,
        risk_amount=risk_amount,
        risk_per_unit=risk_per_unit,
        assumptions="Fixed risk sizes position so total loss at stop equals capital * risk_pct.",
    )


def calculate_position_sizing(
    *,
    win_rate: float | None,
    avg_win: float | None,
    avg_loss: float | None,
    capital: float,
    risk_pct: float,
    entry_price: float,
    stop_loss: float,
) -> PositionSizingResult:
    kelly = None
    if win_rate is not None and avg_win is not None and avg_loss is not None:
        kelly = calculate_kelly_criterion(win_rate, avg_win, avg_loss)

    fixed_risk = calculate_fixed_risk(capital, risk_pct, entry_price, stop_loss)

    return PositionSizingResult(kelly=kelly, fixed_risk=fixed_risk)
