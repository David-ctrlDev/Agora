from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.audit import AuditRead
from app.services import audit as svc
from app.services import projects as projects_svc

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/projects/{project_id}/audit", response_model=list[AuditRead])
async def project_audit(
    project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[AuditRead]:
    project = await projects_svc.get_project(db, project_id)
    if project is None or not await projects_svc.can_access(db, user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    return await svc.list_for_project(db, project_id)
