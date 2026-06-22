from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.project import Project
from app.models.user import User
from app.schemas.google import (
    DriveImport,
    FreeBusyQuery,
    GoogleDocumentRead,
    GoogleStatus,
    MeetingCreate,
    MeetingResult,
)
from app.services import audit
from app.services import google as svc
from app.services import projects as projects_svc

router = APIRouter(prefix="/api", tags=["google"])


async def _project(project_id: int, user: User, db: AsyncSession, *, edit: bool = False) -> Project:
    project = await projects_svc.get_project(db, project_id)
    if project is None or not await projects_svc.can_access(db, user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    if edit and not await projects_svc.can_edit(db, user, project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permiso de edición")
    return project


@router.get("/google/status", response_model=GoogleStatus)
async def google_status(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> GoogleStatus:
    return GoogleStatus(**await svc.status(db, user))


@router.post("/google/connect", response_model=GoogleStatus)
async def google_connect(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> GoogleStatus:
    if not settings.is_development:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await svc.connect_dev(db, user)
    return GoogleStatus(**await svc.status(db, user))


@router.post("/google/disconnect", response_model=GoogleStatus)
async def google_disconnect(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> GoogleStatus:
    await svc.disconnect(db, user)
    return GoogleStatus(**await svc.status(db, user))


@router.post("/projects/{project_id}/google/sync")
async def sync_project(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, int]:
    project = await _project(project_id, user, db, edit=True)
    try:
        return {"new_documents": await svc.sync_project(db, user, project.id, project.name)}
    except svc.GoogleNotConnected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Conecta tu cuenta de Google primero"
        ) from None


@router.post("/projects/{project_id}/google/meetings", response_model=MeetingResult)
async def create_meeting(
    project_id: int,
    payload: MeetingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeetingResult:
    project = await _project(project_id, user, db, edit=True)
    try:
        result = await svc.create_meeting(
            db, user, project.id, payload.title, payload.attendees, payload.when
        )
    except svc.GoogleNotConnected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Conecta tu cuenta de Google primero"
        ) from None
    await audit.log(
        db,
        project_id=project.id,
        entity_type="meeting",
        action="created",
        summary=f"Reunión creada: {result['title']}",
        actor_id=user.id,
    )
    return MeetingResult(**result)


@router.post("/projects/{project_id}/google/import")
async def import_drive(
    project_id: int,
    payload: DriveImport,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    project = await _project(project_id, user, db, edit=True)
    return await svc.import_drive_documents(
        db, user, project.id, [f.model_dump() for f in payload.files]
    )


@router.get("/projects/{project_id}/google/documents", response_model=list[GoogleDocumentRead])
async def list_documents(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list:
    await _project(project_id, user, db)
    return await svc.list_documents(db, project_id)


@router.get("/google/directory")
async def google_directory(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    return await svc.list_directory(db, user)


@router.post("/google/freebusy")
async def google_freebusy(
    payload: FreeBusyQuery,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[dict]]:
    try:
        return await svc.free_busy(db, user, payload.emails, payload.time_min, payload.time_max)
    except svc.GoogleNotConnected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Conecta tu cuenta de Google primero"
        ) from None
    except Exception:
        # p. ej. el token aún no tiene el permiso de calendarios (reconectar Google).
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo leer la disponibilidad; reconecta Google para el permiso de calendarios",
        ) from None


@router.get("/google/drive")
async def browse_drive(
    folder_id: str | None = None,
    q: str | None = None,
    shared: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    try:
        return await svc.browse_drive(db, user, folder_id, q, shared)
    except svc.GoogleNotConnected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Conecta tu cuenta de Google primero"
        ) from None
