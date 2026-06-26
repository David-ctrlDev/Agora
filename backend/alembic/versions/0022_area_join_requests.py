"""Self-service area onboarding: join / new-area requests

Revision ID: 0022_area_join_requests
Revises: 0021_project_drive_docs
Create Date: 2026-06-26

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0022_area_join_requests"
down_revision: Union[str, None] = "0021_project_drive_docs"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "area_join_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="join"),
        sa.Column(
            "area_id",
            sa.Integer(),
            sa.ForeignKey("areas.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("proposed_name", sa.String(length=120), nullable=True),
        sa.Column("proposed_description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "decided_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_area_join_requests_user_id", "area_join_requests", ["user_id"])
    op.create_index("ix_area_join_requests_area_id", "area_join_requests", ["area_id"])
    op.create_index("ix_area_join_requests_status", "area_join_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_area_join_requests_status", table_name="area_join_requests")
    op.drop_index("ix_area_join_requests_area_id", table_name="area_join_requests")
    op.drop_index("ix_area_join_requests_user_id", table_name="area_join_requests")
    op.drop_table("area_join_requests")
