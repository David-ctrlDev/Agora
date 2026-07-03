"""users.last_login_at (sello del último ingreso, para auditoría en admin)

Revision ID: 0024_user_last_login
Revises: 0023_user_avatar_text
Create Date: 2026-07-02

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024_user_last_login"
down_revision: Union[str, None] = "0023_user_avatar_text"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
