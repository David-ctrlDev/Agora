from datetime import datetime

from pydantic import BaseModel


class AuditRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int | None
    action: str
    summary: str
    actor_name: str | None
    created_at: datetime


class GlobalAuditRead(BaseModel):
    """Fila de la bitácora global (panel del super admin): incluye el proyecto."""

    id: int
    entity_type: str
    action: str
    summary: str
    actor_name: str | None
    project_id: int
    project_name: str | None
    area_name: str | None
    created_at: datetime
