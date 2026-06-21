"""Ejecución de acciones del agente (con efecto externo). Solo tras confirmación."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.google.factory import get_google_provider
from app.models.user import User


def execute_create_meeting(params: dict[str, Any]) -> dict[str, Any]:
    provider = get_google_provider()
    when_raw = params.get("when")
    when = datetime.fromisoformat(when_raw) if when_raw else datetime.now(timezone.utc)
    event = provider.create_meeting(
        params.get("title", "Reunión"), params.get("attendees", []), when
    )
    return {
        "title": event.title,
        "attendees": params.get("attendees", []),
        "starts_at": event.starts_at.isoformat(),
        "meet_url": event.meet_url,
        "web_url": event.web_url,
    }


def execute_send_email(params: dict[str, Any]) -> dict[str, Any]:
    # Outbox de desarrollo: no se envía nada real; se registra para auditoría.
    return {
        "to": params.get("to", []),
        "subject": params.get("subject", ""),
        "body": params.get("body", ""),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


async def execute_create_project(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Crea un proyecto respetando la autorización por área del usuario."""
    from app.schemas.project import ProjectCreate
    from app.services import auth as auth_service
    from app.services import projects as projects_svc

    areas = await auth_service.accessible_areas(db, user)
    wanted = (params.get("area_name") or "").strip().lower()
    area = None
    if wanted:
        area = next(
            (a for (a, _) in areas if wanted in a.name.lower() or a.slug == wanted), None
        )
    if area is None and len(areas) == 1:
        area = areas[0][0]
    if area is None:
        opciones = ", ".join(a.name for a, _ in areas) or "(ninguna)"
        return {
            "ok": False,
            "error": f"no identifiqué el área «{params.get('area_name', '')}». Tus áreas: {opciones}.",
        }
    try:
        project = await projects_svc.create_project(
            db, user, ProjectCreate(name=params.get("name", "Nuevo proyecto"), area_id=area.id)
        )
    except projects_svc.AreaNotAllowed:
        return {"ok": False, "error": "no tienes permiso en esa área."}
    return {"ok": True, "project_id": project.id, "name": project.name, "area": area.name}


async def execute_create_task(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Crea una tarea en un proyecto accesible y editable por el usuario."""
    from sqlalchemy import func, select

    from app.models.project import Project
    from app.schemas.task import TaskCreate
    from app.services import projects as projects_svc
    from app.services import tasks as tasks_svc

    project_ids = await projects_svc.accessible_project_ids(db, user)
    if not project_ids:
        return {"ok": False, "error": "no tienes proyectos accesibles."}
    rows = (
        await db.execute(
            select(Project)
            .where(Project.id.in_(project_ids))
            .order_by(func.length(Project.name).desc())
        )
    ).scalars().all()
    wanted = (params.get("project_name") or "").strip().lower()
    project = None
    if wanted:
        project = next((p for p in rows if wanted in p.name.lower()), None)
    if project is None and len(rows) == 1:
        project = rows[0]
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": "no tienes permiso de edición en ese proyecto."}
    task = await tasks_svc.create_task(db, project.id, TaskCreate(title=params.get("title", "Nueva tarea")))
    return {"ok": True, "task_id": task.id, "title": task.title, "project": project.name}
