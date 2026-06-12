"""trade and position module tables

Revision ID: 20260610_0005
Revises: 20260610_0004
Create Date: 2026-06-10 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260610_0005"
down_revision: Union[str, None] = "20260610_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

trade_type_enum = postgresql.ENUM(
    "BUY",
    "SELL",
    "SHORT",
    "COVER",
    name="trade_type",
    create_type=False,
)

position_type_enum = postgresql.ENUM(
    "LONG",
    "SHORT",
    name="position_type",
    create_type=False,
)

position_status_enum = postgresql.ENUM(
    "OPEN",
    "CLOSED",
    name="position_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM("BUY", "SELL", "SHORT", "COVER", name="trade_type").create(bind, checkfirst=True)
    postgresql.ENUM("LONG", "SHORT", name="position_type").create(bind, checkfirst=True)
    postgresql.ENUM("OPEN", "CLOSED", name="position_status").create(bind, checkfirst=True)

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("position_type", position_type_enum, nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("average_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("total_cost", sa.Numeric(20, 8), nullable=False),
        sa.Column("status", position_status_enum, nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("portfolio_id", "asset_id", name="uq_positions_portfolio_asset"),
    )
    op.create_index("ix_positions_portfolio_id", "positions", ["portfolio_id"], unique=False)
    op.create_index("ix_positions_asset_id", "positions", ["asset_id"], unique=False)

    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.Integer(), nullable=True),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("trade_type", trade_type_enum, nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("price", sa.Numeric(20, 8), nullable=False),
        sa.Column("fees", sa.Numeric(20, 8), nullable=False, server_default=sa.text("0")),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trades_portfolio_id", "trades", ["portfolio_id"], unique=False)
    op.create_index("ix_trades_position_id", "trades", ["position_id"], unique=False)
    op.create_index("ix_trades_asset_id", "trades", ["asset_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("ix_trades_asset_id", table_name="trades")
    op.drop_index("ix_trades_position_id", table_name="trades")
    op.drop_index("ix_trades_portfolio_id", table_name="trades")
    op.drop_table("trades")
    op.drop_index("ix_positions_asset_id", table_name="positions")
    op.drop_index("ix_positions_portfolio_id", table_name="positions")
    op.drop_table("positions")
    postgresql.ENUM("OPEN", "CLOSED", name="position_status").drop(bind, checkfirst=True)
    postgresql.ENUM("LONG", "SHORT", name="position_type").drop(bind, checkfirst=True)
    postgresql.ENUM("BUY", "SELL", "SHORT", "COVER", name="trade_type").drop(bind, checkfirst=True)
