from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Area
from app.models.user import User
from app.models.user_area import UserArea


async def accessible_areas(db: AsyncSession, user: User) -> list[tuple[Area, str]]:
    """Áreas accesibles por el usuario, con su rol en cada una.

    Admin global: todas las áreas activas (rol 'admin'). Miembro: sus `user_areas`.
    """
    if user.role == "admin":
        result = await db.execute(
            select(Area).where(Area.is_active.is_(True)).order_by(Area.name)
        )
        return [(area, "admin") for area in result.scalars().all()]

    result = await db.execute(
        select(Area, UserArea.area_role)
        .join(UserArea, UserArea.area_id == Area.id)
        .where(UserArea.user_id == user.id)
        .order_by(Area.name)
    )
    return [(area, area_role) for area, area_role in result.all()]


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.role, User.name))
    return list(result.scalars().all())
