from dataclasses import dataclass


@dataclass(frozen=True)
class AssetExposureInput:
    asset_id: int
    symbol: str
    asset_type: str
    market: str
    value: float


@dataclass(frozen=True)
class AssetExposureItem:
    asset_id: int
    symbol: str
    value: float
    weight_pct: float


@dataclass(frozen=True)
class GroupExposureItem:
    group: str
    value: float
    weight_pct: float


@dataclass(frozen=True)
class ExposureResult:
    total_value: float
    by_asset: list[AssetExposureItem]
    by_asset_type: list[GroupExposureItem]
    by_market: list[GroupExposureItem]
    hhi: float


def calculate_exposure(assets: list[AssetExposureInput]) -> ExposureResult | None:
    if not assets:
        return None

    total_value = sum(asset.value for asset in assets)
    if total_value <= 0:
        return None

    by_asset = [
        AssetExposureItem(
            asset_id=asset.asset_id,
            symbol=asset.symbol,
            value=asset.value,
            weight_pct=(asset.value / total_value) * 100,
        )
        for asset in assets
    ]
    by_asset.sort(key=lambda item: item.weight_pct, reverse=True)

    asset_type_totals: dict[str, float] = {}
    market_totals: dict[str, float] = {}
    for asset in assets:
        asset_type_totals[asset.asset_type] = asset_type_totals.get(asset.asset_type, 0.0) + asset.value
        market_totals[asset.market] = market_totals.get(asset.market, 0.0) + asset.value

    by_asset_type = [
        GroupExposureItem(
            group=group,
            value=value,
            weight_pct=(value / total_value) * 100,
        )
        for group, value in asset_type_totals.items()
    ]
    by_asset_type.sort(key=lambda item: item.weight_pct, reverse=True)

    by_market = [
        GroupExposureItem(
            group=group,
            value=value,
            weight_pct=(value / total_value) * 100,
        )
        for group, value in market_totals.items()
    ]
    by_market.sort(key=lambda item: item.weight_pct, reverse=True)

    weights = [asset.value / total_value for asset in assets]
    hhi = sum(weight ** 2 for weight in weights)

    return ExposureResult(
        total_value=total_value,
        by_asset=by_asset,
        by_asset_type=by_asset_type,
        by_market=by_market,
        hhi=hhi,
    )
