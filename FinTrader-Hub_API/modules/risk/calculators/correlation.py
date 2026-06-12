import math
from dataclasses import dataclass

MIN_PERIODS = 30


@dataclass(frozen=True)
class CorrelationAsset:
    asset_id: int
    symbol: str


@dataclass(frozen=True)
class CorrelationResult:
    assets: list[CorrelationAsset]
    matrix: list[list[float | None]]


def _pearson_correlation(series_a: list[float], series_b: list[float]) -> float | None:
    if len(series_a) < MIN_PERIODS or len(series_b) < MIN_PERIODS:
        return None
    if len(series_a) != len(series_b):
        return None

    mean_a = sum(series_a) / len(series_a)
    mean_b = sum(series_b) / len(series_b)

    covariance = sum((a - mean_a) * (b - mean_b) for a, b in zip(series_a, series_b, strict=True))
    variance_a = sum((a - mean_a) ** 2 for a in series_a)
    variance_b = sum((b - mean_b) ** 2 for b in series_b)

    denominator = math.sqrt(variance_a * variance_b)
    if denominator == 0:
        return None

    return covariance / denominator


def calculate_correlation_matrix(
    asset_returns: dict[int, list[float]],
    asset_symbols: dict[int, str],
) -> CorrelationResult | None:
    if len(asset_returns) < 2:
        return None

    asset_ids = sorted(asset_returns.keys())
    for asset_id in asset_ids:
        if len(asset_returns[asset_id]) < MIN_PERIODS:
            return None

    lengths = {len(asset_returns[asset_id]) for asset_id in asset_ids}
    if len(lengths) != 1:
        return None

    assets = [
        CorrelationAsset(asset_id=asset_id, symbol=asset_symbols[asset_id])
        for asset_id in asset_ids
    ]

    matrix: list[list[float | None]] = []
    for row_id in asset_ids:
        row: list[float | None] = []
        for col_id in asset_ids:
            if row_id == col_id:
                row.append(1.0)
            else:
                row.append(
                    _pearson_correlation(asset_returns[row_id], asset_returns[col_id])
                )
        matrix.append(row)

    return CorrelationResult(assets=assets, matrix=matrix)
