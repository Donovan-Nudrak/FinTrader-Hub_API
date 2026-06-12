import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.health import router as health_router
from core.config import get_settings
from core.config.startup_validation import StartupValidationError, validate_startup_settings
from core.exceptions import register_exception_handlers
from core.logging import setup_logging
from core.middleware import register_middleware
from infrastructure.database.migrations_runner import MigrationStartupError, apply_startup_migrations
from modules.auth.routers import router as auth_router
from modules.portfolio.routers import analytics_router, router as portfolio_router
from modules.asset.routers import router as asset_router
from modules.trade.routers import position_router, trade_router
from modules.market.routers import router as market_router
from modules.risk.routers import router as risk_router
from modules.alerts.routers import router as alerts_router
from modules.dashboard.routers import router as dashboard_router
from modules.settings.routers import router as settings_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings)

    try:
        validate_startup_settings(settings)
    except StartupValidationError as exc:
        logger.critical(str(exc))
        raise SystemExit(str(exc)) from exc

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if not settings.skip_auto_migrations:
            try:
                apply_startup_migrations()
            except MigrationStartupError as exc:
                logger.critical(str(exc))
                raise SystemExit(str(exc)) from exc

        logger.info(
            "Application startup",
            extra={"app_name": settings.app_name, "app_env": settings.app_env},
        )
        yield
        logger.info("Application shutdown")

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        debug=False,
        lifespan=lifespan,
    )

    register_exception_handlers(app)
    register_middleware(app, settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(portfolio_router)
    app.include_router(analytics_router)
    app.include_router(asset_router)
    app.include_router(trade_router)
    app.include_router(position_router)
    app.include_router(market_router)
    app.include_router(risk_router)
    app.include_router(alerts_router)
    app.include_router(dashboard_router)
    app.include_router(settings_router)

    return app
