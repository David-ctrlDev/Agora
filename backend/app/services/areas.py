import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Area
from app.schemas.area import AreaCreate


class AreaSlugExists(Exception):
    """Ya existe un área con el mismo slug."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"Ya existe un área con el slug '{slug}'.")


def slugify(value: str) -> str:
    """Genera un slug ASCII a partir del nombre (p. ej. 'Producción' -> 'produccion')."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)


async def list_areas(db: AsyncSession) -> list[Area]:
    result = await db.execute(select(Area).order_by(Area.name))
    return list(result.scalars().all())


async def create_area(db: AsyncSession, payload: AreaCreate) -> Area:
    area = Area(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        slug=slugify(payload.name),
    )
    db.add(area)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AreaSlugExists(area.slug) from exc
    await db.refresh(area)
    return area
