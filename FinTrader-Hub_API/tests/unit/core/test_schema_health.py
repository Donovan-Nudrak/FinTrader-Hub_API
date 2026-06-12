from unittest.mock import MagicMock, patch

from infrastructure.database.migrations_runner import ALEMBIC_HEAD_REVISION
from infrastructure.database.schema_health import (
    ESSENTIAL_TABLES,
    check_application_schema_ready,
    check_migrations_status,
    check_schema_status,
)


def test_check_migrations_status_returns_applied_for_head_revision() -> None:
    connection = MagicMock()
    connection.execute.return_value.scalar.return_value = ALEMBIC_HEAD_REVISION

    with patch("infrastructure.database.schema_health.engine") as mock_engine:
        mock_engine.connect.return_value.__enter__.return_value = connection
        assert check_migrations_status() == "applied"


def test_check_migrations_status_returns_pending_when_missing_revision() -> None:
    connection = MagicMock()
    connection.execute.return_value.scalar.return_value = None

    with patch("infrastructure.database.schema_health.engine") as mock_engine:
        mock_engine.connect.return_value.__enter__.return_value = connection
        assert check_migrations_status() == "pending"


def test_check_schema_status_returns_ready_when_all_tables_exist() -> None:
    connection = MagicMock()
    connection.execute.return_value = [(table,) for table in ESSENTIAL_TABLES]

    with patch("infrastructure.database.schema_health.engine") as mock_engine:
        mock_engine.connect.return_value.__enter__.return_value = connection
        assert check_schema_status() == "ready"


def test_check_schema_status_returns_incomplete_when_tables_missing() -> None:
    connection = MagicMock()
    connection.execute.return_value = [("users",)]

    with patch("infrastructure.database.schema_health.engine") as mock_engine:
        mock_engine.connect.return_value.__enter__.return_value = connection
        assert check_schema_status() == "incomplete"


def test_check_application_schema_ready_combines_statuses() -> None:
    with patch(
        "infrastructure.database.schema_health.check_migrations_status",
        return_value="applied",
    ):
        with patch(
            "infrastructure.database.schema_health.check_schema_status",
            return_value="ready",
        ):
            assert check_application_schema_ready() == {
                "migrations": "applied",
                "schema": "ready",
            }
