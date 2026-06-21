from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.project import Project
from app.models.user import User
from app.schemas.economics import EconomicsUpdate, ProjectEconomics
from app.services import economics as svc
from app.services import projects as projects_svc

router = APIRouter(prefix="/api/projects", tags=["economics"])


async def _project(project_id: int, user: User, db: AsyncSession, *, edit: bool = False) -> Project:
    project = await projects_svc.get_project(db, project_id)
    if project is None or not await projects_svc.can_access(db, user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    if edit and not await projects_svc.can_edit(db, user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso de edición")
    return project


@router.get("/{project_id}/economics", response_model=ProjectEconomics)
async def get_economics(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ProjectEconomics:
    project = await _project(project_id, user, db)
    return svc.compute(project)


@router.patch("/{project_id}/economics", response_model=ProjectEconomics)
async def patch_economics(
    project_id: int,
    payload: EconomicsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectEconomics:
    project = await _project(project_id, user, db, edit=True)
    return await svc.update_economics(db, project, payload)
