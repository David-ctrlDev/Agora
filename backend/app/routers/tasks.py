from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.project import Project
from app.models.user import User
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services import audit
from app.services import projects as projects_svc
from app.services import tasks as svc

router = APIRouter(prefix="/api", tags=["tasks"])


async def _project_with_access(
    project_id: int, user: User, db: AsyncSession, *, edit: bool = False
) -> Project:
    project = await projects_svc.get_project(db, project_id)
    if project is None or not await projects_svc.can_access(db, user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    if edit and not await projects_svc.can_edit(db, user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso de edición")
    return project


@router.get("/tasks/mine", response_model=list[TaskRead])
async def my_tasks(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[TaskRead]:
    return await svc.list_my_tasks(db, user)


@router.get("/projects/{project_id}/tasks", response_model=list[TaskRead])
async def list_tasks(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[TaskRead]:
    await _project_with_access(project_id, user, db)
    return await svc.list_project_tasks(db, project_id)


@router.post(
    "/projects/{project_id}/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED
)
async def create_task(
    project_id: int,
    payload: TaskCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    await _project_with_access(project_id, user, db, edit=True)
    task = await svc.create_task(db, project_id, payload)
    await audit.log(
        db,
        project_id=project_id,
        entity_type="task",
        entity_id=task.id,
        action="created",
        summary=f"Tarea creada: {task.title}",
        actor_id=user.id,
    )
    return task


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    task = await svc.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    await _project_with_access(task.project_id, user, db, edit=True)
    old_status, old_assignee, old_sprint = task.status, task.assignee_id, task.sprint_id
    updated = await svc.update_task(db, task, payload)
    changes = []
    if updated.status != old_status:
        changes.append(f"estado {old_status}→{updated.status}")
    if updated.assignee_id != old_assignee:
        changes.append("responsable actualizado")
    if updated.sprint_id != old_sprint:
        changes.append("sprint actualizado")
    if changes:
        await audit.log(
            db,
            project_id=task.project_id,
            entity_type="task",
            entity_id=task.id,
            action="updated",
            summary=f"Tarea «{updated.title}»: {', '.join(changes)}",
            actor_id=user.id,
        )
    return updated


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    task = await svc.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    await _project_with_access(task.project_id, user, db, edit=True)
    await svc.delete_task(db, task)
