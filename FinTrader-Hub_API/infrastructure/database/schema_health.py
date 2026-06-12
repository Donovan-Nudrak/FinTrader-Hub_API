from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.migrations_runner import ALEMBIC_HEAD_REVISION
from infrastructure.database.session import engine

ESSENTIAL_TABLES = (
    "users",
    "roles",
    "portfolios",
    "assets",
    "trades",
    "positions",
    "market_prices",
    "alerts",
    "user_settings",
)


def check_migrations_status() -> str:
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1"),
            )
            current_revision = result.scalar()
    except SQLAlchemyError:
        return "unknown"

    if current_revision is None:
        return "pending"

    if current_revision != ALEMBIC_HEAD_REVISION:
        return "outdated"

    return "applied"


def check_schema_status() -> str:
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = ANY(:table_names)
                    """,
                ),
                {"table_names": list(ESSENTIAL_TABLES)},
            )
            existing_tables = {row[0] for row in result}
    except SQLAlchemyError:
        return "incomplete"

    if existing_tables == set(ESSENTIAL_TABLES):
        return "ready"

    return "incomplete"


def check_application_schema_ready() -> dict[str, str]:
    return {
        "migrations": check_migrations_status(),
        "schema": check_schema_status(),
    }
