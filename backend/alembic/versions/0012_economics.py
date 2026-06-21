"""add project economics (cost/benefit)

Revision ID: 0012_economics
Revises: 0011_sprints
Create Date: 2026-06-21

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_economics"
down_revision: Union[str, None] = "0011_sprints"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("estimated_cost", sa.Float(), nullable=True))
    op.add_column("projects", sa.Column("actual_cost", sa.Float(), nullable=True))
    op.add_column("projects", sa.Column("expected_benefit", sa.Float(), nullable=True))
    op.add_column("projects", sa.Column("actual_benefit", sa.Float(), nullable=True))
    op.add_column(
        "projects",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="COP"),
    )


def downgrade() -> None:
    op.drop_column("projects", "currency")
    op.drop_column("projects", "actual_benefit")
    op.drop_column("projects", "expected_benefit")
    op.drop_column("projects", "actual_cost")
    op.drop_column("projects", "estimated_cost")
