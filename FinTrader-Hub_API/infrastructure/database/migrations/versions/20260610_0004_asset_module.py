"""asset module table

Revision ID: 20260610_0004
Revises: 20260610_0003
Create Date: 2026-06-10 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260610_0004"
down_revision: Union[str, None] = "20260610_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

asset_type_enum = postgresql.ENUM(
    "STOCK",
    "CRYPTO",
    "FOREX",
    "FUTURE",
    "OPTION",
    "ETF",
    "INDEX",
    name="asset_type",
    create_type=False,
)

market_type_enum = postgresql.ENUM(
    "NYSE",
    "NASDAQ",
    "CRYPTO",
    "FOREX",
    "CME",
    "BINANCE",
    name="market_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "STOCK",
        "CRYPTO",
        "FOREX",
        "FUTURE",
        "OPTION",
        "ETF",
        "INDEX",
        name="asset_type",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "NYSE",
        "NASDAQ",
        "CRYPTO",
        "FOREX",
        "CME",
        "BINANCE",
        name="market_type",
    ).create(bind, checkfirst=True)

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("market", market_type_enum, nullable=False),
        sa.Column("asset_type", asset_type_enum, nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol"),
    )
    op.create_index("ix_assets_symbol", "assets", ["symbol"], unique=False)
    op.create_index("ix_assets_name", "assets", ["name"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("ix_assets_name", table_name="assets")
    op.drop_index("ix_assets_symbol", table_name="assets")
    op.drop_table("assets")
    postgresql.ENUM(
        "NYSE",
        "NASDAQ",
        "CRYPTO",
        "FOREX",
        "CME",
        "BINANCE",
        name="market_type",
    ).drop(bind, checkfirst=True)
    postgresql.ENUM(
        "STOCK",
        "CRYPTO",
        "FOREX",
        "FUTURE",
        "OPTION",
        "ETF",
        "INDEX",
        name="asset_type",
    ).drop(bind, checkfirst=True)
