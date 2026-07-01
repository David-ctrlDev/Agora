"""users.avatar_url -> Text (las URLs de avatar de Google superan varchar(512))

Revision ID: 0023_user_avatar_text
Revises: 0022_area_join_requests
Create Date: 2026-07-01

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023_user_avatar_text"
down_revision: Union[str, None] = "0022_area_join_requests"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.alter_column(
        "users", "avatar_url", type_=sa.Text(), existing_type=sa.String(length=512), existing_nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        "users", "avatar_url", type_=sa.String(length=512), existing_type=sa.Text(), existing_nullable=True
    )
