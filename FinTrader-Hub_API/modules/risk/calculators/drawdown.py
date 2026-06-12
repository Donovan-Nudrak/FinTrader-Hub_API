from dataclasses import dataclass


@dataclass(frozen=True)
class DrawdownResult:
    maximum_drawdown: float
    current_drawdown: float


def calculate_drawdown(values: list[float]) -> DrawdownResult | None:
    if len(values) < 2:
        return None

    running_peak = values[0]
    maximum_drawdown = 0.0
    current_drawdown = 0.0

    for value in values:
        if value > running_peak:
            running_peak = value
            current_drawdown = 0.0
        elif running_peak > 0:
            drawdown = (running_peak - value) / running_peak
            maximum_drawdown = max(maximum_drawdown, drawdown)
            current_drawdown = drawdown

    return DrawdownResult(
        maximum_drawdown=maximum_drawdown,
        current_drawdown=current_drawdown,
    )
