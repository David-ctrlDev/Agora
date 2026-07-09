"""Detalle de costo: tokens de pensamiento y caché + tarifa de caché por modelo

Revision ID: 0029_token_cost_detail
Revises: 0028_model_pricing
Create Date: 2026-07-04

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029_token_cost_detail"
down_revision: Union[str, None] = "0028_model_pricing"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "agent_token_usage",
        sa.Column("thought_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "agent_token_usage",
        sa.Column("cached_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("model_pricing", sa.Column("cached_per_1m", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("model_pricing", "cached_per_1m")
    op.drop_column("agent_token_usage", "cached_tokens")
    op.drop_column("agent_token_usage", "thought_tokens")
