"""market module tables

Revision ID: 20260610_0006
Revises: 20260610_0005
Create Date: 2026-06-10 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260610_0006"
down_revision: Union[str, None] = "20260610_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_prices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(20, 8), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_prices_asset_id", "market_prices", ["asset_id"], unique=False)
    op.create_index("ix_market_prices_timestamp", "market_prices", ["timestamp"], unique=False)

    op.create_table(
        "news",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url", name="uq_news_url"),
    )
    op.create_index("ix_news_asset_id", "news", ["asset_id"], unique=False)
    op.create_index("ix_news_published_at", "news", ["published_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_news_published_at", table_name="news")
    op.drop_index("ix_news_asset_id", table_name="news")
    op.drop_table("news")
    op.drop_index("ix_market_prices_timestamp", table_name="market_prices")
    op.drop_index("ix_market_prices_asset_id", table_name="market_prices")
    op.drop_table("market_prices")
