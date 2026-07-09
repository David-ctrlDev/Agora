"""agent_token_usage.tool_tokens (tokens de herramientas reportados por Gemini)

Revision ID: 0030_tool_tokens
Revises: 0029_token_cost_detail
Create Date: 2026-07-09

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0030_tool_tokens"
down_revision: Union[str, None] = "0029_token_cost_detail"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "agent_token_usage",
        sa.Column("tool_tokens", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("agent_token_usage", "tool_tokens")
