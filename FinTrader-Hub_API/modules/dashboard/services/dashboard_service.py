import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from core.enums import PositionStatus
from modules.alerts.repositories import AlertEventRepository, AlertRepository
from modules.asset.repositories.asset_repository import AssetRepository
from modules.dashboard.schemas.dashboard import (
    ActiveAlertItem,
    ActiveAlertsResponse,
    DailyPerformanceAssetItem,
    DailyPerformanceResponse,
    DashboardMoverItem,
    DashboardSummaryResponse,
    PortfolioSnapshotItem,
    PortfolioSnapshotResponse,
    TopMoversResponse,
)
from modules.market.repositories.market_price_repository import MarketPriceRepository
from modules.portfolio.repositories import PortfolioRepository
from modules.portfolio.services.analytics_service import AnalyticsService
from modules.risk.services.risk_service import RiskService
from modules.trade.repositories.position_repository import PositionRepository
from modules.trade.repositories.trade_repository import TradeRepository

logger = logging.getLogger(__name__)


def _to_decimal(value: Decimal | str | float | int) -> Decimal:
    return Decimal(str(value))


def _pnl_pct(pnl: Decimal, cost_basis: Decimal) -> Decimal:
    if cost_basis <= 0:
        return Decimal("0")
    return (pnl / cost_basis) * Decimal("100")


def _change_pct(current: Decimal, previous: Decimal) -> Decimal:
    if previous <= 0:
        return Decimal("0")
    return ((current - previous) / previous) * Decimal("100")


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.portfolio_repository = PortfolioRepository(db)
        self.position_repository = PositionRepository(db)
        self.trade_repository = TradeRepository(db)
        self.market_price_repository = MarketPriceRepository(db)
        self.asset_repository = AssetRepository(db)
        self.alert_repository = AlertRepository(db)
        self.alert_event_repository = AlertEventRepository(db)
        self.analytics_service = AnalyticsService(db)
        self.risk_service = RiskService(db)

    def get_dashboard_summary(self, user_id: int) -> DashboardSummaryResponse:
        portfolios = self.portfolio_repository.list_by_user_id(user_id)
        active_alerts = self._list_active_alerts(user_id)

        total_value = Decimal("0")
        total_cost = Decimal("0")
        total_realized = Decimal("0")
        open_positions_count = 0
        position_movers: list[DashboardMoverItem] = []
        drawdowns: list[Decimal] = []
        last_price_update: datetime | None = None

        for portfolio in portfolios:
            try:
                performance = self.analytics_service.calculate_portfolio_performance(
                    user_id,
                    portfolio.id,
                )
                total_realized += _to_decimal(performance.total_realized_pnl)
            except Exception as exc:
                logger.warning("Summary performance unavailable for portfolio %s: %s", portfolio.id, exc)

            try:
                value_data = self.analytics_service.calculate_portfolio_value(user_id, portfolio.id)
                total_value += _to_decimal(value_data.portfolio_value)
                total_cost += _to_decimal(value_data.total_cost)

                for position in value_data.positions:
                    open_positions_count += 1
                    cost_basis = _to_decimal(position.quantity) * _to_decimal(position.average_price)
                    unrealized = _to_decimal(position.current_value) - cost_basis
                    position_movers.append(
                        DashboardMoverItem(
                            asset_id=position.asset_id,
                            symbol=position.symbol,
                            portfolio_id=portfolio.id,
                            change_pct=_pnl_pct(unrealized, cost_basis),
                            current_price=_to_decimal(position.latest_price),
                            previous_price=_to_decimal(position.average_price),
                            unrealized_pnl=unrealized,
                            unrealized_pnl_pct=_pnl_pct(unrealized, cost_basis),
                        )
                    )
            except Exception as exc:
                logger.warning("Summary value unavailable for portfolio %s: %s", portfolio.id, exc)

            try:
                drawdown = self.risk_service.calculate_drawdown(user_id, portfolio.id)
                if drawdown.current_drawdown is not None:
                    drawdowns.append(_to_decimal(drawdown.current_drawdown))
            except Exception as exc:
                logger.warning("Summary drawdown unavailable for portfolio %s: %s", portfolio.id, exc)

        asset_ids = self._collect_user_asset_ids(user_id)
        for asset_id in asset_ids:
            try:
                latest = self.market_price_repository.get_latest_by_asset_id(asset_id)
                if latest and (last_price_update is None or latest.timestamp > last_price_update):
                    last_price_update = latest.timestamp
            except Exception:
                continue

        total_unrealized = total_value - total_cost if total_value or total_cost else Decimal("0")
        gainers = sorted(position_movers, key=lambda item: item.unrealized_pnl_pct or Decimal("0"), reverse=True)
        losers = sorted(position_movers, key=lambda item: item.unrealized_pnl_pct or Decimal("0"))

        return DashboardSummaryResponse(
            portfolio_total_value=total_value,
            total_unrealized_pnl=total_unrealized,
            total_unrealized_pnl_pct=_pnl_pct(total_unrealized, total_cost),
            total_realized_pnl=total_realized,
            open_positions_count=open_positions_count,
            active_alerts_count=len(active_alerts),
            top_gainers=gainers[:3],
            top_losers=losers[:3],
            current_drawdown=max(drawdowns) if drawdowns else None,
            last_price_update=last_price_update,
        )

    def get_portfolio_snapshot(self, user_id: int) -> PortfolioSnapshotResponse:
        portfolios = self.portfolio_repository.list_by_user_id(user_id)
        snapshots: list[PortfolioSnapshotItem] = []

        for portfolio in portfolios:
            open_positions_count = 0
            current_value = None
            total_cost = None
            unrealized_pnl = None
            unrealized_pnl_pct = None
            asset_type_allocation: list[dict[str, Decimal | str]] = []

            try:
                positions = self.position_repository.list_by_portfolio_id(portfolio.id)
                open_positions_count = sum(
                    1 for position in positions if position.status == PositionStatus.OPEN
                )
            except Exception as exc:
                logger.warning("Snapshot positions unavailable for portfolio %s: %s", portfolio.id, exc)

            try:
                value_data = self.analytics_service.calculate_portfolio_value(user_id, portfolio.id)
                current_value = _to_decimal(value_data.portfolio_value)
                total_cost = _to_decimal(value_data.total_cost)
                unrealized_pnl = _to_decimal(value_data.unrealized_pnl)
                unrealized_pnl_pct = _to_decimal(value_data.unrealized_pnl_pct)
            except Exception as exc:
                logger.warning("Snapshot value unavailable for portfolio %s: %s", portfolio.id, exc)

            try:
                allocation = self.analytics_service.calculate_asset_allocation(user_id, portfolio.id)
                asset_type_allocation = [
                    {
                        "group": item.group,
                        "weight_pct": _to_decimal(item.weight_pct),
                    }
                    for item in allocation.by_asset_type
                ]
            except Exception as exc:
                logger.warning("Snapshot allocation unavailable for portfolio %s: %s", portfolio.id, exc)

            snapshots.append(
                PortfolioSnapshotItem(
                    portfolio_id=portfolio.id,
                    portfolio_name=portfolio.name,
                    current_value=current_value,
                    total_cost=total_cost,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    open_positions_count=open_positions_count,
                    asset_type_allocation=asset_type_allocation,
                )
            )

        return PortfolioSnapshotResponse(portfolios=snapshots)

    def get_daily_performance(self, user_id: int) -> DailyPerformanceResponse:
        now = datetime.now(UTC)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        portfolios = self.portfolio_repository.list_by_user_id(user_id)

        current_value = Decimal("0")
        start_value = Decimal("0")
        trades_today = 0
        asset_day_changes: list[DailyPerformanceAssetItem] = []

        for portfolio in portfolios:
            try:
                trades = self.trade_repository.list_by_portfolio_id(portfolio.id)
                trades_today += sum(1 for trade in trades if trade.executed_at >= day_start)
            except Exception as exc:
                logger.warning("Daily trades unavailable for portfolio %s: %s", portfolio.id, exc)

            try:
                positions = self.position_repository.list_by_portfolio_id(portfolio.id)
                open_positions = [position for position in positions if position.status == PositionStatus.OPEN]

                for position in open_positions:
                    latest = self.market_price_repository.get_latest_by_asset_id(position.asset_id)
                    if latest is None:
                        continue

                    asset = self.asset_repository.get_by_id(position.asset_id)
                    if asset is None:
                        continue

                    quantity = _to_decimal(position.quantity)
                    current_price = _to_decimal(latest.price)
                    start_price = self._price_at_day_start(position.asset_id, day_start)

                    position_current = quantity * current_price
                    current_value += position_current

                    if start_price is None:
                        continue

                    position_start = quantity * start_price
                    start_value += position_start
                    change_value = position_current - position_start

                    asset_day_changes.append(
                        DailyPerformanceAssetItem(
                            asset_id=asset.id,
                            symbol=asset.symbol,
                            change_value=change_value,
                            change_pct=_change_pct(current_price, start_price),
                        )
                    )
            except Exception as exc:
                logger.warning("Daily performance unavailable for portfolio %s: %s", portfolio.id, exc)

        change_value = current_value - start_value if start_value > 0 else None
        change_pct = _change_pct(current_value, start_value) if start_value > 0 else None
        top_gainer = max(asset_day_changes, key=lambda item: item.change_pct, default=None)
        top_loser = min(asset_day_changes, key=lambda item: item.change_pct, default=None)

        return DailyPerformanceResponse(
            start_of_day_value=start_value if start_value > 0 else None,
            current_value=current_value if current_value > 0 else None,
            change_value=change_value,
            change_pct=change_pct,
            top_gainer=top_gainer,
            top_loser=top_loser,
            trades_executed_today=trades_today,
        )

    def get_active_alerts(self, user_id: int) -> ActiveAlertsResponse:
        alerts = self._list_active_alerts(user_id)
        items: list[ActiveAlertItem] = []

        for alert in alerts:
            try:
                events = self.alert_event_repository.list_by_alert_id(alert.id)
                items.append(
                    ActiveAlertItem(
                        alert_id=alert.id,
                        alert_type=alert.alert_type,
                        condition=alert.condition,
                        threshold=_to_decimal(alert.threshold),
                        portfolio_id=alert.portfolio_id,
                        asset_id=alert.asset_id,
                        last_triggered_at=alert.last_triggered_at,
                        total_triggers=len(events),
                    )
                )
            except Exception as exc:
                logger.warning("Active alert item unavailable for alert %s: %s", alert.id, exc)

        return ActiveAlertsResponse(alerts=items, total_active=len(items))

    def get_top_movers(self, user_id: int) -> TopMoversResponse:
        movers = self._calculate_price_movers_24h(user_id)
        gainers = sorted(movers, key=lambda item: item.change_pct, reverse=True)[:5]
        losers = sorted(movers, key=lambda item: item.change_pct)[:5]
        return TopMoversResponse(top_gainers=gainers, top_losers=losers)

    def _list_active_alerts(self, user_id: int) -> list:
        try:
            return [
                alert
                for alert in self.alert_repository.list_by_user_id(user_id)
                if alert.is_active
            ]
        except Exception as exc:
            logger.warning("Active alerts unavailable for user %s: %s", user_id, exc)
            return []

    def _collect_user_asset_ids(self, user_id: int) -> set[int]:
        asset_ids: set[int] = set()
        portfolios = self.portfolio_repository.list_by_user_id(user_id)
        for portfolio in portfolios:
            try:
                positions = self.position_repository.list_by_portfolio_id(portfolio.id)
                for position in positions:
                    if position.status == PositionStatus.OPEN:
                        asset_ids.add(position.asset_id)
            except Exception:
                continue
        return asset_ids

    def _calculate_price_movers_24h(self, user_id: int) -> list[DashboardMoverItem]:
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=24)
        movers: list[DashboardMoverItem] = []
        asset_ids = self._collect_user_asset_ids(user_id)

        for asset_id in asset_ids:
            try:
                asset = self.asset_repository.get_by_id(asset_id)
                if asset is None:
                    continue

                latest = self.market_price_repository.get_latest_by_asset_id(asset_id)
                if latest is None:
                    continue

                previous_price = self._price_near_datetime(asset_id, cutoff)
                if previous_price is None:
                    continue

                current_price = _to_decimal(latest.price)
                movers.append(
                    DashboardMoverItem(
                        asset_id=asset.id,
                        symbol=asset.symbol,
                        change_pct=_change_pct(current_price, previous_price),
                        current_price=current_price,
                        previous_price=previous_price,
                    )
                )
            except Exception as exc:
                logger.warning("Top mover unavailable for asset %s: %s", asset_id, exc)

        return movers

    def _price_at_day_start(self, asset_id: int, day_start: datetime) -> Decimal | None:
        prices = self.market_price_repository.list_by_asset_and_range(
            asset_id,
            from_date=day_start,
            to_date=day_start + timedelta(hours=1),
        )
        if prices:
            return _to_decimal(prices[0].price)

        fallback = self._price_near_datetime(asset_id, day_start)
        return fallback

    def _price_near_datetime(self, asset_id: int, target: datetime) -> Decimal | None:
        prices = self.market_price_repository.list_by_asset_and_range(
            asset_id,
            from_date=target - timedelta(hours=2),
            to_date=target + timedelta(hours=2),
        )
        if not prices:
            older_prices = self.market_price_repository.list_by_asset_and_range(
                asset_id,
                from_date=target - timedelta(days=7),
                to_date=target,
            )
            if not older_prices:
                return None
            return _to_decimal(older_prices[-1].price)

        closest = min(prices, key=lambda price: abs((price.timestamp - target).total_seconds()))
        return _to_decimal(closest.price)
