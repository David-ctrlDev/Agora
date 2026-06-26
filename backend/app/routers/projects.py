from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.project import Project
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
)
from app.services import audit
from app.services import projects as svc

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def _accessible_project(project_id: int, user: User, db: AsyncSession) -> Project:
    project = await svc.get_project(db, project_id)
    # 404 también cuando no hay acceso, para no filtrar existencia.
    if project is None or not await svc.can_access(db, user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    return project


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ProjectRead]:
    return await svc.list_projects(db, user)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    try:
        return await svc.create_project(db, user, payload)
    except svc.AreaNotAllowed as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No perteneces a esa área"
        ) from exc


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ProjectRead:
    project = await _accessible_project(project_id, user, db)
    return await svc.to_read(db, project)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    project = await _accessible_project(project_id, user, db)
    if not await svc.can_edit(db, user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso de edición")
    old_status = project.status
    read = await svc.update_project(db, project, payload)
    if read.status != old_status:
        await audit.log(
            db,
            project_id=project.id,
            entity_type="project",
            entity_id=project.id,
            action="status_changed",
            summary=f"Estado del proyecto: {old_status}→{read.status}",
            actor_id=user.id,
        )
    return read


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    project = await _accessible_project(project_id, user, db)
    if not (user.role == "admin" or project.owner_id == user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Solo el propietario o un admin"
        )
    await svc.delete_project(db, project)


@router.get("/{project_id}/members", response_model=list[ProjectMemberRead])
async def list_members(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ProjectMemberRead]:
    await _accessible_project(project_id, user, db)
    return await svc.list_members(db, project_id)


@router.post(
    "/{project_id}/members",
    response_model=list[ProjectMemberRead],
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    project_id: int,
    payload: ProjectMemberCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectMemberRead]:
    project = await _accessible_project(project_id, user, db)
    if not await svc.can_edit(db, user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso")
    await svc.add_member(db, project_id, payload.user_id, payload.role, actor=user)
    return await svc.list_members(db, project_id)


@router.delete("/{project_id}/members/{member_user_id}", response_model=list[ProjectMemberRead])
async def remove_member(
    project_id: int,
    member_user_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectMemberRead]:
    project = await _accessible_project(project_id, user, db)
    if not await svc.can_edit(db, user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso")
    await svc.remove_member(db, project_id, member_user_id)
    return await svc.list_members(db, project_id)
