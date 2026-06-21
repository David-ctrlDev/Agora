"""Bitácora de auditoría de cambios por proyecto."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditRead


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
