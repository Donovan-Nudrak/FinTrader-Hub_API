import math

MIN_PERIODS = 30
TRADING_DAYS_PER_YEAR = 252


def calculate_sharpe_ratio(
    returns: list[float],
    risk_free_rate: float = 0.0,
) -> float | None:
    if len(returns) < MIN_PERIODS:
        return None

    mean_return = sum(returns) / len(returns)
    daily_risk_free_rate = risk_free_rate / TRADING_DAYS_PER_YEAR

    variance = sum((value - mean_return) ** 2 for value in returns) / len(returns)
    std_return = math.sqrt(variance)
    if std_return == 0:
        return None

    return ((mean_return - daily_risk_free_rate) / std_return) * math.sqrt(TRADING_DAYS_PER_YEAR)
