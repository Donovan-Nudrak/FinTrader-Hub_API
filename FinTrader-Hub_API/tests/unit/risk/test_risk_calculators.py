import math

from modules.risk.calculators.correlation import calculate_correlation_matrix
from modules.risk.calculators.drawdown import calculate_drawdown
from modules.risk.calculators.exposure import AssetExposureInput, calculate_exposure
from modules.risk.calculators.position_sizing import (
    calculate_fixed_risk,
    calculate_kelly_criterion,
    calculate_position_sizing,
)
from modules.risk.calculators.sharpe_ratio import calculate_sharpe_ratio
from modules.risk.calculators.sortino_ratio import calculate_sortino_ratio


def test_drawdown_known_series() -> None:
    values = [100.0, 120.0, 90.0, 110.0]
    result = calculate_drawdown(values)

    assert result is not None
    assert abs(result.maximum_drawdown - 0.25) < 1e-9
    assert abs(result.current_drawdown - ((120.0 - 110.0) / 120.0)) < 1e-9


def test_sharpe_ratio_known_returns() -> None:
    returns = [0.01, 0.02, -0.01, 0.015, 0.005] * 6
    result = calculate_sharpe_ratio(returns, risk_free_rate=0.0)

    mean_return = sum(returns) / len(returns)
    variance = sum((value - mean_return) ** 2 for value in returns) / len(returns)
    std_return = math.sqrt(variance)
    expected = (mean_return / std_return) * math.sqrt(252)

    assert result is not None
    assert abs(result - expected) < 1e-9


def test_sortino_ignores_positive_downside() -> None:
    returns = [0.05, 0.04, 0.03, -0.02, -0.03, -0.01] * 5
    sortino = calculate_sortino_ratio(returns, risk_free_rate=0.0)
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.0)

    assert sortino is not None
    assert sharpe is not None
    assert sortino > sharpe


def test_exposure_two_assets_and_hhi() -> None:
    assets = [
        AssetExposureInput(
            asset_id=1,
            symbol="AAA",
            asset_type="CRYPTO",
            market="CRYPTO",
            value=750.0,
        ),
        AssetExposureInput(
            asset_id=2,
            symbol="BBB",
            asset_type="STOCK",
            market="NASDAQ",
            value=250.0,
        ),
    ]
    result = calculate_exposure(assets)

    assert result is not None
    assert result.total_value == 1000.0
    assert abs(result.by_asset[0].weight_pct - 75.0) < 1e-9
    assert abs(result.by_asset[1].weight_pct - 25.0) < 1e-9
    assert abs(sum(item.weight_pct for item in result.by_asset) - 100.0) < 1e-9
    assert abs(result.hhi - (0.75**2 + 0.25**2)) < 1e-9


def test_kelly_criterion_known_values() -> None:
    result = calculate_kelly_criterion(win_rate=0.6, avg_win=100.0, avg_loss=50.0)

    assert result is not None
    assert abs(result.fraction - 0.4) < 1e-9
    assert abs(result.payoff_ratio - 2.0) < 1e-9


def test_fixed_risk_known_values() -> None:
    result = calculate_fixed_risk(
        capital=10000.0,
        risk_pct=0.02,
        entry_price=100.0,
        stop_loss=95.0,
    )

    assert result is not None
    assert abs(result.risk_amount - 200.0) < 1e-9
    assert abs(result.risk_per_unit - 5.0) < 1e-9
    assert abs(result.quantity - 40.0) < 1e-9


def test_correlation_matrix_valid() -> None:
    returns = [0.01, -0.02, 0.015, 0.005, -0.01] * 6
    result = calculate_correlation_matrix(
        {1: returns, 2: returns},
        {1: "AAA", 2: "BBB"},
    )

    assert result is not None
    assert result.matrix[0][0] == 1.0
    assert result.matrix[1][1] == 1.0
    assert result.matrix[0][1] == 1.0


def test_insufficient_data_returns_none() -> None:
    short_returns = [0.01, 0.02, -0.01]

    assert calculate_sharpe_ratio(short_returns) is None
    assert calculate_sortino_ratio(short_returns) is None
    assert calculate_correlation_matrix({1: short_returns, 2: short_returns}, {1: "A", 2: "B"}) is None

    sizing = calculate_position_sizing(
        win_rate=None,
        avg_win=None,
        avg_loss=None,
        capital=10000.0,
        risk_pct=0.02,
        entry_price=100.0,
        stop_loss=100.0,
    )
    assert sizing.fixed_risk is None
