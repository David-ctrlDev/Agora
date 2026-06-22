from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_admin
from app.models.area import Area
from app.models.user import User
from app.schemas.admin import (
    AdminAreaUpdate,
    AdminStats,
    AdminUserCreate,
    AdminUserRead,
    AdminUserUpdate,
    UserAreasSet,
)
from app.schemas.area import AreaCreate, AreaRead
from app.services import admin as admin_svc
from app.services import areas as areas_service

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/stats", response_model=AdminStats)
async def stats(db: AsyncSession = Depends(get_db)) -> AdminStats:
    return await admin_svc.system_stats(db)


async def _get_user(user_id: int, db: AsyncSession) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return user


@router.get("/users", response_model=list[AdminUserRead])
async def list_users(db: AsyncSession = Depends(get_db)) -> list[AdminUserRead]:
    return await admin_svc.list_users(db)


@router.post("/users", response_model=AdminUserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: AdminUserCreate, db: AsyncSession = Depends(get_db)) -> AdminUserRead:
    try:
        return await admin_svc.create_user(db, payload)
    except admin_svc.EmailExists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese correo"
        ) from None


@router.patch("/users/{user_id}", response_model=AdminUserRead)
async def update_user(
    user_id: int, payload: AdminUserUpdate, db: AsyncSession = Depends(get_db)
) -> AdminUserRead:
    user = await _get_user(user_id, db)
    return await admin_svc.update_user(db, user, payload)


@router.put("/users/{user_id}/areas", response_model=AdminUserRead)
async def set_user_areas(
    user_id: int, payload: UserAreasSet, db: AsyncSession = Depends(get_db)
) -> AdminUserRead:
    user = await _get_user(user_id, db)
    return await admin_svc.set_user_areas(db, user, payload.areas)


@router.post("/users/{user_id}/reset-2fa", response_model=AdminUserRead)
async def reset_user_2fa(user_id: int, db: AsyncSession = Depends(get_db)) -> AdminUserRead:
    user = await _get_user(user_id, db)
    return await admin_svc.reset_2fa(db, user)


@router.get("/areas", response_model=list[AreaRead])
async def list_areas(db: AsyncSession = Depends(get_db)) -> list[Area]:
    return list((await db.execute(select(Area).order_by(Area.name))).scalars().all())


@router.post("/areas", response_model=AreaRead, status_code=status.HTTP_201_CREATED)
async def create_area(payload: AreaCreate, db: AsyncSession = Depends(get_db)) -> Area:
    try:
        return await areas_service.create_area(db, payload)
    except areas_service.AreaSlugExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/areas/{area_id}", response_model=AreaRead)
async def update_area(
    area_id: int, payload: AdminAreaUpdate, db: AsyncSession = Depends(get_db)
) -> Area:
    area = await db.get(Area, area_id)
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Área no encontrada")
    if payload.name is not None:
        area.name = payload.name.strip()
    if payload.description is not None:
        area.description = payload.description
    if payload.is_active is not None:
        area.is_active = payload.is_active
    await db.commit()
    await db.refresh(area)
    return area
