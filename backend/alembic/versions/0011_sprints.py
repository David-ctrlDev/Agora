"""create sprints table and link tasks

Revision ID: 0011_sprints
Revises: 0010_notifications
Create Date: 2026-06-21

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_sprints"
down_revision: Union[str, None] = "0010_notifications"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "sprints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="planned"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sprints_project_id", "sprints", ["project_id"])

    op.add_column("tasks", sa.Column("sprint_id", sa.Integer(), nullable=True))
    op.add_column("tasks", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_tasks_sprint_id", "tasks", "sprints", ["sprint_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_tasks_sprint_id", "tasks", ["sprint_id"])
    # Backfill: las tareas ya cerradas se dan por completadas en su última actualización.
    op.execute("UPDATE tasks SET completed_at = updated_at WHERE status = 'done'")


def downgrade() -> None:
    op.drop_index("ix_tasks_sprint_id", table_name="tasks")
    op.drop_constraint("fk_tasks_sprint_id", "tasks", type_="foreignkey")
    op.drop_column("tasks", "completed_at")
    op.drop_column("tasks", "sprint_id")
    op.drop_index("ix_sprints_project_id", table_name="sprints")
    op.drop_table("sprints")
