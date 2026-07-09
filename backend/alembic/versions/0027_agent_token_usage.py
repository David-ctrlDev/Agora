"""agent_token_usage (consumo de tokens del agente) + users.can_view_costs

Revision ID: 0027_agent_token_usage
Revises: 0026_catalog_terms
Create Date: 2026-07-04

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0027_agent_token_usage"
down_revision: Union[str, None] = "0026_catalog_terms"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "agent_token_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_agent_token_usage_user_id", "agent_token_usage", ["user_id"])
    op.create_index("ix_agent_token_usage_created_at", "agent_token_usage", ["created_at"])

    op.add_column(
        "users",
        sa.Column("can_view_costs", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "can_view_costs")
    op.drop_index("ix_agent_token_usage_created_at", table_name="agent_token_usage")
    op.drop_index("ix_agent_token_usage_user_id", table_name="agent_token_usage")
    op.drop_table("agent_token_usage")
