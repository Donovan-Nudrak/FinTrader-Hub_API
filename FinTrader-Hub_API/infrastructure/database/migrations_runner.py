import logging
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from core.config import get_settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_HEAD_REVISION = "20260610_0009"

DEFAULT_MAX_ATTEMPTS = 30
DEFAULT_RETRY_DELAY_SECONDS = 2.0


class MigrationStartupError(Exception):
    """Raised when database startup or migrations fail during application boot."""


def wait_for_database(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database connection established", extra={"attempt": attempt})
            return
        except SQLAlchemyError as exc:
            last_error = exc
            logger.warning(
                "Database not ready, retrying",
                extra={"attempt": attempt, "max_attempts": max_attempts, "error": str(exc)},
            )
            time.sleep(delay_seconds)

    raise MigrationStartupError(
        f"Database is not reachable after {max_attempts} attempts: {last_error}",
    ) from last_error


def run_migrations() -> None:
    settings = get_settings()
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", "infrastructure/database/migrations")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    try:
        logger.info("Applying Alembic migrations", extra={"target": "head"})
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception as exc:
        raise MigrationStartupError(f"Alembic migration failed: {exc}") from exc


def apply_startup_migrations() -> None:
    wait_for_database()
    run_migrations()
