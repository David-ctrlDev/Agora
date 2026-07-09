from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import decode_session_token
from app.models.user import User
from app.models.user_area import UserArea


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    user_id = decode_session_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida")
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no válido")
    return user


# Roles por área que otorgan administración del área (además de la visibilidad).
AREA_ADMIN_ROLES = ("lead", "admin")


def is_superadmin(user: User) -> bool:
    """Super administrador global. Se define por CONFIGURACIÓN (lista de correos),
    no por un rol en la BD, para que nadie se vuelva super admin por error."""
    return (user.email or "").strip().lower() in settings.superadmin_email_set


async def require_superadmin(user: User = Depends(get_current_user)) -> User:
    if not is_superadmin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Requiere super administrador"
        )
    return user


async def get_user_area_ids(db: AsyncSession, user: User) -> list[int] | None:
    """IDs de áreas VISIBLES por el usuario. None = sin restricción (super admin)."""
    if is_superadmin(user):
        return None
    result = await db.execute(select(UserArea.area_id).where(UserArea.user_id == user.id))
    return [row[0] for row in result.all()]


async def admin_area_ids(db: AsyncSession, user: User) -> list[int] | None:
    """IDs de áreas que el usuario ADMINISTRA. None = todas (super admin).
    Un administrador de área es quien tiene rol de área lead/admin en esa área."""
    if is_superadmin(user):
        return None
    result = await db.execute(
        select(UserArea.area_id).where(
            UserArea.user_id == user.id, UserArea.area_role.in_(AREA_ADMIN_ROLES)
        )
    )
    return [row[0] for row in result.all()]


async def require_area_admin(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> User:
    """Permite super admin o cualquier administrador de área (de ≥1 área)."""
    ids = await admin_area_ids(db, user)
    if ids is None or len(ids) > 0:
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Requiere administrador de área"
    )


async def require_costs_access(user: User = Depends(get_current_user)) -> User:
    """Módulo de costos: super admin o usuarios habilitados por él."""
    if is_superadmin(user) or user.can_view_costs:
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso al módulo de costos"
    )
