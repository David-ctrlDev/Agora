from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import is_superadmin
from app.models.area import Area
from app.models.user import User
from app.models.user_area import UserArea


def _auto_provision_allowed(email: str) -> bool:
    """¿Se puede auto-crear esta cuenta? Solo si la auto-provisión está activada y el
    correo pertenece al dominio permitido (la frontera de seguridad)."""
    if not settings.google_auto_provision:
        return False
    hd = (settings.google_allowed_hd or "").strip().lower()
    if not hd:
        return False  # sin dominio configurado NO auto-creamos (no abrir a cualquiera)
    return (email or "").strip().lower().endswith("@" + hd)


async def accessible_areas(db: AsyncSession, user: User) -> list[tuple[Area, str]]:
    """Áreas accesibles por el usuario, con su rol en cada una.

    Super admin: todas las áreas activas. Resto: sus `user_areas`.
    """
    if is_superadmin(user):
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


async def resolve_google_user(
    db: AsyncSession,
    *,
    email: str,
    sub: str | None,
    name: str | None,
    avatar_url: str | None,
) -> User | None:
    """Encuentra (o auto-crea) al usuario tras autenticar con Google.

    Si el correo pertenece al dominio permitido y no existe, se crea como 'member'
    activo (auto-provisión). Un usuario DESACTIVADO por un admin no puede entrar.
    Devuelve None si no existe y el dominio no permite auto-provisión.
    """
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None and sub:
        user = (await db.execute(select(User).where(User.google_sub == sub))).scalar_one_or_none()
    if user is None:
        if not _auto_provision_allowed(email):
            return None
        user = User(
            email=email.strip().lower(),
            name=name or email,
            google_sub=sub,
            avatar_url=avatar_url,
            role="member",
            is_active=True,
        )
        db.add(user)
        await db.flush()
        return user
    if not user.is_active:
        return None
    if sub and not user.google_sub:
        user.google_sub = sub
    if avatar_url:
        user.avatar_url = avatar_url
    if name and (not user.name or user.name == user.email):
        user.name = name
    await db.flush()
    return user
