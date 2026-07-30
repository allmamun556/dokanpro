"""add waiter chef roles and loyalty redemption

Revision ID: 513462244ff7
Revises: 472cc6b45294
Create Date: 2026-07-29 08:57:26.746738

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '513462244ff7'
down_revision: Union[str, None] = '472cc6b45294'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside Postgres's implicit
    # transaction block, so each needs its own autocommit block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE roleenum ADD VALUE IF NOT EXISTS 'waiter'")
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE roleenum ADD VALUE IF NOT EXISTS 'chef'")

    op.add_column("orders", sa.Column("loyalty_points_redeemed", sa.Integer(), nullable=True))


def downgrade() -> None:
    # PostgreSQL cannot remove values from an existing enum type (no
    # ALTER TYPE ... DROP VALUE) — the only true reversal is manually
    # dropping and recreating the roleenum type, a DBA-supervised operation.
    raise NotImplementedError(
        "Cannot downgrade: PostgreSQL does not support removing enum values "
        "('waiter'/'chef' from roleenum). Manual intervention required."
    )
