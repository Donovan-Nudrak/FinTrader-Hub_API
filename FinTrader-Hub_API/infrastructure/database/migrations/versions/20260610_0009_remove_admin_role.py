"""remove unused admin role

Revision ID: 20260610_0009
Revises: 20260610_0008
Create Date: 2026-06-12 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260610_0009"
down_revision: Union[str, None] = "20260610_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM roles
            WHERE name = 'admin'
              AND NOT EXISTS (
                  SELECT 1 FROM users WHERE users.role_id = roles.id
              )
            """,
        ),
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO roles (name, description, created_at, updated_at)
            SELECT 'admin', 'Administrator role', NOW(), NOW()
            WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = 'admin')
            """,
        ),
    )
