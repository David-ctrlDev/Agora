"""Maestra de iniciativas: siembra catalog_terms(kind='initiative') desde los
valores actuales de projects.initiative, normalizando variantes de mayúsculas.

Revision ID: 0033_initiative_catalog
Revises: 0032_adjust_parent_reqs
Create Date: 2026-07-15

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0033_initiative_catalog"
down_revision: Union[str, None] = "0032_adjust_parent_reqs"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[str, None] = None


def _norm(value: str) -> str:
    return (value or "").strip().upper()


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT initiative AS v, count(*) AS c FROM projects "
            "WHERE initiative IS NOT NULL AND btrim(initiative) <> '' GROUP BY initiative"
        )
    ).fetchall()
    groups: dict[str, list[tuple[str, int]]] = {}
    for value, count in rows:
        groups.setdefault(_norm(value), []).append((value, count))
    for norm, variants in groups.items():
        variants.sort(key=lambda x: (-x[1], x[0]))
        canonical = variants[0][0].strip()
        bind.execute(
            sa.text(
                "INSERT INTO catalog_terms (kind, name, norm) VALUES ('initiative', :nm, :n) "
                "ON CONFLICT DO NOTHING"
            ),
            {"nm": canonical, "n": norm},
        )
        bind.execute(
            sa.text(
                "UPDATE projects SET initiative = :nm "
                "WHERE upper(btrim(initiative)) = :n AND initiative <> :nm"
            ),
            {"nm": canonical, "n": norm},
        )


def downgrade() -> None:
    op.get_bind().execute(sa.text("DELETE FROM catalog_terms WHERE kind = 'initiative'"))
