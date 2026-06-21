"""roadmap fields on projects (from the planning Excel)

Revision ID: 0018_project_roadmap_fields
Revises: 0017_agent_attachments
Create Date: 2026-06-21

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018_project_roadmap_fields"
down_revision: Union[str, None] = "0017_agent_attachments"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None

_COLUMNS = [
    ("initiative", sa.String(length=120)),
    ("proposed_by", sa.String(length=160)),
    ("project_type", sa.String(length=60)),
    ("category", sa.String(length=80)),
    ("criticality", sa.String(length=20)),
    ("process", sa.String(length=120)),
    ("benefits", sa.Text()),
    ("change_management", sa.String(length=20)),
]


def upgrade() -> None:
    for name, col_type in _COLUMNS:
        op.add_column("projects", sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(_COLUMNS):
        op.drop_column("projects", name)
