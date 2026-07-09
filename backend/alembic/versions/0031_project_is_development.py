"""projects.is_development (habilita la pestaña Código / repo Git interno)

Revision ID: 0031_project_is_development
Revises: 0030_tool_tokens
Create Date: 2026-07-09

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0031_project_is_development"
down_revision: Union[str, None] = "0030_tool_tokens"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("is_development", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("projects", "is_development")
