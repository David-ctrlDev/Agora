"""Ejecución de acciones del agente (con efecto externo). Solo tras confirmación."""
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations.google.factory import get_google_provider
from app.models.user import User


def _norm(text: str) -> str:
    """Minúsculas sin acentos, para comparaciones tolerantes (Renovación ≈ renovacion)."""
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).strip()


async def _resolve_project_id(db: AsyncSession, user: User, project_name: str | None) -> int | None:
    """Liga la reunión a un proyecto accesible si el nombre coincide; si no, None."""
    if not (project_name or "").strip():
        return None
    from app.agent.tools import _accessible_project_ids
    from app.models.project import Project

    pids = await _accessible_project_ids(db, user)
    if not pids:
        return None
    rows = (
        await db.execute(
            select(Project.id, Project.name)
            .where(Project.id.in_(pids))
            .order_by(func.length(Project.name).desc())
        )
    ).all()
    who = project_name.strip().lower()
    match = next((pid for pid, name in rows if who in (name or "").lower()), None)
    return match


async def _resolve_project(db: AsyncSession, user: User, project_name: str | None):
    """Devuelve el Project accesible cuyo nombre coincide (el más específico), o None."""
    from app.agent.tools import _accessible_project_ids
    from app.models.project import Project

    if not (project_name or "").strip():
        return None
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return None
    rows = (
        await db.execute(
            select(Project).where(Project.id.in_(pids)).order_by(func.length(Project.name).desc())
        )
    ).scalars().all()
    who = project_name.strip().lower()
    return next((p for p in rows if who in (p.name or "").lower()), None)


async def execute_create_meeting(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    title = params.get("title", "Reunión")
    attendees = params.get("attendees", [])
    when_raw = params.get("when")
    duration = int(params.get("duration_minutes") or 60)

    if settings.google_provider == "real":
        # Crea la reunión REAL en el calendario del usuario (con su token OAuth).
        from app.services import google as google_service

        project_id = await _resolve_project_id(db, user, params.get("project_name"))
        result = await google_service.create_meeting(
            db, user, project_id, title, attendees, when_raw, duration
        )
        starts_at, ends_at = result.get("starts_at"), result.get("ends_at")
        return {
            "title": result["title"],
            "attendees": attendees,
            "starts_at": starts_at.isoformat() if hasattr(starts_at, "isoformat") else starts_at,
            "ends_at": ends_at.isoformat() if hasattr(ends_at, "isoformat") else ends_at,
            "duration_minutes": duration,
            "meet_url": result.get("meet_url"),
            "web_url": result.get("web_url"),
        }

    # Modo mock (sin red): provider determinista.
    provider = get_google_provider()
    when = datetime.fromisoformat(when_raw) if when_raw else datetime.now(timezone.utc)
    event = provider.create_meeting(title, attendees, when)
    return {
        "title": event.title,
        "attendees": attendees,
        "starts_at": event.starts_at.isoformat(),
        "ends_at": (event.starts_at + timedelta(minutes=duration)).isoformat(),
        "duration_minutes": duration,
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
    if project is None and not wanted and len(rows) == 1:
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


async def _create_tasks_in(
    db: AsyncSession, user: User, project, items: list
) -> tuple[list[str], list[str]]:
    """Crea las tareas dentro de un proyecto. Devuelve (títulos creados, responsables sin resolver).

    Un responsable "sin resolver" es un nombre que el documento indicó pero que no
    corresponde a ningún usuario de Ágora (la tarea queda sin asignar, no se cae al
    usuario actual).
    """
    from app.schemas.task import TaskCreate
    from app.services import tasks as tasks_svc

    created: list[str] = []
    unmatched: list[str] = []
    for it in items or []:
        data = it if isinstance(it, dict) else {"title": str(it)}
        title = (data.get("title") or "").strip()
        if not title:
            continue
        who = (data.get("assignee") or "").strip()
        assignee_id = await _resolve_assignee(db, user, who)
        if who and assignee_id is None and who.lower() not in _SELF_WORDS:
            unmatched.append(who)
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
    # Únicos preservando orden.
    seen: set[str] = set()
    unmatched = [w for w in unmatched if not (w.lower() in seen or seen.add(w.lower()))]
    return created, unmatched


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
    created, unmatched = await _create_tasks_in(db, user, project, params.get("tasks") or [])
    return {
        "ok": True,
        "name": proj["name"],
        "area": proj["area"],
        "project_id": proj["project_id"],
        "tasks": created,
        "unmatched": unmatched,
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
    if project is None and not wanted and len(rows) == 1:
        project = rows[0]
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": "no tienes permiso de edición en ese proyecto."}
    created, unmatched = await _create_tasks_in(db, user, project, params.get("tasks") or [])
    if not created:
        return {"ok": False, "error": "no me diste tareas válidas para crear."}
    return {"ok": True, "project": project.name, "tasks": created, "unmatched": unmatched}


async def execute_save_diagram(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Guarda un diagrama (código Mermaid) en la documentación de un proyecto."""
    from sqlalchemy import func, select

    from app.models.project import Project
    from app.services import knowledge as knowledge_service
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
    project = next((p for p in rows if wanted and wanted in _norm(p.name)), None)
    if project is None and not wanted and len(rows) == 1:
        project = rows[0]
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": "no tienes permiso de edición en ese proyecto."}
    code = (params.get("mermaid") or "").strip()
    if not code:
        return {"ok": False, "error": "no recibí el diagrama a guardar."}
    title = (params.get("title") or "Diagrama").strip()[:300]
    document = await knowledge_service.ingest_document(
        db, project.id, title, code, source="diagram", mime_type="text/vnd.mermaid"
    )
    try:
        from app.services import drive_docs

        await drive_docs.push_document(db, project, document)
    except Exception:
        pass
    return {"ok": True, "project": project.name, "title": title}


async def execute_create_sprint(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Crea un sprint en un proyecto accesible y editable (fechas con valores por defecto)."""
    from datetime import date, timedelta

    from sqlalchemy import func, select

    from app.models.project import Project
    from app.schemas.sprint import SprintCreate
    from app.services import projects as projects_svc
    from app.services import sprints as sprints_svc

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
    project = next((p for p in rows if wanted and wanted in _norm(p.name)), None)
    if project is None and not wanted and len(rows) == 1:
        project = rows[0]
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": "no tienes permiso de edición en ese proyecto."}
    start = _parse_task_due(params.get("start_date")) or date.today()
    end = _parse_task_due(params.get("end_date")) or (start + timedelta(days=14))
    if end < start:
        end = start + timedelta(days=14)
    sprint = await sprints_svc.create_sprint(
        db,
        project.id,
        SprintCreate(
            name=(params.get("name") or "Sprint").strip()[:200],
            goal=params.get("goal") or None,
            start_date=start,
            end_date=end,
        ),
    )
    return {
        "ok": True,
        "project": project.name,
        "name": sprint.name,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }


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
    """Edita campos de una tarea: estado, prioridad, fecha, título o descripción."""
    from app.schemas.task import TaskUpdate
    from app.services import projects as projects_svc
    from app.services import tasks as tasks_svc

    found = await _find_task(db, user, params.get("title", ""))
    if found is None:
        return {"ok": False, "error": f"no encontré la tarea «{params.get('title', '')}»."}
    task, project = found
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": "no tienes permiso de edición en ese proyecto."}
    fields: dict[str, Any] = {}
    if params.get("status"):
        fields["status"] = params["status"]
    if params.get("priority"):
        fields["priority"] = _coerce_priority(params["priority"])
    if params.get("due_date"):
        due = _parse_task_due(params["due_date"])
        if due:
            fields["due_date"] = due
    if (params.get("new_title") or "").strip():
        fields["title"] = params["new_title"].strip()[:300]
    if params.get("description"):
        fields["description"] = params["description"]
    if not fields:
        fields["status"] = "done"  # compat: «marca la tarea como hecha»
    updated = await tasks_svc.update_task(db, task, TaskUpdate(**fields))
    return {
        "ok": True,
        "title": updated.title,
        "status": updated.status,
        "priority": getattr(updated, "priority", None),
        "project": project.name,
        "changed": list(fields.keys()),
    }


async def execute_delete_task(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Elimina una tarea. Requiere permiso de edición en su proyecto."""
    from app.services import projects as projects_svc
    from app.services import tasks as tasks_svc

    found = await _find_task(db, user, params.get("title", ""))
    if found is None:
        return {"ok": False, "error": f"no encontré la tarea «{params.get('title', '')}»."}
    task, project = found
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": "no tienes permiso de edición en ese proyecto."}
    title = task.title
    await tasks_svc.delete_task(db, task)
    return {"ok": True, "title": title, "project": project.name}


async def execute_comment_task(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Añade un comentario a una tarea. Basta con acceso al proyecto."""
    from app.services import comments as comments_svc
    from app.services import projects as projects_svc

    found = await _find_task(db, user, params.get("title", ""))
    if found is None:
        return {"ok": False, "error": f"no encontré la tarea «{params.get('title', '')}»."}
    task, project = found
    if not await projects_svc.can_access(db, user, project):
        return {"ok": False, "error": "no tienes acceso a esa tarea."}
    body = (params.get("body") or "").strip()
    if not body:
        return {"ok": False, "error": "no recibí el texto del comentario."}
    await comments_svc.add_comment(db, task.id, user.id, body)
    return {"ok": True, "title": task.title, "project": project.name}


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


async def execute_archive_project(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Archiva un proyecto (status=archived). Reversible. Requiere permiso de edición."""
    from app.services import projects as projects_svc

    project = await _resolve_project(db, user, params.get("project_name"))
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": f"no tienes permiso para archivar «{project.name}»."}
    if project.status == "archived":
        return {"ok": True, "name": project.name, "already": True}
    project.status = "archived"
    await db.commit()
    return {"ok": True, "name": project.name}


async def execute_delete_project(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Elimina un proyecto PERMANENTEMENTE. Irreversible. Solo propietario o admin."""
    from app.services import projects as projects_svc

    project = await _resolve_project(db, user, params.get("project_name"))
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not (user.role == "admin" or project.owner_id == user.id):
        return {"ok": False, "error": f"solo el propietario o un admin puede eliminar «{project.name}»."}
    name = project.name
    await projects_svc.delete_project(db, project)
    return {"ok": True, "name": name}


async def _resolve_user(db: AsyncSession, who: str | None):
    """Encuentra un usuario por correo exacto o por coincidencia de nombre/correo."""
    who = (who or "").strip().lower()
    if not who:
        return None
    return (
        await db.execute(
            select(User)
            .where(
                or_(
                    func.lower(User.email) == who,
                    func.lower(User.name).contains(who),
                    func.lower(User.email).contains(who),
                )
            )
            .limit(1)
        )
    ).scalar_one_or_none()


async def execute_update_project(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Edita campos de un proyecto: estado, nombre, descripción, fechas, avance,
    criticidad, categoría o dueño. Requiere permiso de edición."""
    from app.schemas.project import ProjectUpdate
    from app.services import projects as projects_svc

    project = await _resolve_project(db, user, params.get("project_name"))
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": f"no tienes permiso de edición en «{project.name}»."}
    fields: dict[str, Any] = {}
    if params.get("status"):
        fields["status"] = params["status"]
    if (params.get("new_name") or "").strip():
        fields["name"] = params["new_name"].strip()[:200]
    if params.get("description"):
        fields["description"] = params["description"]
    if params.get("due_date"):
        d = _parse_task_due(params["due_date"])
        if d:
            fields["due_date"] = d
    if params.get("start_date"):
        d = _parse_task_due(params["start_date"])
        if d:
            fields["start_date"] = d
    if str(params.get("progress") or "").strip():
        try:
            fields["progress"] = max(0, min(int(params["progress"]), 100))
        except (TypeError, ValueError):
            pass
    if params.get("criticality"):
        fields["criticality"] = params["criticality"]
    if params.get("category"):
        fields["category"] = params["category"]
    if (params.get("owner") or "").strip():
        owner = await _resolve_user(db, params["owner"])
        if owner is None:
            return {"ok": False, "error": f"no encontré al usuario «{params.get('owner', '')}» para dueño."}
        fields["owner_id"] = owner.id
    if not fields:
        return {"ok": False, "error": "no indicaste qué cambiar del proyecto."}
    read = await projects_svc.update_project(db, project, ProjectUpdate(**fields))
    return {"ok": True, "name": read.name, "status": read.status, "changed": list(fields.keys())}


async def execute_add_project_member(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Añade (o cambia el rol de) un miembro a un proyecto. Requiere edición."""
    from app.services import projects as projects_svc

    project = await _resolve_project(db, user, params.get("project_name"))
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": f"no tienes permiso de edición en «{project.name}»."}
    target = await _resolve_user(db, params.get("person"))
    if target is None:
        return {"ok": False, "error": f"no encontré al usuario «{params.get('person', '')}»."}
    role = (params.get("role") or "editor").strip().lower()
    if role not in ("owner", "editor", "viewer"):
        role = "editor"
    await projects_svc.add_member(db, project.id, target.id, role)
    return {"ok": True, "project": project.name, "person": target.name, "role": role}


async def execute_remove_project_member(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Quita un miembro de un proyecto. Requiere edición."""
    from app.services import projects as projects_svc

    project = await _resolve_project(db, user, params.get("project_name"))
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": f"no tienes permiso de edición en «{project.name}»."}
    target = await _resolve_user(db, params.get("person"))
    if target is None:
        return {"ok": False, "error": f"no encontré al usuario «{params.get('person', '')}»."}
    await projects_svc.remove_member(db, project.id, target.id)
    return {"ok": True, "project": project.name, "person": target.name}


async def _find_sprint(db: AsyncSession, project_id: int, sprint_name: str | None):
    """Encuentra el Sprint (ORM) de un proyecto por su nombre."""
    from app.services import sprints as sprints_svc

    items = await sprints_svc.list_sprints(db, project_id)
    who = (sprint_name or "").strip().lower()
    sr = next((s for s in items if who and who in s.name.lower()), None)
    if sr is None and len(items) == 1:
        sr = items[0]
    if sr is None:
        return None
    return await sprints_svc.get_sprint(db, sr.id)


async def execute_update_sprint(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Edita un sprint (nombre, objetivo, fechas o estado). Requiere edición."""
    from app.schemas.sprint import SprintUpdate
    from app.services import projects as projects_svc
    from app.services import sprints as sprints_svc

    project = await _resolve_project(db, user, params.get("project_name"))
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": f"no tienes permiso de edición en «{project.name}»."}
    sprint = await _find_sprint(db, project.id, params.get("sprint_name"))
    if sprint is None:
        return {"ok": False, "error": f"no encontré el sprint «{params.get('sprint_name', '')}» en {project.name}."}
    fields: dict[str, Any] = {}
    if (params.get("new_name") or "").strip():
        fields["name"] = params["new_name"].strip()[:200]
    if params.get("goal"):
        fields["goal"] = params["goal"]
    if params.get("start_date"):
        d = _parse_task_due(params["start_date"])
        if d:
            fields["start_date"] = d
    if params.get("end_date"):
        d = _parse_task_due(params["end_date"])
        if d:
            fields["end_date"] = d
    if params.get("status") in ("planned", "active", "completed"):
        fields["status"] = params["status"]
    if not fields:
        return {"ok": False, "error": "no indicaste qué cambiar del sprint."}
    read = await sprints_svc.update_sprint(db, sprint, SprintUpdate(**fields))
    return {"ok": True, "project": project.name, "name": read.name, "changed": list(fields.keys())}


async def execute_delete_sprint(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Elimina un sprint. Requiere edición."""
    from app.services import projects as projects_svc
    from app.services import sprints as sprints_svc

    project = await _resolve_project(db, user, params.get("project_name"))
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": f"no tienes permiso de edición en «{project.name}»."}
    sprint = await _find_sprint(db, project.id, params.get("sprint_name"))
    if sprint is None:
        return {"ok": False, "error": f"no encontré el sprint «{params.get('sprint_name', '')}» en {project.name}."}
    name = sprint.name
    await sprints_svc.delete_sprint(db, sprint)
    return {"ok": True, "project": project.name, "name": name}


# ---------------------------------------------------------------------------
# Administración (áreas y usuarios) — solo para administradores globales.
# ---------------------------------------------------------------------------
def _is_admin(user: User) -> bool:
    return user.role == "admin"


async def _resolve_area(db: AsyncSession, area_name: str | None):
    from app.models.area import Area

    who = (area_name or "").strip().lower()
    if not who:
        return None
    rows = (
        await db.execute(select(Area).order_by(func.length(Area.name).desc()))
    ).scalars().all()
    return next((a for a in rows if who in (a.name or "").lower()), None)


async def execute_create_area(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    if not _is_admin(user):
        return {"ok": False, "error": "solo un administrador puede crear áreas."}
    from app.schemas.area import AreaCreate
    from app.services import areas as areas_svc

    name = (params.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "falta el nombre del área."}
    try:
        area = await areas_svc.create_area(
            db, AreaCreate(name=name, description=params.get("description") or None)
        )
    except areas_svc.AreaSlugExists:
        return {"ok": False, "error": f"ya existe un área parecida a «{name}»."}
    return {"ok": True, "name": area.name}


async def execute_update_area(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    if not _is_admin(user):
        return {"ok": False, "error": "solo un administrador puede editar áreas."}
    area = await _resolve_area(db, params.get("area_name"))
    if area is None:
        return {"ok": False, "error": f"no encontré el área «{params.get('area_name', '')}»."}
    changed = []
    if (params.get("new_name") or "").strip():
        area.name = params["new_name"].strip()[:120]
        changed.append("nombre")
    if params.get("description"):
        area.description = params["description"]
        changed.append("descripción")
    if not changed:
        return {"ok": False, "error": "no indicaste qué cambiar del área."}
    await db.commit()
    return {"ok": True, "name": area.name}


async def execute_create_user(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    if not _is_admin(user):
        return {"ok": False, "error": "solo un administrador puede crear usuarios."}
    from app.schemas.admin import AdminUserCreate
    from app.services import admin as admin_svc

    email = (params.get("email") or "").strip()
    name = (params.get("name") or "").strip()
    if not email or not name:
        return {"ok": False, "error": "necesito al menos el correo y el nombre."}
    role = params.get("role") if params.get("role") in ("admin", "member") else "member"
    try:
        read = await admin_svc.create_user(db, AdminUserCreate(email=email, name=name, role=role))
    except admin_svc.EmailExists:
        return {"ok": False, "error": f"ya existe un usuario con el correo {email}."}
    return {"ok": True, "name": read.name, "email": read.email, "role": read.role}


async def execute_update_user_admin(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    if not _is_admin(user):
        return {"ok": False, "error": "solo un administrador puede editar usuarios."}
    from app.schemas.admin import AdminUserUpdate
    from app.services import admin as admin_svc

    target = await _resolve_user(db, params.get("person"))
    if target is None:
        return {"ok": False, "error": f"no encontré al usuario «{params.get('person', '')}»."}
    payload: dict[str, Any] = {}
    if (params.get("new_name") or "").strip():
        payload["name"] = params["new_name"].strip()
    if (params.get("new_email") or "").strip():
        payload["email"] = params["new_email"].strip()
    if params.get("role") in ("admin", "member"):
        payload["role"] = params["role"]
    if params.get("is_active") is not None and str(params.get("is_active")) != "":
        payload["is_active"] = bool(params["is_active"])
    if not payload:
        return {"ok": False, "error": "no indicaste qué cambiar del usuario."}
    try:
        read = await admin_svc.update_user(db, target, AdminUserUpdate(**payload))
    except admin_svc.EmailExists:
        return {"ok": False, "error": "ese correo ya está en uso por otro usuario."}
    return {"ok": True, "name": read.name, "email": read.email}


async def execute_set_user_areas(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    if not _is_admin(user):
        return {"ok": False, "error": "solo un administrador puede asignar áreas."}
    from app.schemas.admin import AreaAssignment
    from app.services import admin as admin_svc

    target = await _resolve_user(db, params.get("person"))
    if target is None:
        return {"ok": False, "error": f"no encontré al usuario «{params.get('person', '')}»."}
    names = params.get("area_names") or []
    if isinstance(names, str):
        names = [names]
    assignments, resolved = [], []
    for n in names:
        area = await _resolve_area(db, n)
        if area is not None:
            assignments.append(AreaAssignment(area_id=area.id, area_role="member"))
            resolved.append(area.name)
    if not assignments:
        return {"ok": False, "error": "no identifiqué áreas válidas para asignar."}
    await admin_svc.set_user_areas(db, target, assignments)
    return {"ok": True, "person": target.name, "areas": resolved}


# ---------------------------------------------------------------------------
# Google / Drive — importar y sincronizar documentos en un proyecto.
# ---------------------------------------------------------------------------
async def prepare_import_drive(db: AsyncSession, user: User, project_name: str, query: str) -> dict[str, Any]:
    """Resuelve EN EL SERVIDOR los archivos de Drive que coinciden con la búsqueda,
    para proponer su importación (el agente no maneja IDs de archivo)."""
    from app.services import google as google_service
    from app.services import projects as projects_svc

    project = await _resolve_project(db, user, project_name)
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{project_name}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": f"no tienes permiso de edición en «{project.name}»."}
    try:
        files = await google_service.browse_drive(db, user, None, (query or None), True)
    except google_service.GoogleNotConnected:
        return {"ok": False, "error": "no tienes Google conectado para leer Drive."}
    except Exception:
        return {"ok": False, "error": "no pude buscar en Drive (revisa la conexión de Google)."}
    files = [f for f in files if f.get("external_id")]
    if not files:
        return {"ok": False, "error": f"no encontré en tu Drive archivos que coincidan con «{query}»."}
    items = [
        {
            "external_id": f["external_id"],
            "title": f.get("title"),
            "mime_type": f.get("mime_type"),
            "web_url": f.get("web_url"),
            "modified_at": f.get("modified_at"),
        }
        for f in files
    ]
    return {
        "ok": True,
        "params": {"project_name": project.name, "project_id": project.id, "items": items},
        "titles": [f.get("title") or "(sin nombre)" for f in files],
    }


async def execute_import_drive(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Importa a un proyecto los archivos de Drive ya resueltos y los indexa (RAG)."""
    from app.services import google as google_service
    from app.services import projects as projects_svc

    project = await projects_svc.get_project(db, params.get("project_id"))
    if project is None:
        return {"ok": False, "error": "el proyecto ya no existe."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": "no tienes permiso de edición en ese proyecto."}
    items = params.get("items") or []
    if not items:
        return {"ok": False, "error": "no hay archivos para importar."}
    res = await google_service.import_drive_documents(db, user, project.id, items)
    return {
        "ok": True,
        "project": project.name,
        "new": res.get("new_documents", 0),
        "indexed": res.get("indexed", 0),
    }


async def execute_sync_project_drive(db: AsyncSession, user: User, params: dict[str, Any]) -> dict[str, Any]:
    """Re-sincroniza los documentos de Google/Drive vinculados al proyecto."""
    from app.services import google as google_service
    from app.services import projects as projects_svc

    project = await _resolve_project(db, user, params.get("project_name"))
    if project is None:
        return {"ok": False, "error": f"no identifiqué el proyecto «{params.get('project_name', '')}»."}
    if not await projects_svc.can_edit(db, user, project):
        return {"ok": False, "error": f"no tienes permiso de edición en «{project.name}»."}
    try:
        new = await google_service.sync_project(db, user, project.id, project.name)
    except google_service.GoogleNotConnected:
        return {"ok": False, "error": "no tienes Google conectado."}
    except Exception:
        return {"ok": False, "error": "no pude sincronizar con Google (revisa la conexión)."}
    return {"ok": True, "project": project.name, "new": new}
