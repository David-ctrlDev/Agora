"""Levantamiento de requerimientos: propuesta de tareas con IA y aceptación.

El texto digitado vive en projects.requirements (se edita vía PATCH del
proyecto). Aquí: proponer tareas desde ese texto (y/o un adjunto PDF/Word)
y crear en lote las aceptadas por el usuario.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.project import Project
from app.models.user import User
from app.schemas.task import TaskCreate, TaskPriority, TaskRead
from app.services import audit
from app.services import projects as projects_svc
from app.services import task_ai
from app.services import tasks as tasks_svc

router = APIRouter(prefix="/api/projects/{project_id}/requirements", tags=["requirements"])


class TaskProposal(BaseModel):
    title: str
    description: str = ""
    priority: TaskPriority = "medium"


class AcceptProposals(BaseModel):
    tasks: list[TaskProposal] = Field(min_length=1, max_length=30)


async def _editable_project(project_id: int, user: User, db: AsyncSession) -> Project:
    project = await projects_svc.get_project(db, project_id)
    if project is None or not await projects_svc.can_access(db, user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    if not await projects_svc.can_edit(db, user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso de edición")
    return project


@router.post("/proposals", response_model=list[TaskProposal])
async def propose(
    project_id: int,
    file: UploadFile | None = File(default=None),
    extra_text: str = Form(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskProposal]:
    """Propone tareas desde projects.requirements + texto extra + adjunto (opcional)."""
    project = await _editable_project(project_id, user, db)
    parts = [project.requirements or "", extra_text or ""]
    if file is not None:
        from app.rag.extract import UnsupportedFile, extract_text

        data = await file.read()
        if len(data) > 15 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El adjunto supera 15 MB",
            )
        try:
            parts.append(extract_text(file.filename or "adjunto", file.content_type, data))
        except UnsupportedFile:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Formato de adjunto no soportado (usa PDF, Word o texto)",
            ) from None
    text = "\n\n".join(p for p in parts if p.strip())
    try:
        proposals = await task_ai.propose_tasks(user, project.name, text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El asistente de IA no está disponible en este momento; intenta más tarde",
        ) from None
    return [TaskProposal(**p) for p in proposals]


@router.post("/accept", response_model=list[TaskRead], status_code=status.HTTP_201_CREATED)
async def accept(
    project_id: int,
    payload: AcceptProposals,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskRead]:
    """Crea en lote las tareas aceptadas (sin responsable/fecha: los pone el humano)."""
    await _editable_project(project_id, user, db)
    created: list[TaskRead] = []
    for proposal in payload.tasks:
        created.append(
            await tasks_svc.create_task(
                db,
                project_id,
                TaskCreate(
                    title=proposal.title,
                    description=proposal.description or None,
                    priority=proposal.priority,
                ),
                actor=user,
            )
        )
    await audit.log(
        db,
        project_id=project_id,
        entity_type="task",
        action="created_from_requirements",
        summary=f"{len(created)} tarea(s) creadas desde el levantamiento (propuestas por IA)",
        actor_id=user.id,
    )
    return created
