from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.task import Task
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentRead
from app.services import comments as svc
from app.services import projects as projects_svc
from app.services import tasks as tasks_svc

router = APIRouter(prefix="/api/tasks", tags=["comments"])


async def _task_with_access(task_id: int, user: User, db: AsyncSession) -> Task:
    task = await tasks_svc.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    project = await projects_svc.get_project(db, task.project_id)
    if project is None or not await projects_svc.can_access(db, user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    return task


@router.get("/{task_id}/comments", response_model=list[CommentRead])
async def list_comments(
    task_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[CommentRead]:
    await _task_with_access(task_id, user, db)
    return await svc.list_comments(db, task_id)


@router.post(
    "/{task_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED
)
async def add_comment(
    task_id: int,
    payload: CommentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentRead:
    await _task_with_access(task_id, user, db)
    return await svc.add_comment(db, task_id, user.id, payload.body)
