"""Ajustes (tasks.is_adjustment), proyecto padre (projects.parent_id) y
levantamiento de requerimientos (projects.requirements).

Revision ID: 0032_adjust_parent_reqs
Revises: 0031_project_is_development
Create Date: 2026-07-15

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0032_adjust_parent_reqs"
down_revision: Union[str, None] = "0031_project_is_development"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("is_adjustment", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "projects",
        sa.Column(
            "parent_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_projects_parent_id", "projects", ["parent_id"])
    op.add_column("projects", sa.Column("requirements", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "requirements")
    op.drop_index("ix_projects_parent_id", table_name="projects")
    op.drop_column("projects", "parent_id")
    op.drop_column("tasks", "is_adjustment")
