"""catalog_terms: maestras de proceso/categoría/tipo, sembradas desde los valores
actuales de projects (normalizando variantes de mayúsculas).

Revision ID: 0026_catalog_terms
Revises: 0025_progress_snapshots
Create Date: 2026-07-03

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026_catalog_terms"
down_revision: Union[str, None] = "0025_progress_snapshots"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None

# maestra -> columna de projects
_KINDS = {"process": "process", "category": "category", "project_type": "project_type"}


def _norm(value: str) -> str:
    return (value or "").strip().upper()


def upgrade() -> None:
    op.create_table(
        "catalog_terms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("norm", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_catalog_terms_kind", "catalog_terms", ["kind"])
    op.create_unique_constraint("uq_catalog_kind_norm", "catalog_terms", ["kind", "norm"])

    bind = op.get_bind()
    for kind, col in _KINDS.items():
        rows = bind.execute(
            sa.text(
                f"SELECT {col} AS v, count(*) AS c FROM projects "
                f"WHERE {col} IS NOT NULL AND btrim({col}) <> '' GROUP BY {col}"
            )
        ).fetchall()
        # Agrupa variantes por su forma normalizada (mayúsculas, sin bordes).
        groups: dict[str, list[tuple[str, int]]] = {}
        for value, count in rows:
            groups.setdefault(_norm(value), []).append((value, count))
        for norm, variants in groups.items():
            # Canónico = variante más frecuente; desempate alfabético.
            variants.sort(key=lambda x: (-x[1], x[0]))
            canonical = variants[0][0].strip()
            bind.execute(
                sa.text("INSERT INTO catalog_terms (kind, name, norm) VALUES (:k, :nm, :n)"),
                {"k": kind, "nm": canonical, "n": norm},
            )
            # Normaliza los proyectos a la forma canónica.
            bind.execute(
                sa.text(
                    f"UPDATE projects SET {col} = :nm "
                    f"WHERE upper(btrim({col})) = :n AND {col} <> :nm"
                ),
                {"nm": canonical, "n": norm},
            )


def downgrade() -> None:
    op.drop_constraint("uq_catalog_kind_norm", "catalog_terms", type_="unique")
    op.drop_index("ix_catalog_terms_kind", table_name="catalog_terms")
    op.drop_table("catalog_terms")
