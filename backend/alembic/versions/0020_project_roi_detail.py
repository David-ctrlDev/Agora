"""richer ROI: executor (process that does it) vs beneficiary (process it's for)

Revision ID: 0020_project_roi_detail
Revises: 0019_user_2fa
Create Date: 2026-06-22

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_project_roi_detail"
down_revision: Union[str, None] = "0019_user_2fa"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None

# Lado ejecutor (el proceso que lo hace) + lado beneficiario (para el que se hace).
_COLUMNS = [
    # Ejecutor: inversión no monetaria.
    ("effort_hours_estimated", sa.Float()),
    ("effort_hours_actual", sa.Float()),
    ("executor_team", sa.String(length=200)),
    ("implementation_complexity", sa.String(length=20)),
    ("resources_needed", sa.Text()),
    # Beneficiario: a quién/qué proceso sirve y su retorno no monetario.
    ("beneficiary_area_id", sa.Integer()),
    ("beneficiary_process", sa.String(length=160)),
    ("hours_saved_monthly", sa.Float()),
    ("people_impacted", sa.Integer()),
    ("risk_reduction", sa.String(length=20)),
    ("strategic_value", sa.String(length=20)),
]

_FK = "fk_projects_beneficiary_area"


def upgrade() -> None:
    for name, col_type in _COLUMNS:
        op.add_column("projects", sa.Column(name, col_type, nullable=True))
    op.create_foreign_key(
        _FK, "projects", "areas", ["beneficiary_area_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint(_FK, "projects", type_="foreignkey")
    for name, _ in reversed(_COLUMNS):
        op.drop_column("projects", name)
