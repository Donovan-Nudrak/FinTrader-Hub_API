import math

MIN_PERIODS = 30
TRADING_DAYS_PER_YEAR = 252


def calculate_sortino_ratio(
    returns: list[float],
    risk_free_rate: float = 0.0,
) -> float | None:
    if len(returns) < MIN_PERIODS:
        return None

    mean_return = sum(returns) / len(returns)
    daily_risk_free_rate = risk_free_rate / TRADING_DAYS_PER_YEAR

    downside_squared = [
        min(0.0, value - daily_risk_free_rate) ** 2
        for value in returns
        if value < daily_risk_free_rate
    ]
    if not downside_squared:
        return None

    downside_deviation = math.sqrt(sum(downside_squared) / len(returns))
    if downside_deviation == 0:
        return None

    return ((mean_return - daily_risk_free_rate) / downside_deviation) * math.sqrt(TRADING_DAYS_PER_YEAR)
