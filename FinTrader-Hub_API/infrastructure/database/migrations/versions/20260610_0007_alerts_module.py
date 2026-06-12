"""alerts module tables

Revision ID: 20260610_0007
Revises: 20260610_0006
Create Date: 2026-06-10 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260610_0007"
down_revision: Union[str, None] = "20260610_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("portfolio_id", sa.Integer(), nullable=True),
        sa.Column(
            "alert_type",
            sa.Enum(
                "PRICE",
                "PORTFOLIO_VALUE",
                "PORTFOLIO_PNL",
                "DRAWDOWN",
                "CONCENTRATION",
                name="alert_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "condition",
            sa.Enum("ABOVE", "BELOW", "PERCENT_CHANGE", name="alert_condition"),
            nullable=False,
        ),
        sa.Column("threshold", sa.Numeric(20, 8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"], unique=False)
    op.create_index("ix_alerts_asset_id", "alerts", ["asset_id"], unique=False)
    op.create_index("ix_alerts_portfolio_id", "alerts", ["portfolio_id"], unique=False)

    op.create_table(
        "alert_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trigger_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_events_alert_id", "alert_events", ["alert_id"], unique=False)
    op.create_index("ix_alert_events_triggered_at", "alert_events", ["triggered_at"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_event_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.Enum("EMAIL", name="notification_channel"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "SENT", "FAILED", name="notification_status"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["alert_event_id"], ["alert_events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_event_id", name="uq_notifications_alert_event_id"),
    )
    op.create_index("ix_notifications_alert_event_id", "notifications", ["alert_event_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notifications_alert_event_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_alert_events_triggered_at", table_name="alert_events")
    op.drop_index("ix_alert_events_alert_id", table_name="alert_events")
    op.drop_table("alert_events")
    op.drop_index("ix_alerts_portfolio_id", table_name="alerts")
    op.drop_index("ix_alerts_asset_id", table_name="alerts")
    op.drop_index("ix_alerts_user_id", table_name="alerts")
    op.drop_table("alerts")
    op.execute("DROP TYPE IF EXISTS notification_status")
    op.execute("DROP TYPE IF EXISTS notification_channel")
    op.execute("DROP TYPE IF EXISTS alert_condition")
    op.execute("DROP TYPE IF EXISTS alert_type")
