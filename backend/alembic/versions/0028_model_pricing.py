"""model_pricing: tarifa por modelo (USD/1M tokens in y out), editable por el super admin

Revision ID: 0028_model_pricing
Revises: 0027_agent_token_usage
Create Date: 2026-07-04

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0028_model_pricing"
down_revision: Union[str, None] = "0027_agent_token_usage"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "model_pricing",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model", sa.String(length=80), nullable=False, unique=True),
        sa.Column("input_per_1m", sa.Float(), nullable=False, server_default="0"),
        sa.Column("output_per_1m", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    # Semilla: tarifa del modelo de chat actual (ajustable luego desde el módulo de Costos).
    op.get_bind().execute(
        sa.text(
            "INSERT INTO model_pricing (model, input_per_1m, output_per_1m) "
            "VALUES ('gemini-flash-latest', 0.10, 0.40)"
        )
    )


def downgrade() -> None:
    op.drop_table("model_pricing")
