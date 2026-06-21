"""create github_repos and github_events tables

Revision ID: 0006_github
Revises: 0005_task_comments
Create Date: 2026-06-20

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_github"
down_revision: Union[str, None] = "0005_task_comments"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "github_repos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("html_url", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_id", "full_name", name="uq_github_repo_project_fullname"),
    )
    op.create_index("ix_github_repos_project_id", "github_repos", ["project_id"])

    op.create_table(
        "github_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("html_url", sa.String(length=512), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["repo_id"], ["github_repos.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("repo_id", "external_id", name="uq_github_event_repo_external"),
    )
    op.create_index("ix_github_events_repo_id", "github_events", ["repo_id"])
    op.create_index("ix_github_events_occurred_at", "github_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_github_events_occurred_at", table_name="github_events")
    op.drop_index("ix_github_events_repo_id", table_name="github_events")
    op.drop_table("github_events")
    op.drop_index("ix_github_repos_project_id", table_name="github_repos")
    op.drop_table("github_repos")
