from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from core.enums import PositionStatus, TradeType
from core.exceptions import NotFoundError
from modules.asset.models.asset import Asset
from modules.asset.repositories.asset_repository import AssetRepository
from modules.market.models.market_price import MarketPrice
from modules.market.repositories.market_price_repository import MarketPriceRepository
from modules.portfolio.repositories import PortfolioRepository
from modules.portfolio.schemas.analytics import (
    AllocationGroupItem,
    AllocationItem,
    AssetAllocationResponse,
    AssetWithoutPriceItem,
    PortfolioPerformanceResponse,
    PortfolioValueResponse,
    PositionPnLResponse,
    PositionValueItem,
)
from modules.trade.models.position import Position
from modules.trade.models.trade import Trade
from modules.trade.repositories.position_repository import PositionRepository
from modules.trade.repositories.trade_repository import TradeRepository


def _to_decimal(value: Decimal | str | float | int) -> Decimal:
    return Decimal(str(value))


def _pnl_pct(pnl: Decimal, cost_basis: Decimal) -> Decimal:
    if cost_basis <= 0:
        return Decimal("0")
    return (pnl / cost_basis) * Decimal("100")


def calculate_realized_pnl(trades: list[Trade]) -> Decimal:
    if not trades:
        return Decimal("0")

    realized = Decimal("0")
    quantity = Decimal("0")
    average_price = Decimal("0")
    total_cost = Decimal("0")

    ordered_trades = sorted(trades, key=lambda trade: (trade.executed_at, trade.id))

    for trade in ordered_trades:
        trade_quantity = _to_decimal(trade.quantity)
        trade_price = _to_decimal(trade.price)

        if trade.trade_type == TradeType.BUY:
            total_cost += trade_quantity * trade_price
            quantity += trade_quantity
            if quantity > 0:
                average_price = total_cost / quantity

        elif trade.trade_type == TradeType.SELL:
            realized += (trade_price - average_price) * trade_quantity
            total_cost -= trade_quantity * average_price
            quantity -= trade_quantity
            if quantity > 0:
                average_price = total_cost / quantity
            else:
                average_price = Decimal("0")
                total_cost = Decimal("0")

        elif trade.trade_type == TradeType.SHORT:
            total_cost += trade_quantity * trade_price
            quantity += trade_quantity
            if quantity > 0:
                average_price = total_cost / quantity

        elif trade.trade_type == TradeType.COVER:
            realized += (average_price - trade_price) * trade_quantity
            total_cost -= trade_quantity * average_price
            quantity -= trade_quantity
            if quantity > 0:
                average_price = total_cost / quantity
            else:
                average_price = Decimal("0")
                total_cost = Decimal("0")

    return realized


def calculate_total_invested(trades: list[Trade]) -> Decimal:
    invested = Decimal("0")
    for trade in trades:
        trade_quantity = _to_decimal(trade.quantity)
        trade_price = _to_decimal(trade.price)
        if trade.trade_type in {TradeType.BUY, TradeType.SHORT}:
            invested += trade_quantity * trade_price
    return invested


def calculate_unrealized_pnl(quantity: Decimal, average_price: Decimal, latest_price: Decimal) -> Decimal:
    return (latest_price - average_price) * quantity


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.portfolio_repository = PortfolioRepository(db)
        self.position_repository = PositionRepository(db)
        self.trade_repository = TradeRepository(db)
        self.market_price_repository = MarketPriceRepository(db)
        self.asset_repository = AssetRepository(db)

    def calculate_portfolio_value(self, user_id: int, portfolio_id: int) -> PortfolioValueResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        positions = self.position_repository.list_by_portfolio_id(portfolio_id)
        open_positions = [position for position in positions if position.status == PositionStatus.OPEN]

        assets = self._load_assets_for_positions(open_positions)
        latest_prices = self._load_latest_prices(open_positions)

        portfolio_value = Decimal("0")
        total_cost = Decimal("0")
        position_items: list[PositionValueItem] = []
        assets_without_price: list[AssetWithoutPriceItem] = []

        for position in open_positions:
            asset = assets.get(position.asset_id)
            if asset is None:
                continue

            latest_price = latest_prices.get(position.asset_id)
            if latest_price is None:
                assets_without_price.append(
                    AssetWithoutPriceItem(asset_id=asset.id, symbol=asset.symbol)
                )
                continue

            quantity = _to_decimal(position.quantity)
            average_price = _to_decimal(position.average_price)
            price = _to_decimal(latest_price.price)
            current_value = quantity * price
            cost_basis = quantity * average_price

            portfolio_value += current_value
            total_cost += cost_basis
            position_items.append(
                PositionValueItem(
                    position_id=position.id,
                    asset_id=asset.id,
                    symbol=asset.symbol,
                    quantity=quantity,
                    average_price=average_price,
                    latest_price=price,
                    current_value=current_value,
                )
            )

        unrealized_pnl = portfolio_value - total_cost

        return PortfolioValueResponse(
            portfolio_id=portfolio_id,
            portfolio_value=portfolio_value,
            total_cost=total_cost,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=_pnl_pct(unrealized_pnl, total_cost),
            positions=position_items,
            assets_without_price=assets_without_price,
        )

    def calculate_position_pnl(
        self,
        user_id: int,
        portfolio_id: int,
        position_id: int,
    ) -> PositionPnLResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        position = self.position_repository.get_by_id_and_portfolio_id(position_id, portfolio_id)
        if position is None:
            raise NotFoundError("Position not found")

        asset = self.asset_repository.get_by_id(position.asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")

        trades = self.trade_repository.list_by_portfolio_and_asset(portfolio_id, position.asset_id)
        quantity = _to_decimal(position.quantity)
        average_price = _to_decimal(position.average_price)
        latest_price_record = self.market_price_repository.get_latest_by_asset_id(position.asset_id)
        latest_price = _to_decimal(latest_price_record.price) if latest_price_record else None

        if position.status == PositionStatus.OPEN:
            if latest_price is None:
                return PositionPnLResponse(
                    position_id=position.id,
                    asset_id=asset.id,
                    symbol=asset.symbol,
                    status=position.status,
                    position_type=position.position_type,
                    quantity=quantity,
                    average_price=average_price,
                    latest_price=None,
                    unrealized_pnl=Decimal("0"),
                    unrealized_pnl_pct=Decimal("0"),
                    realized_pnl=None,
                )

            unrealized_pnl = calculate_unrealized_pnl(quantity, average_price, latest_price)
            cost_basis = quantity * average_price
            return PositionPnLResponse(
                position_id=position.id,
                asset_id=asset.id,
                symbol=asset.symbol,
                status=position.status,
                position_type=position.position_type,
                quantity=quantity,
                average_price=average_price,
                latest_price=latest_price,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=_pnl_pct(unrealized_pnl, cost_basis),
                realized_pnl=None,
            )

        realized_pnl = calculate_realized_pnl(trades)
        return PositionPnLResponse(
            position_id=position.id,
            asset_id=asset.id,
            symbol=asset.symbol,
            status=position.status,
            position_type=position.position_type,
            quantity=quantity,
            average_price=average_price,
            latest_price=latest_price,
            unrealized_pnl=Decimal("0"),
            unrealized_pnl_pct=Decimal("0"),
            realized_pnl=realized_pnl,
        )

    def calculate_asset_allocation(self, user_id: int, portfolio_id: int) -> AssetAllocationResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        positions = self.position_repository.list_by_portfolio_id(portfolio_id)
        open_positions = [position for position in positions if position.status == PositionStatus.OPEN]

        assets = self._load_assets_for_positions(open_positions)
        latest_prices = self._load_latest_prices(open_positions)

        total_value = Decimal("0")
        assets_without_price: list[AssetWithoutPriceItem] = []
        asset_values: dict[int, Decimal] = {}

        for position in open_positions:
            asset = assets.get(position.asset_id)
            if asset is None:
                continue

            latest_price = latest_prices.get(position.asset_id)
            if latest_price is None:
                assets_without_price.append(
                    AssetWithoutPriceItem(asset_id=asset.id, symbol=asset.symbol)
                )
                continue

            value = _to_decimal(position.quantity) * _to_decimal(latest_price.price)
            asset_values[asset.id] = asset_values.get(asset.id, Decimal("0")) + value
            total_value += value

        by_asset: list[AllocationItem] = []
        by_asset_type_values: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        by_market_values: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

        for asset_id, value in asset_values.items():
            asset = assets[asset_id]
            weight_pct = (value / total_value) * Decimal("100") if total_value > 0 else Decimal("0")
            by_asset.append(
                AllocationItem(
                    asset_id=asset.id,
                    symbol=asset.symbol,
                    asset_type=asset.asset_type,
                    market=asset.market,
                    value=value,
                    weight_pct=weight_pct,
                )
            )
            by_asset_type_values[asset.asset_type.value] += value
            by_market_values[asset.market.value] += value

        by_asset.sort(key=lambda item: item.weight_pct, reverse=True)

        by_asset_type = [
            AllocationGroupItem(
                group=group,
                value=value,
                weight_pct=(value / total_value) * Decimal("100") if total_value > 0 else Decimal("0"),
            )
            for group, value in by_asset_type_values.items()
        ]
        by_asset_type.sort(key=lambda item: item.weight_pct, reverse=True)

        by_market = [
            AllocationGroupItem(
                group=group,
                value=value,
                weight_pct=(value / total_value) * Decimal("100") if total_value > 0 else Decimal("0"),
            )
            for group, value in by_market_values.items()
        ]
        by_market.sort(key=lambda item: item.weight_pct, reverse=True)

        return AssetAllocationResponse(
            portfolio_id=portfolio_id,
            total_value=total_value,
            by_asset=by_asset,
            by_asset_type=by_asset_type,
            by_market=by_market,
            assets_without_price=assets_without_price,
        )

    def calculate_portfolio_performance(
        self,
        user_id: int,
        portfolio_id: int,
    ) -> PortfolioPerformanceResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        positions = self.position_repository.list_by_portfolio_id(portfolio_id)
        open_positions = [position for position in positions if position.status == PositionStatus.OPEN]

        assets = self._load_assets_for_positions(positions)
        latest_prices = self._load_latest_prices(open_positions)

        total_current_value = Decimal("0")
        total_unrealized_pnl = Decimal("0")
        total_realized_pnl = Decimal("0")
        total_invested = Decimal("0")
        assets_without_price: list[AssetWithoutPriceItem] = []
        seen_missing_assets: set[int] = set()

        all_trades = self.trade_repository.list_by_portfolio_id(portfolio_id)
        total_invested = calculate_total_invested(all_trades)

        asset_trade_map: dict[int, list[Trade]] = defaultdict(list)
        for trade in all_trades:
            asset_trade_map[trade.asset_id].append(trade)

        for position in positions:
            trades = asset_trade_map.get(position.asset_id, [])
            if position.status == PositionStatus.CLOSED:
                total_realized_pnl += calculate_realized_pnl(trades)

        for position in open_positions:
            asset = assets.get(position.asset_id)
            if asset is None:
                continue

            latest_price = latest_prices.get(position.asset_id)
            if latest_price is None:
                if position.asset_id not in seen_missing_assets:
                    assets_without_price.append(
                        AssetWithoutPriceItem(asset_id=asset.id, symbol=asset.symbol)
                    )
                    seen_missing_assets.add(position.asset_id)
                continue

            quantity = _to_decimal(position.quantity)
            average_price = _to_decimal(position.average_price)
            price = _to_decimal(latest_price.price)
            current_value = quantity * price
            unrealized = calculate_unrealized_pnl(quantity, average_price, price)

            total_current_value += current_value
            total_unrealized_pnl += unrealized

        total_pnl = total_realized_pnl + total_unrealized_pnl

        return PortfolioPerformanceResponse(
            portfolio_id=portfolio_id,
            total_invested=total_invested,
            total_current_value=total_current_value,
            total_realized_pnl=total_realized_pnl,
            total_unrealized_pnl=total_unrealized_pnl,
            total_pnl=total_pnl,
            total_return_pct=_pnl_pct(total_pnl, total_invested),
            assets_without_price=assets_without_price,
        )

    def _ensure_portfolio_access(self, user_id: int, portfolio_id: int) -> None:
        portfolio = self.portfolio_repository.get_by_id_and_user_id(portfolio_id, user_id)
        if portfolio is None:
            raise NotFoundError("Portfolio not found")

    def _load_assets_for_positions(self, positions: list[Position]) -> dict[int, Asset]:
        assets: dict[int, Asset] = {}
        for position in positions:
            if position.asset_id in assets:
                continue
            asset = self.asset_repository.get_by_id(position.asset_id)
            if asset is not None:
                assets[position.asset_id] = asset
        return assets

    def _load_latest_prices(self, positions: list[Position]) -> dict[int, MarketPrice]:
        latest_prices: dict[int, MarketPrice] = {}
        for position in positions:
            if position.asset_id in latest_prices:
                continue
            latest_price = self.market_price_repository.get_latest_by_asset_id(position.asset_id)
            if latest_price is not None:
                latest_prices[position.asset_id] = latest_price
        return latest_prices
