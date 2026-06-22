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


async def get_or_create_google_user(
    db: AsyncSession,
    *,
    email: str,
    sub: str | None,
    name: str | None,
    avatar_url: str | None,
) -> User:
    """Encuentra (por email o google_sub) o crea el usuario tras autenticar con Google."""
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None and sub:
        user = (await db.execute(select(User).where(User.google_sub == sub))).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            name=name or email,
            google_sub=sub,
            avatar_url=avatar_url,
            role="member",
            is_active=True,
        )
        db.add(user)
    else:
        if sub and not user.google_sub:
            user.google_sub = sub
        if avatar_url:
            user.avatar_url = avatar_url
        if name and (not user.name or user.name == user.email):
            user.name = name
    await db.flush()
    return user
