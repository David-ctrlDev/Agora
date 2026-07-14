"""Bitácora de auditoría de cambios por proyecto."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Area
from app.models.audit_log import AuditLog
from app.models.project import Project
from app.models.user import User
from app.schemas.audit import AuditRead, GlobalAuditRead


async def log(
    db: AsyncSession,
    *,
    project_id: int,
    entity_type: str,
    action: str,
    summary: str,
    entity_id: int | None = None,
    actor_id: int | None = None,
) -> None:
    db.add(
        AuditLog(
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            summary=summary[:500],
            actor_id=actor_id,
        )
    )
    await db.commit()


async def list_for_project(db: AsyncSession, project_id: int, limit: int = 50) -> list[AuditRead]:
    rows = (
        await db.execute(
            select(AuditLog, User.name)
            .outerjoin(User, User.id == AuditLog.actor_id)
            .where(AuditLog.project_id == project_id)
            .order_by(AuditLog.id.desc())
            .limit(limit)
        )
    ).all()
    return [
        AuditRead(
            id=entry.id,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            action=entry.action,
            summary=entry.summary,
            actor_name=actor_name,
            created_at=entry.created_at,
        )
        for (entry, actor_name) in rows
    ]


async def list_global(
    db: AsyncSession, *, limit: int = 300, area_ids: list[int] | None = None
) -> list[GlobalAuditRead]:
    """Bitácora global con proyecto/área resueltos. `area_ids=None` = todo
    (super admin); una lista acota a esas áreas (panel del admin de área)."""
    stmt = (
        select(AuditLog, User.name, Project.name, Area.name, Project.area_id)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .outerjoin(Project, Project.id == AuditLog.project_id)
        .outerjoin(Area, Area.id == Project.area_id)
    )
    if area_ids is not None:
        if not area_ids:
            return []
        stmt = stmt.where(Project.area_id.in_(area_ids))
    rows = (await db.execute(stmt.order_by(AuditLog.id.desc()).limit(limit))).all()
    return [
        GlobalAuditRead(
            id=entry.id,
            entity_type=entry.entity_type,
            action=entry.action,
            summary=entry.summary,
            actor_name=actor_name,
            project_id=entry.project_id,
            project_name=project_name,
            area_name=area_name,
            created_at=entry.created_at,
        )
        for (entry, actor_name, project_name, area_name, _aid) in rows
    ]
