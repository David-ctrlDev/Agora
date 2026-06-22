"""Drive as project documentation filesystem: folder per project + file sync tracking

Revision ID: 0021_project_drive_docs
Revises: 0020_project_roi_detail
Create Date: 2026-06-22

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021_project_drive_docs"
down_revision: Union[str, None] = "0020_project_roi_detail"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Carpeta de Drive que actúa como documentación del proyecto.
    op.add_column("projects", sa.Column("docs_folder_id", sa.String(length=120), nullable=True))
    # Vínculo de cada documento indexado con su archivo en Drive (para sync/re-vectorizado).
    op.add_column("documents", sa.Column("drive_file_id", sa.String(length=120), nullable=True))
    op.add_column("documents", sa.Column("drive_checksum", sa.String(length=64), nullable=True))
    op.add_column(
        "documents", sa.Column("drive_synced_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("ix_documents_drive_file_id", "documents", ["drive_file_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_drive_file_id", table_name="documents")
    op.drop_column("documents", "drive_synced_at")
    op.drop_column("documents", "drive_checksum")
    op.drop_column("documents", "drive_file_id")
    op.drop_column("projects", "docs_folder_id")
