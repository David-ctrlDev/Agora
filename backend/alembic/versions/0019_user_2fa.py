"""two-factor (TOTP) fields on users

Revision ID: 0019_user_2fa
Revises: 0018_project_roadmap_fields
Create Date: 2026-06-21

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019_user_2fa"
down_revision: Union[str, None] = "0018_project_roadmap_fields"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
