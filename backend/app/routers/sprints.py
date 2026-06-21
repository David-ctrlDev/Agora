from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.sprint import Sprint
from app.models.user import User
from app.schemas.sprint import Burndown, SprintCreate, SprintRead, SprintUpdate
from app.services import audit
from app.services import projects as projects_svc
from app.services import sprints as svc

router = APIRouter(prefix="/api", tags=["sprints"])


async def _project_access(
    project_id: int, user: User, db: AsyncSession, *, edit: bool = False
) -> None:
    project = await projects_svc.get_project(db, project_id)
    if project is None or not await projects_svc.can_access(db, user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    if edit and not await projects_svc.can_edit(db, user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso de edición")


async def _sprint_access(
    sprint_id: int, user: User, db: AsyncSession, *, edit: bool = False
) -> Sprint:
    sprint = await svc.get_sprint(db, sprint_id)
    if sprint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sprint no encontrado")
    await _project_access(sprint.project_id, user, db, edit=edit)
    return sprint


@router.get("/projects/{project_id}/sprints", response_model=list[SprintRead])
async def list_sprints(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[SprintRead]:
    await _project_access(project_id, user, db)
    return await svc.list_sprints(db, project_id)


@router.post(
    "/projects/{project_id}/sprints", response_model=SprintRead, status_code=status.HTTP_201_CREATED
)
async def create_sprint(
    project_id: int,
    payload: SprintCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SprintRead:
    await _project_access(project_id, user, db, edit=True)
    sprint = await svc.create_sprint(db, project_id, payload)
    await audit.log(
        db,
        project_id=project_id,
        entity_type="sprint",
        entity_id=sprint.id,
        action="created",
        summary=f"Sprint creado: {sprint.name}",
        actor_id=user.id,
    )
    return sprint


@router.patch("/sprints/{sprint_id}", response_model=SprintRead)
async def update_sprint(
    sprint_id: int,
    payload: SprintUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SprintRead:
    sprint = await _sprint_access(sprint_id, user, db, edit=True)
    return await svc.update_sprint(db, sprint, payload)


@router.delete("/sprints/{sprint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sprint(
    sprint_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    sprint = await _sprint_access(sprint_id, user, db, edit=True)
    await svc.delete_sprint(db, sprint)


@router.get("/sprints/{sprint_id}/burndown", response_model=Burndown)
async def sprint_burndown(
    sprint_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Burndown:
    sprint = await _sprint_access(sprint_id, user, db)
    return await svc.burndown(db, sprint)
