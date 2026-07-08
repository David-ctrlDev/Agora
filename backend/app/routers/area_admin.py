from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_area_admin
from app.models.user import User
from app.schemas.area_admin import (
    AreaAdminActivity,
    AreaAdminMembers,
    AreaAdminScope,
    AreaAdminStats,
    AreaMemberSet,
)
from app.schemas.task import TaskSummary
from app.services import area_admin as svc
from app.services import tasks as tasks_svc

router = APIRouter(
    prefix="/api/area-admin", tags=["area-admin"], dependencies=[Depends(require_area_admin)]
)


@router.get("/scope", response_model=AreaAdminScope)
async def scope(
    user: User = Depends(require_area_admin), db: AsyncSession = Depends(get_db)
) -> AreaAdminScope:
    return await svc.scope(db, user)


@router.get("/stats", response_model=AreaAdminStats)
async def stats(
    user: User = Depends(require_area_admin), db: AsyncSession = Depends(get_db)
) -> AreaAdminStats:
    return await svc.stats(db, user)


@router.get("/activity", response_model=AreaAdminActivity)
async def activity(
    limit: int = 10,
    user: User = Depends(require_area_admin),
    db: AsyncSession = Depends(get_db),
) -> AreaAdminActivity:
    return await svc.activity(db, user, limit=min(max(limit, 1), 50))


@router.get("/tasks", response_model=TaskSummary)
async def tasks(
    user: User = Depends(require_area_admin), db: AsyncSession = Depends(get_db)
) -> TaskSummary:
    pids = await svc.administered_project_ids(db, user)
    return await tasks_svc.task_summary(db, pids)


@router.get("/members", response_model=AreaAdminMembers)
async def members(
    user: User = Depends(require_area_admin), db: AsyncSession = Depends(get_db)
) -> AreaAdminMembers:
    return await svc.members(db, user)


@router.put("/areas/{area_id}/members", status_code=status.HTTP_204_NO_CONTENT)
async def set_member(
    area_id: int,
    payload: AreaMemberSet,
    user: User = Depends(require_area_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await svc.set_member(db, user, area_id, payload.user_id, payload.area_role)
    except svc.NotAllowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No administras esa área"
        ) from None


@router.delete(
    "/areas/{area_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    area_id: int,
    user_id: int,
    user: User = Depends(require_area_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await svc.remove_member(db, user, area_id, user_id)
    except svc.NotAllowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No administras esa área"
        ) from None
