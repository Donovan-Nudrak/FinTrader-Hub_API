from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from core.config import get_settings
from core.enums import PositionStatus, TradeType
from core.exceptions import NotFoundError
from modules.asset.repositories.asset_repository import AssetRepository
from modules.market.models.market_price import MarketPrice
from modules.market.repositories.market_price_repository import MarketPriceRepository
from modules.portfolio.repositories import PortfolioRepository
from modules.risk.calculators.correlation import calculate_correlation_matrix
from modules.risk.calculators.drawdown import calculate_drawdown
from modules.risk.calculators.exposure import AssetExposureInput, calculate_exposure
from modules.risk.calculators.position_sizing import calculate_position_sizing
from modules.risk.calculators.sharpe_ratio import calculate_sharpe_ratio
from modules.risk.calculators.sortino_ratio import calculate_sortino_ratio
from modules.risk.schemas.risk import (
    AssetExposureItem,
    CorrelationAssetItem,
    CorrelationResponse,
    DrawdownResponse,
    ExposureResponse,
    FixedRiskResponse,
    GroupExposureItem,
    KellyCriterionResponse,
    PortfolioValuePoint,
    PositionSizingRequest,
    PositionSizingResponse,
    RiskReportResponse,
    SharpeRatioResponse,
    SortinoRatioResponse,
)
from modules.trade.models.trade import Trade
from modules.trade.repositories.position_repository import PositionRepository
from modules.trade.repositories.trade_repository import TradeRepository


class RiskService:
    LOOKBACK_DAYS = 365

    def __init__(self, db: Session) -> None:
        self.db = db
        self.portfolio_repository = PortfolioRepository(db)
        self.position_repository = PositionRepository(db)
        self.trade_repository = TradeRepository(db)
        self.market_price_repository = MarketPriceRepository(db)
        self.asset_repository = AssetRepository(db)
        self.settings = get_settings()

    def calculate_drawdown(self, user_id: int, portfolio_id: int) -> DrawdownResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        value_series = self._build_portfolio_value_series(portfolio_id)
        values = [point[1] for point in value_series]

        if len(values) < 2:
            return DrawdownResponse(
                portfolio_id=portfolio_id,
                insufficient_data=True,
                value_series=[
                    PortfolioValuePoint(date=point[0], value=point[1]) for point in value_series
                ],
            )

        result = calculate_drawdown(values)
        return DrawdownResponse(
            portfolio_id=portfolio_id,
            maximum_drawdown=result.maximum_drawdown if result else None,
            current_drawdown=result.current_drawdown if result else None,
            value_series=[
                PortfolioValuePoint(date=point[0], value=point[1]) for point in value_series
            ],
            insufficient_data=result is None,
        )

    def calculate_sharpe_ratio(self, user_id: int, portfolio_id: int) -> SharpeRatioResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        returns = self._build_portfolio_returns(portfolio_id)
        sharpe = calculate_sharpe_ratio(returns, self.settings.risk_free_rate)

        return SharpeRatioResponse(
            portfolio_id=portfolio_id,
            sharpe_ratio=sharpe,
            risk_free_rate=self.settings.risk_free_rate,
            periods=len(returns),
            insufficient_data=sharpe is None,
        )

    def calculate_sortino_ratio(self, user_id: int, portfolio_id: int) -> SortinoRatioResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        returns = self._build_portfolio_returns(portfolio_id)
        sortino = calculate_sortino_ratio(returns, self.settings.risk_free_rate)

        return SortinoRatioResponse(
            portfolio_id=portfolio_id,
            sortino_ratio=sortino,
            risk_free_rate=self.settings.risk_free_rate,
            periods=len(returns),
            insufficient_data=sortino is None,
        )

    def calculate_exposure(self, user_id: int, portfolio_id: int) -> ExposureResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        positions = self.position_repository.list_by_portfolio_id(portfolio_id)
        open_positions = [position for position in positions if position.status == PositionStatus.OPEN]

        assets_without_price: list[str] = []
        exposure_inputs: list[AssetExposureInput] = []

        for position in open_positions:
            asset = self.asset_repository.get_by_id(position.asset_id)
            if asset is None:
                continue

            latest_price = self.market_price_repository.get_latest_by_asset_id(position.asset_id)
            if latest_price is None:
                assets_without_price.append(asset.symbol)
                continue

            value = float(Decimal(str(position.quantity)) * Decimal(str(latest_price.price)))
            exposure_inputs.append(
                AssetExposureInput(
                    asset_id=asset.id,
                    symbol=asset.symbol,
                    asset_type=asset.asset_type.value,
                    market=asset.market.value,
                    value=value,
                )
            )

        result = calculate_exposure(exposure_inputs)
        if result is None:
            return ExposureResponse(
                portfolio_id=portfolio_id,
                total_value=0.0,
                hhi=0.0,
                assets_without_price=assets_without_price,
            )

        return ExposureResponse(
            portfolio_id=portfolio_id,
            total_value=result.total_value,
            by_asset=[
                AssetExposureItem(
                    asset_id=item.asset_id,
                    symbol=item.symbol,
                    value=item.value,
                    weight_pct=item.weight_pct,
                )
                for item in result.by_asset
            ],
            by_asset_type=[
                GroupExposureItem(group=item.group, value=item.value, weight_pct=item.weight_pct)
                for item in result.by_asset_type
            ],
            by_market=[
                GroupExposureItem(group=item.group, value=item.value, weight_pct=item.weight_pct)
                for item in result.by_market
            ],
            hhi=result.hhi,
            assets_without_price=assets_without_price,
        )

    def calculate_correlation(self, user_id: int, portfolio_id: int) -> CorrelationResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        asset_returns, asset_symbols = self._build_asset_return_series(portfolio_id)

        if len(asset_returns) < 2:
            return CorrelationResponse(portfolio_id=portfolio_id, insufficient_data=True)

        result = calculate_correlation_matrix(asset_returns, asset_symbols)
        if result is None:
            return CorrelationResponse(portfolio_id=portfolio_id, insufficient_data=True)

        return CorrelationResponse(
            portfolio_id=portfolio_id,
            assets=[
                CorrelationAssetItem(asset_id=asset.asset_id, symbol=asset.symbol)
                for asset in result.assets
            ],
            matrix=result.matrix,
            insufficient_data=False,
        )

    def calculate_position_sizing(
        self,
        user_id: int,
        portfolio_id: int,
        request: PositionSizingRequest,
    ) -> PositionSizingResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        win_rate, avg_win, avg_loss = self._compute_kelly_inputs(portfolio_id)

        result = calculate_position_sizing(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            capital=float(request.capital),
            risk_pct=float(request.risk_pct),
            entry_price=float(request.entry_price),
            stop_loss=float(request.stop_loss),
        )

        kelly_response = None
        if result.kelly is not None:
            kelly_response = KellyCriterionResponse(
                fraction=result.kelly.fraction,
                win_rate=result.kelly.win_rate,
                avg_win=result.kelly.avg_win,
                avg_loss=result.kelly.avg_loss,
                payoff_ratio=result.kelly.payoff_ratio,
                assumptions=result.kelly.assumptions,
            )

        fixed_risk_response = None
        if result.fixed_risk is not None:
            fixed_risk_response = FixedRiskResponse(
                quantity=result.fixed_risk.quantity,
                risk_amount=result.fixed_risk.risk_amount,
                risk_per_unit=result.fixed_risk.risk_per_unit,
                assumptions=result.fixed_risk.assumptions,
            )

        return PositionSizingResponse(
            portfolio_id=portfolio_id,
            kelly=kelly_response,
            fixed_risk=fixed_risk_response,
        )

    def generate_risk_report(self, user_id: int, portfolio_id: int) -> RiskReportResponse:
        self._ensure_portfolio_access(user_id, portfolio_id)
        return RiskReportResponse(
            portfolio_id=portfolio_id,
            drawdown=self.calculate_drawdown(user_id, portfolio_id),
            sharpe=self.calculate_sharpe_ratio(user_id, portfolio_id),
            sortino=self.calculate_sortino_ratio(user_id, portfolio_id),
            exposure=self.calculate_exposure(user_id, portfolio_id),
            correlation=self.calculate_correlation(user_id, portfolio_id),
        )

    def _ensure_portfolio_access(self, user_id: int, portfolio_id: int) -> None:
        portfolio = self.portfolio_repository.get_by_id_and_user_id(portfolio_id, user_id)
        if portfolio is None:
            raise NotFoundError("Portfolio not found")

    def _build_portfolio_value_series(self, portfolio_id: int) -> list[tuple[date, float]]:
        trades = self.trade_repository.list_by_portfolio_id(portfolio_id)
        if not trades:
            return []

        asset_ids = {trade.asset_id for trade in trades}
        to_date = datetime.now(UTC)
        from_date = to_date - timedelta(days=self.LOOKBACK_DAYS)

        daily_prices_by_asset: dict[int, dict[date, float]] = {}
        all_dates: set[date] = set()

        for asset_id in asset_ids:
            prices = self.market_price_repository.list_by_asset_and_range(
                asset_id,
                from_date=from_date,
                to_date=to_date,
            )
            daily_prices = self._to_daily_prices(prices)
            if daily_prices:
                daily_prices_by_asset[asset_id] = daily_prices
                all_dates.update(daily_prices.keys())

        if not all_dates:
            return []

        trades_by_asset = self._group_trades_by_asset(trades)
        sorted_dates = sorted(all_dates)
        value_series: list[tuple[date, float]] = []

        for current_date in sorted_dates:
            as_of = datetime.combine(current_date, datetime.max.time(), tzinfo=UTC)
            total_value = 0.0

            for asset_id, asset_trades in trades_by_asset.items():
                quantity = self._quantity_at_date(asset_trades, as_of)
                if quantity == 0:
                    continue

                price = self._price_on_date(daily_prices_by_asset.get(asset_id, {}), current_date)
                if price is None:
                    continue

                total_value += quantity * price

            if total_value > 0:
                value_series.append((current_date, total_value))

        return value_series

    def _build_portfolio_returns(self, portfolio_id: int) -> list[float]:
        value_series = self._build_portfolio_value_series(portfolio_id)
        values = [value for _, value in value_series]
        return self._returns_from_values(values)

    def _build_asset_return_series(
        self,
        portfolio_id: int,
    ) -> tuple[dict[int, list[float]], dict[int, str]]:
        positions = self.position_repository.list_by_portfolio_id(portfolio_id)
        open_asset_ids = {
            position.asset_id
            for position in positions
            if position.status == PositionStatus.OPEN
        }
        if len(open_asset_ids) < 2:
            return {}, {}

        to_date = datetime.now(UTC)
        from_date = to_date - timedelta(days=self.LOOKBACK_DAYS)

        daily_prices_by_asset: dict[int, dict[date, float]] = {}
        asset_symbols: dict[int, str] = {}

        for asset_id in sorted(open_asset_ids):
            asset = self.asset_repository.get_by_id(asset_id)
            if asset is None:
                continue

            prices = self.market_price_repository.list_by_asset_and_range(
                asset_id,
                from_date=from_date,
                to_date=to_date,
            )
            daily_prices = self._to_daily_prices(prices)
            if len(daily_prices) < 31:
                continue

            daily_prices_by_asset[asset_id] = daily_prices
            asset_symbols[asset_id] = asset.symbol

        if len(daily_prices_by_asset) < 2:
            return {}, {}

        common_dates = set.intersection(
            *[set(daily_prices.keys()) for daily_prices in daily_prices_by_asset.values()]
        )
        if len(common_dates) < 31:
            return {}, {}

        sorted_dates = sorted(common_dates)
        asset_returns: dict[int, list[float]] = {}

        for asset_id, daily_prices in daily_prices_by_asset.items():
            values = [daily_prices[current_date] for current_date in sorted_dates]
            returns = self._returns_from_values(values)
            if len(returns) < 30:
                return {}, {}
            asset_returns[asset_id] = returns

        return asset_returns, asset_symbols

    def _compute_kelly_inputs(self, portfolio_id: int) -> tuple[float | None, float | None, float | None]:
        trades = self.trade_repository.list_by_portfolio_id(portfolio_id)
        outcomes = self._extract_realized_outcomes(trades)
        if not outcomes:
            return None, None, None

        wins = [outcome for outcome in outcomes if outcome > 0]
        losses = [abs(outcome) for outcome in outcomes if outcome < 0]
        if not wins or not losses:
            return None, None, None

        win_rate = len(wins) / len(outcomes)
        avg_win = sum(wins) / len(wins)
        avg_loss = sum(losses) / len(losses)
        return win_rate, avg_win, avg_loss

    def _extract_realized_outcomes(self, trades: list[Trade]) -> list[float]:
        outcomes: list[float] = []
        trades_by_asset = self._group_trades_by_asset(trades)

        for asset_trades in trades_by_asset.values():
            quantity = Decimal("0")
            average_price = Decimal("0")
            total_cost = Decimal("0")

            for trade in sorted(asset_trades, key=lambda item: (item.executed_at, item.id)):
                trade_quantity = Decimal(str(trade.quantity))
                trade_price = Decimal(str(trade.price))

                if trade.trade_type == TradeType.BUY:
                    total_cost += trade_quantity * trade_price
                    quantity += trade_quantity
                    if quantity > 0:
                        average_price = total_cost / quantity

                elif trade.trade_type == TradeType.SELL:
                    realized = float((trade_price - average_price) * trade_quantity)
                    outcomes.append(realized)
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
                    realized = float((average_price - trade_price) * trade_quantity)
                    outcomes.append(realized)
                    total_cost -= trade_quantity * average_price
                    quantity -= trade_quantity
                    if quantity > 0:
                        average_price = total_cost / quantity
                    else:
                        average_price = Decimal("0")
                        total_cost = Decimal("0")

        return outcomes

    def _group_trades_by_asset(self, trades: list[Trade]) -> dict[int, list[Trade]]:
        grouped: dict[int, list[Trade]] = defaultdict(list)
        for trade in trades:
            grouped[trade.asset_id].append(trade)
        return grouped

    def _quantity_at_date(self, trades: list[Trade], as_of: datetime) -> float:
        quantity = Decimal("0")
        average_price = Decimal("0")
        total_cost = Decimal("0")

        for trade in sorted(trades, key=lambda item: (item.executed_at, item.id)):
            if trade.executed_at > as_of:
                break

            trade_quantity = Decimal(str(trade.quantity))
            trade_price = Decimal(str(trade.price))

            if trade.trade_type == TradeType.BUY:
                total_cost += trade_quantity * trade_price
                quantity += trade_quantity
                if quantity > 0:
                    average_price = total_cost / quantity

            elif trade.trade_type == TradeType.SELL:
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
                total_cost -= trade_quantity * average_price
                quantity -= trade_quantity
                if quantity > 0:
                    average_price = total_cost / quantity
                else:
                    average_price = Decimal("0")
                    total_cost = Decimal("0")

        return float(quantity)

    def _to_daily_prices(self, prices: list[MarketPrice]) -> dict[date, float]:
        daily: dict[date, float] = {}
        for price in sorted(prices, key=lambda item: item.timestamp):
            daily[price.timestamp.date()] = float(price.price)
        return daily

    def _price_on_date(self, daily_prices: dict[date, float], current_date: date) -> float | None:
        if current_date in daily_prices:
            return daily_prices[current_date]

        prior_dates = [price_date for price_date in daily_prices if price_date <= current_date]
        if not prior_dates:
            return None

        return daily_prices[max(prior_dates)]

    def _returns_from_values(self, values: list[float]) -> list[float]:
        if len(values) < 2:
            return []

        returns: list[float] = []
        for previous, current in zip(values, values[1:], strict=False):
            if previous == 0:
                continue
            returns.append((current - previous) / previous)
        return returns
