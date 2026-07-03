"""project_progress_snapshots (histórico de avance para seguimiento trimestral)

Revision ID: 0025_progress_snapshots
Revises: 0024_user_last_login
Create Date: 2026-07-03

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0025_progress_snapshots"
down_revision: Union[str, None] = "0024_user_last_login"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "project_progress_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_project_progress_snapshots_project_id",
        "project_progress_snapshots",
        ["project_id"],
    )
    op.create_index(
        "ix_project_progress_snapshots_captured_at",
        "project_progress_snapshots",
        ["captured_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_progress_snapshots_captured_at", table_name="project_progress_snapshots"
    )
    op.drop_index(
        "ix_project_progress_snapshots_project_id", table_name="project_progress_snapshots"
    )
    op.drop_table("project_progress_snapshots")
