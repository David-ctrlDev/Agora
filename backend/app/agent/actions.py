"""Ejecución de acciones del agente (con efecto externo). Solo tras confirmación."""
import unicodedata
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.google.factory import get_google_provider
from app.models.user import User


def _norm(text: str) -> str:
    """Minúsculas sin acentos, para comparaciones tolerantes (Renovación ≈ renovacion)."""
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).strip()


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
    wanted = _norm(params.get("area_name") or "")
    area = None
    if wanted:
        area = next(
            (a for (a, _) in areas if wanted in _norm(a.name) or _norm(a.slug) == wanted), None
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


_SELF_WORDS = {"mí", "mi", "yo", "yo mismo", "me", "self", "a mí", "a mi"}


async def _resolve_assignee(db: AsyncSession, user: User, who: str | None) -> int | None:
    """Resuelve un responsable por «mí», nombre o correo. None si no aplica."""
    if not who:
        return None
    from sqlalchemy import func, or_, select

    needle = who.strip().lower()
    first_name = user.name.split()[0].lower() if user.name else ""
    if (
        needle in _SELF_WORDS
        or needle == user.name.lower()
        or needle == user.email.lower()
        or needle == first_name
    ):
        return user.id
    found = (
        await db.execute(
            select(User)
            .where(or_(func.lower(User.name).contains(needle), func.lower(User.email).contains(needle)))
            .limit(1)
        )
    ).scalar_one_or_none()
    return found.id if found else None


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
    wanted = _norm(params.get("project_name") or "")
    project = None
    if wanted:
        project = next((p for p in rows if wanted in _norm(p.name)), None)
    if project is None and len(rows) == 1:
        project = rows[0]
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": "no tienes permiso de edición en ese proyecto."}
    assignee_id = await _resolve_assignee(db, user, params.get("assignee"))
    task = await tasks_svc.create_task(
        db,
        project.id,
        TaskCreate(title=params.get("title", "Nueva tarea"), assignee_id=assignee_id),
    )
    return {
        "ok": True,
        "task_id": task.id,
        "title": task.title,
        "project": project.name,
        "assignee": task.assignee_name,
    }


def _coerce_priority(value: Any) -> str:
    return value if value in ("low", "medium", "high") else "medium"


def _parse_task_due(value: Any):
    from datetime import date

    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


async def _create_tasks_in(db: AsyncSession, user: User, project, items: list) -> list[str]:
    """Crea una lista de tareas dentro de un proyecto ya resuelto. Devuelve los títulos creados."""
    from app.schemas.task import TaskCreate
    from app.services import tasks as tasks_svc

    created: list[str] = []
    for it in items or []:
        data = it if isinstance(it, dict) else {"title": str(it)}
        title = (data.get("title") or "").strip()
        if not title:
            continue
        assignee_id = await _resolve_assignee(db, user, data.get("assignee"))
        task = await tasks_svc.create_task(
            db,
            project.id,
            TaskCreate(
                title=title[:300],
                priority=_coerce_priority(data.get("priority")),
                assignee_id=assignee_id,
                due_date=_parse_task_due(data.get("due_date")),
            ),
        )
        created.append(task.title)
    return created


async def execute_create_project_with_tasks(
    db: AsyncSession, user: User, params: dict[str, Any]
) -> dict[str, Any]:
    """Crea un proyecto y, dentro de él, toda una lista de tareas en un solo paso."""
    from app.models.project import Project

    proj = await execute_create_project(
        db, user, {"name": params.get("name", "Nuevo proyecto"), "area_name": params.get("area_name")}
    )
    if not proj.get("ok"):
        return proj
    project = await db.get(Project, proj["project_id"])
    created = await _create_tasks_in(db, user, project, params.get("tasks") or [])
    return {
        "ok": True,
        "name": proj["name"],
        "area": proj["area"],
        "project_id": proj["project_id"],
        "tasks": created,
    }


async def execute_create_tasks(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Crea varias tareas (lote) en un proyecto existente, accesible y editable."""
    from sqlalchemy import func, select

    from app.models.project import Project
    from app.services import projects as projects_svc

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
    wanted = _norm(params.get("project_name") or "")
    project = None
    if wanted:
        project = next((p for p in rows if wanted in _norm(p.name)), None)
    if project is None and len(rows) == 1:
        project = rows[0]
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": "no tienes permiso de edición en ese proyecto."}
    created = await _create_tasks_in(db, user, project, params.get("tasks") or [])
    if not created:
        return {"ok": False, "error": "no me diste tareas válidas para crear."}
    return {"ok": True, "project": project.name, "tasks": created}


async def _find_task(db: AsyncSession, user: User, title: str):
    from sqlalchemy import func, select

    from app.models.project import Project
    from app.models.task import Task
    from app.services import projects as projects_svc

    project_ids = await projects_svc.accessible_project_ids(db, user)
    if not project_ids:
        return None
    rows = (
        await db.execute(
            select(Task, Project)
            .join(Project, Project.id == Task.project_id)
            .where(Task.project_id.in_(project_ids))
            .order_by(func.length(Task.title).desc())
        )
    ).all()
    wanted = _norm(title or "")
    if not wanted:
        return None
    return next(((t, p) for (t, p) in rows if wanted in _norm(t.title)), None)


async def execute_update_task(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    from app.schemas.task import TaskUpdate
    from app.services import projects as projects_svc
    from app.services import tasks as tasks_svc

    found = await _find_task(db, user, params.get("title", ""))
    if found is None:
        return {"ok": False, "error": f"no encontré la tarea «{params.get('title', '')}»."}
    task, project = found
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": "no tienes permiso de edición en ese proyecto."}
    updated = await tasks_svc.update_task(db, task, TaskUpdate(status=params.get("status", "done")))
    return {"ok": True, "title": updated.title, "status": updated.status, "project": project.name}


async def execute_assign_task(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    from sqlalchemy import func, or_, select

    from app.schemas.task import TaskUpdate
    from app.services import projects as projects_svc
    from app.services import tasks as tasks_svc

    found = await _find_task(db, user, params.get("title", ""))
    if found is None:
        return {"ok": False, "error": f"no encontré la tarea «{params.get('title', '')}»."}
    task, project = found
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": "no tienes permiso de edición en ese proyecto."}
    who = (params.get("assignee") or "").strip().lower()
    assignee = None
    if who:
        assignee = (
            await db.execute(
                select(User)
                .where(or_(func.lower(User.name).contains(who), func.lower(User.email).contains(who)))
                .limit(1)
            )
        ).scalar_one_or_none()
    if assignee is None:
        return {"ok": False, "error": f"no encontré al usuario «{params.get('assignee', '')}»."}
    await tasks_svc.update_task(db, task, TaskUpdate(assignee_id=assignee.id))
    return {"ok": True, "title": task.title, "assignee": assignee.name, "project": project.name}
