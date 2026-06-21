"""store uploaded file content and metadata on documents

Revision ID: 0013_document_files
Revises: 0012_economics
Create Date: 2026-06-21

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_document_files"
down_revision: Union[str, None] = "0012_economics"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("file_name", sa.String(length=300), nullable=True))
    op.add_column("documents", sa.Column("mime_type", sa.String(length=120), nullable=True))
    op.add_column("documents", sa.Column("content_text", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("file_data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "file_data")
    op.drop_column("documents", "content_text")
    op.drop_column("documents", "mime_type")
    op.drop_column("documents", "file_name")
