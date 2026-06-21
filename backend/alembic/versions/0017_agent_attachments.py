"""agent conversation attachments

Revision ID: 0017_agent_attachments
Revises: 0016_project_progress
Create Date: 2026-06-21

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_agent_attachments"
down_revision: Union[str, None] = "0016_project_progress"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "agent_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="upload"),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["agent_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_attachments_conversation_id", "agent_attachments", ["conversation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_agent_attachments_conversation_id", table_name="agent_attachments")
    op.drop_table("agent_attachments")
