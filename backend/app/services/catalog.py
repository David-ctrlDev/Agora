"""Maestras de valores (proceso, categoría, tipo) para elegir en los proyectos."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog_term import CatalogTerm

KINDS = {"process", "category", "project_type"}


class InvalidKind(Exception):
    pass


class InvalidName(Exception):
    pass


class TermExists(Exception):
    pass


def _norm(value: str) -> str:
    return (value or "").strip().upper()


async def list_terms(
    db: AsyncSession, kind: str, *, active_only: bool = False
) -> list[CatalogTerm]:
    if kind not in KINDS:
        raise InvalidKind()
    stmt = select(CatalogTerm).where(CatalogTerm.kind == kind)
    if active_only:
        stmt = stmt.where(CatalogTerm.is_active.is_(True))
    return list((await db.execute(stmt.order_by(CatalogTerm.name))).scalars().all())


async def create_term(db: AsyncSession, kind: str, name: str) -> CatalogTerm:
    if kind not in KINDS:
        raise InvalidKind()
    name = (name or "").strip()
    norm = _norm(name)
    if not norm:
        raise InvalidName()
    existing = (
        await db.execute(
            select(CatalogTerm).where(CatalogTerm.kind == kind, CatalogTerm.norm == norm)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise TermExists()
    term = CatalogTerm(kind=kind, name=name, norm=norm)
    db.add(term)
    await db.commit()
    await db.refresh(term)
    return term


async def delete_term(db: AsyncSession, term_id: int) -> bool:
    term = await db.get(CatalogTerm, term_id)
    if term is None:
        return False
    await db.delete(term)
    await db.commit()
    return True
