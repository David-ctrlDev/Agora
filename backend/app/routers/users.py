from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserRead])
async def list_users(
    _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[User]:
    """Lista de usuarios activos (para asignar miembros/responsables)."""
    result = await db.execute(select(User).where(User.is_active.is_(True)).order_by(User.name))
    return list(result.scalars().all())
