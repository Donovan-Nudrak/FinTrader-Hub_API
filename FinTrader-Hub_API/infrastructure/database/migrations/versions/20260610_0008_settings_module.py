"""settings module tables

Revision ID: 20260610_0008
Revises: 20260610_0007
Create Date: 2026-06-11 08:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260610_0008"
down_revision: Union[str, None] = "20260610_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("alert_email", sa.String(length=255), nullable=True),
        sa.Column("dashboard_refresh_interval", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_settings_user_id"),
    )
    op.create_index("ix_user_settings_user_id", "user_settings", ["user_id"], unique=False)

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column(
            "provider",
            sa.Enum(
                "FINNHUB",
                "COINGECKO",
                "ALPHA_VANTAGE",
                "EXCHANGE_RATE",
                name="api_key_provider",
            ),
            nullable=False,
        ),
        sa.Column("key_value", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index("ix_user_settings_user_id", table_name="user_settings")
    op.drop_table("user_settings")
    op.execute("DROP TYPE IF EXISTS api_key_provider")
