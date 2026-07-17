"""Tools de lectura del agente. SIEMPRE acotadas a las áreas del usuario."""
from datetime import date
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_user_area_ids
from app.models.area import Area
from app.models.github_event import GitHubEvent
from app.models.github_repo import GitHubRepo
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.sprint import Sprint
from app.models.task import Task
from app.models.user import User


async def _accessible_project_ids(db: AsyncSession, user: User) -> list[int]:
    area_ids = await get_user_area_ids(db, user)
    stmt = select(Project.id)
    if area_ids is not None:
        member_pids = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
        stmt = stmt.where(or_(Project.area_id.in_(area_ids), Project.id.in_(member_pids)))
    return [row[0] for row in (await db.execute(stmt)).all()]


async def _count(db: AsyncSession, *conditions: Any) -> int:
    value = (await db.execute(select(func.count(Task.id)).where(*conditions))).scalar()
    return int(value or 0)


async def projects_status(db: AsyncSession, user: User) -> list[dict[str, Any]]:
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return []
    rows = (
        await db.execute(
            select(Project, Area.name)
            .join(Area, Area.id == Project.area_id)
            .where(Project.id.in_(pids))
            .order_by(Project.name)
        )
    ).all()
    today = date.today()
    result = []
    for project, area_name in rows:
        result.append(
            {
                "name": project.name,
                "area": area_name,
                "status": project.status,
                "open_tasks": await _count(db, Task.project_id == project.id, Task.status != "done"),
                "overdue": await _count(
                    db,
                    Task.project_id == project.id,
                    Task.status != "done",
                    Task.due_date.is_not(None),
                    Task.due_date < today,
                ),
            }
        )
    return result


async def projects_overview(db: AsyncSession, user: User, limit: int = 250) -> list[dict[str, Any]]:
    """Panorama de proyectos accesibles: responsable/líder, estado, avance (%) y entrega."""
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return []
    rows = (
        await db.execute(
            select(Project, Area.name, User.name)
            .join(Area, Area.id == Project.area_id)
            .join(User, User.id == Project.owner_id, isouter=True)
            .where(Project.id.in_(pids))
            .order_by(Project.name)
            .limit(limit)
        )
    ).all()
    return [
        {
            "name": project.name,
            "area": area_name,
            "lead": owner_name,
            "status": project.status,
            "progress": project.progress,
            "due_date": project.due_date.isoformat() if project.due_date else None,
        }
        for (project, area_name, owner_name) in rows
    ]


async def overdue_tasks(db: AsyncSession, user: User) -> list[dict[str, Any]]:
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return []
    today = date.today()
    rows = (
        await db.execute(
            select(Task, Project.name)
            .join(Project, Project.id == Task.project_id)
            .where(
                Task.project_id.in_(pids),
                Task.is_adjustment.is_(False),
                Task.status != "done",
                Task.due_date.is_not(None),
                Task.due_date < today,
            )
            .order_by(Task.due_date)
        )
    ).all()
    return [
        {"title": t.title, "project": pn, "due_date": t.due_date.isoformat(), "status": t.status}
        for (t, pn) in rows
    ]


async def recent_activity(db: AsyncSession, user: User, limit: int = 10) -> list[dict[str, Any]]:
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return []
    repo_ids = select(GitHubRepo.id).where(GitHubRepo.project_id.in_(pids))
    rows = (
        await db.execute(
            select(GitHubEvent, GitHubRepo.full_name)
            .join(GitHubRepo, GitHubRepo.id == GitHubEvent.repo_id)
            .where(GitHubEvent.repo_id.in_(repo_ids))
            .order_by(GitHubEvent.occurred_at.desc())
            .limit(limit)
        )
    ).all()
    return [
        {"type": e.event_type, "title": e.title, "repo": fn, "when": e.occurred_at.date().isoformat()}
        for (e, fn) in rows
    ]


async def project_summary(db: AsyncSession, user: User, message: str) -> dict[str, Any] | None:
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return None
    rows = (
        await db.execute(
            select(Project, Area.name)
            .join(Area, Area.id == Project.area_id)
            .where(Project.id.in_(pids))
            .order_by(func.length(Project.name).desc())
        )
    ).all()
    lowered = message.lower()
    match = next(((p, an) for (p, an) in rows if p.name.lower() in lowered), None)
    if match is None:
        return None
    project, area_name = match
    today = date.today()
    recent = await recent_activity(db, user, limit=1)
    recent_for = next((r for r in recent), None)
    members = (
        await db.execute(
            select(func.count(ProjectMember.user_id)).where(ProjectMember.project_id == project.id)
        )
    ).scalar() or 0
    return {
        "name": project.name,
        "area": area_name,
        "status": project.status,
        "open_tasks": await _count(db, Task.project_id == project.id, Task.status != "done"),
        "overdue": await _count(
            db,
            Task.project_id == project.id,
            Task.status != "done",
            Task.due_date.is_not(None),
            Task.due_date < today,
        ),
        "done": await _count(db, Task.project_id == project.id, Task.status == "done"),
        "members": int(members),
        "recent": f"[{recent_for['type']}] {recent_for['title']}" if recent_for else None,
    }


async def knowledge_search(db: AsyncSession, user: User, query: str) -> list[dict[str, Any]]:
    from app.services import knowledge as knowledge_service

    project_ids = await _accessible_project_ids(db, user)
    return await knowledge_service.search(db, query, project_ids, k=4)


def _task_row(task: Task, project_name: str) -> dict[str, Any]:
    return {
        "title": task.title,
        "project": project_name,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else None,
    }


async def my_tasks(db: AsyncSession, user: User, limit: int = 25) -> list[dict[str, Any]]:
    """Tareas abiertas asignadas al usuario actual."""
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return []
    rows = (
        await db.execute(
            select(Task, Project.name)
            .join(Project, Project.id == Task.project_id)
            .where(Task.project_id.in_(pids), Task.assignee_id == user.id, Task.status != "done", Task.is_adjustment.is_(False))
            .order_by(Task.due_date.is_(None), Task.due_date)
            .limit(limit)
        )
    ).all()
    return [_task_row(t, pn) for (t, pn) in rows]


async def tasks_by_assignee(db: AsyncSession, user: User, person: str, limit: int = 25) -> dict[str, Any]:
    """Tareas asignadas a una persona (por nombre o correo), dentro de las áreas del usuario."""
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return {"found": False, "message": "No tienes proyectos accesibles."}
    who = (person or "").strip().lower()
    target = None
    if who:
        target = (
            await db.execute(
                select(User)
                .where(or_(func.lower(User.name).contains(who), func.lower(User.email).contains(who)))
                .limit(1)
            )
        ).scalar_one_or_none()
    if target is None:
        return {"found": False, "message": f"No encontré a «{person}» entre los usuarios."}
    rows = (
        await db.execute(
            select(Task, Project.name)
            .join(Project, Project.id == Task.project_id)
            .where(Task.project_id.in_(pids), Task.assignee_id == target.id, Task.is_adjustment.is_(False))
            .order_by(Task.status, Task.due_date.is_(None), Task.due_date)
            .limit(limit)
        )
    ).all()
    return {"found": True, "person": target.name, "tasks": [_task_row(t, pn) for (t, pn) in rows]}


async def project_details(db: AsyncSession, user: User, project_name: str) -> dict[str, Any] | None:
    """Ficha completa de un proyecto: estado, líder, avance, fechas, economía/ROI y sprints."""
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return None
    rows = (
        await db.execute(
            select(Project, Area.name, User.name)
            .join(Area, Area.id == Project.area_id)
            .join(User, User.id == Project.owner_id, isouter=True)
            .where(Project.id.in_(pids))
            .order_by(func.length(Project.name).desc())
        )
    ).all()
    who = (project_name or "").strip().lower()
    match = next(((p, an, on) for (p, an, on) in rows if who and who in p.name.lower()), None)
    if match is None:
        return None
    project, area_name, owner_name = match
    from app.services import economics as economics_service

    ec = economics_service.compute(project)
    today = date.today()
    sprints = (
        await db.execute(select(func.count(Sprint.id)).where(Sprint.project_id == project.id))
    ).scalar() or 0
    beneficiary_area = None
    if ec.beneficiary_area_id:
        beneficiary_area = (
            await db.execute(select(Area.name).where(Area.id == ec.beneficiary_area_id))
        ).scalar_one_or_none()
    return {
        "name": project.name,
        "area": area_name,
        "lead": owner_name,
        "status": project.status,
        "progress": project.progress,
        "category": project.category,
        "criticality": project.criticality,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "due_date": project.due_date.isoformat() if project.due_date else None,
        "due_in_days": (project.due_date - today).days if project.due_date else None,
        "open_tasks": await _count(db, Task.project_id == project.id, Task.status != "done"),
        "overdue": await _count(
            db,
            Task.project_id == project.id,
            Task.status != "done",
            Task.due_date.is_not(None),
            Task.due_date < today,
        ),
        "done_tasks": await _count(db, Task.project_id == project.id, Task.status == "done"),
        "sprints": int(sprints),
        "economics": {
            "currency": ec.currency,
            "has_data": ec.has_data,
            "has_impact": ec.has_impact,
            "estimated_cost": ec.estimated_cost,
            "actual_cost": ec.actual_cost,
            "expected_benefit": ec.expected_benefit,
            "actual_benefit": ec.actual_benefit,
            "roi_expected_pct": ec.roi_expected_pct,
            "roi_actual_pct": ec.roi_actual_pct,
            "executor": {
                "area": area_name,
                "process": ec.executor_process,
                "effort_hours_estimated": ec.effort_hours_estimated,
                "effort_hours_actual": ec.effort_hours_actual,
                "team": ec.executor_team,
                "complexity": ec.implementation_complexity,
                "resources": ec.resources_needed,
            },
            "beneficiary": {
                "area": beneficiary_area,
                "process": ec.beneficiary_process,
                "hours_saved_monthly": ec.hours_saved_monthly,
                "hours_saved_yearly": ec.hours_saved_yearly,
                "people_impacted": ec.people_impacted,
                "risk_reduction": ec.risk_reduction,
                "strategic_value": ec.strategic_value,
            },
        },
    }


async def areas_overview(db: AsyncSession, user: User) -> dict[str, Any]:
    """Panorama por área (proyectos, % de avance, en riesgo) y totales globales accesibles."""
    from app.services import analytics as analytics_service

    ov = await analytics_service.overview(db, user)
    return {
        "totals": ov.totals.model_dump(),
        "by_area": [
            {
                "area": a.area,
                "projects": a.projects,
                "completion_pct": a.completion_pct,
                "at_risk": a.at_risk,
            }
            for a in ov.by_area
        ],
    }


async def upcoming_deliveries(db: AsyncSession, user: User, limit: int = 10) -> list[dict[str, Any]]:
    """Próximas entregas: proyectos no terminados con fecha de entrega, de la más cercana en adelante."""
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return []
    today = date.today()
    rows = (
        await db.execute(
            select(Project.name, Project.due_date, Project.status, Project.progress)
            .where(
                Project.id.in_(pids),
                Project.due_date.is_not(None),
                Project.status != "done",
            )
            .order_by(Project.due_date)
            .limit(limit)
        )
    ).all()
    return [
        {
            "project": name,
            "due_date": due.isoformat(),
            "in_days": (due - today).days,
            "status": st,
            "progress": pr,
        }
        for (name, due, st, pr) in rows
    ]


async def query_data(
    db: AsyncSession,
    user: User,
    entity: str,
    *,
    status: str = "",
    assignee: str = "",
    owner: str = "",
    area: str = "",
    project: str = "",
    priority: str = "",
    criticality: str = "",
    search: str = "",
    created_after: str = "",
    created_before: str = "",
    due_after: str = "",
    due_before: str = "",
    group_by: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    """Consulta flexible y SEGURA sobre proyectos o tareas del usuario, SIEMPRE acotada
    a sus áreas accesibles. Soporta filtros, rango de fechas y agrupación (conteos).
    Cubre casi cualquier pregunta de datos sin necesidad de una tool por pregunta."""
    from datetime import date as _date

    pids = await _accessible_project_ids(db, user)
    if not pids:
        return {"entity": entity, "count": 0, "items": []}
    limit = max(1, min(int(limit or 50), 200))

    def pdate(s: str):
        try:
            return _date.fromisoformat((s or "").strip())
        except ValueError:
            return None

    async def area_id(name: str):
        n = (name or "").strip().lower()
        if not n:
            return None
        return (
            await db.execute(select(Area.id).where(func.lower(Area.name).contains(n)).limit(1))
        ).scalar_one_or_none() or -1

    async def user_id(name: str):
        n = (name or "").strip().lower()
        if n in ("sin asignar", "nadie", "unassigned", "sin responsable", "sin dueño"):
            return "NONE"
        if not n:
            return None
        return (
            await db.execute(
                select(User.id)
                .where(
                    or_(
                        func.lower(User.email) == n,
                        func.lower(User.name).contains(n),
                        func.lower(User.email).contains(n),
                    )
                )
                .limit(1)
            )
        ).scalar_one_or_none() or -1

    if entity == "tasks":
        conds = [Task.project_id.in_(pids), Task.is_adjustment.is_(False)]
        if status:
            conds.append(Task.status == status)
        if priority:
            conds.append(Task.priority == priority)
        if search:
            conds.append(func.lower(Task.title).contains(search.strip().lower()))
        if project:
            conds.append(func.lower(Project.name).contains(project.strip().lower()))
        if area:
            conds.append(Project.area_id == await area_id(area))
        if assignee:
            uid = await user_id(assignee)
            conds.append(Task.assignee_id.is_(None) if uid == "NONE" else Task.assignee_id == uid)
        if pdate(created_after):
            conds.append(func.date(Task.created_at) >= pdate(created_after))
        if pdate(created_before):
            conds.append(func.date(Task.created_at) <= pdate(created_before))
        if pdate(due_after):
            conds.append(Task.due_date >= pdate(due_after))
        if pdate(due_before):
            conds.append(Task.due_date <= pdate(due_before))

        if group_by:
            key = {
                "assignee": func.coalesce(User.name, "(sin asignar)"),
                "status": Task.status,
                "priority": Task.priority,
                "project": Project.name,
                "area": Area.name,
            }.get(group_by)
            if key is None:
                return {"error": f"group_by no soportado para tareas: {group_by}"}
            rows = (
                await db.execute(
                    select(key.label("key"), func.count(Task.id).label("n"))
                    .select_from(Task)
                    .join(Project, Project.id == Task.project_id)
                    .join(Area, Area.id == Project.area_id)
                    .outerjoin(User, User.id == Task.assignee_id)
                    .where(*conds)
                    .group_by(key)
                    .order_by(func.count(Task.id).desc())
                )
            ).all()
            return {"entity": "tasks", "group_by": group_by, "groups": [{"key": k, "count": n} for k, n in rows]}

        rows = (
            await db.execute(
                select(
                    Task.title, Project.name, User.name, Task.status, Task.priority,
                    Task.due_date, Task.created_at,
                )
                .select_from(Task)
                .join(Project, Project.id == Task.project_id)
                .join(Area, Area.id == Project.area_id)
                .outerjoin(User, User.id == Task.assignee_id)
                .where(*conds)
                .order_by(Task.created_at.desc())
                .limit(limit)
            )
        ).all()
        return {
            "entity": "tasks",
            "count": len(rows),
            "items": [
                {
                    "title": t, "project": p, "assignee": a or "(sin asignar)", "status": s,
                    "priority": pr, "due_date": dd.isoformat() if dd else None,
                    "created_at": c.isoformat() if c else None,
                }
                for (t, p, a, s, pr, dd, c) in rows
            ],
        }

    # entity == "projects"
    conds = [Project.id.in_(pids)]
    if status:
        conds.append(Project.status == status)
    if criticality:
        conds.append(func.lower(Project.criticality) == criticality.strip().lower())
    if search:
        conds.append(func.lower(Project.name).contains(search.strip().lower()))
    if area:
        conds.append(Project.area_id == await area_id(area))
    if owner:
        uid = await user_id(owner)
        conds.append(Project.owner_id.is_(None) if uid == "NONE" else Project.owner_id == uid)
    if pdate(created_after):
        conds.append(func.date(Project.created_at) >= pdate(created_after))
    if pdate(created_before):
        conds.append(func.date(Project.created_at) <= pdate(created_before))
    if pdate(due_after):
        conds.append(Project.due_date >= pdate(due_after))
    if pdate(due_before):
        conds.append(Project.due_date <= pdate(due_before))

    if group_by:
        key = {
            "status": Project.status,
            "area": Area.name,
            "owner": func.coalesce(User.name, "(sin dueño)"),
            "criticality": Project.criticality,
            "category": Project.category,
        }.get(group_by)
        if key is None:
            return {"error": f"group_by no soportado para proyectos: {group_by}"}
        rows = (
            await db.execute(
                select(key.label("key"), func.count(Project.id).label("n"))
                .select_from(Project)
                .join(Area, Area.id == Project.area_id)
                .outerjoin(User, User.id == Project.owner_id)
                .where(*conds)
                .group_by(key)
                .order_by(func.count(Project.id).desc())
            )
        ).all()
        return {"entity": "projects", "group_by": group_by, "groups": [{"key": k, "count": n} for k, n in rows]}

    rows = (
        await db.execute(
            select(
                Project.name, Area.name, User.name, Project.status, Project.criticality,
                Project.due_date, Project.created_at,
            )
            .select_from(Project)
            .join(Area, Area.id == Project.area_id)
            .outerjoin(User, User.id == Project.owner_id)
            .where(*conds)
            .order_by(Project.created_at.desc())
            .limit(limit)
        )
    ).all()
    return {
        "entity": "projects",
        "count": len(rows),
        "items": [
            {
                "name": n, "area": a, "owner": o, "status": s, "criticality": cr,
                "due_date": dd.isoformat() if dd else None,
                "created_at": c.isoformat() if c else None,
            }
            for (n, a, o, s, cr, dd, c) in rows
        ],
    }


async def recent_created(db: AsyncSession, user: User, limit: int = 20) -> dict[str, Any]:
    """Proyectos y tareas creados más recientemente (con su área/dueño y a quién se
    asignó cada tarea). Ordenados del más nuevo al más antiguo."""
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return {"projects": [], "tasks": []}
    proj_rows = (
        await db.execute(
            select(Project.name, Area.name, User.name, Project.created_at)
            .join(Area, Area.id == Project.area_id)
            .join(User, User.id == Project.owner_id, isouter=True)
            .where(Project.id.in_(pids))
            .order_by(Project.created_at.desc())
            .limit(limit)
        )
    ).all()
    task_rows = (
        await db.execute(
            select(Task.title, Project.name, User.name, Task.created_at)
            .join(Project, Project.id == Task.project_id)
            .join(User, User.id == Task.assignee_id, isouter=True)
            .where(Task.project_id.in_(pids), Task.is_adjustment.is_(False))
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
    ).all()
    return {
        "projects": [
            {"name": n, "area": a, "owner": o, "created_at": c.isoformat() if c else None}
            for (n, a, o, c) in proj_rows
        ],
        "tasks": [
            {"title": t, "project": p, "assignee": asg or "(sin asignar)", "created_at": c.isoformat() if c else None}
            for (t, p, asg, c) in task_rows
        ],
    }


async def list_tasks(db: AsyncSession, user: User, project_name: str) -> dict[str, Any]:
    """Tareas de un proyecto (título, estado, prioridad, responsable, fecha)."""
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return {"error": "no tienes proyectos accesibles.", "tasks": []}
    rows = (
        await db.execute(
            select(Project).where(Project.id.in_(pids)).order_by(func.length(Project.name).desc())
        )
    ).scalars().all()
    who = (project_name or "").strip().lower()
    project = next((p for p in rows if who and who in p.name.lower()), None)
    if project is None and not who and len(rows) == 1:
        project = rows[0]
    if project is None:
        return {"error": f"no identifiqué el proyecto «{project_name}».", "tasks": []}
    from app.services import tasks as tasks_svc

    items = await tasks_svc.list_project_tasks(db, project.id)
    return {
        "project": project.name,
        "count": len(items),
        "tasks": [
            {
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "assignee": t.assignee_name,
                "due_date": t.due_date.isoformat() if t.due_date else None,
            }
            for t in items
        ],
    }


async def google_status(db: AsyncSession, user: User) -> dict[str, Any]:
    """Estado de la conexión de Google del usuario (conectado y permisos/scopes)."""
    from app.services import google as google_service

    return await google_service.status(db, user)


async def search_drive(db: AsyncSession, user: User, query: str) -> dict[str, Any]:
    """Busca archivos/carpetas en el Drive del usuario (no importa nada, solo consulta)."""
    from app.services import google as google_service

    try:
        files = await google_service.browse_drive(db, user, None, (query or None), True)
    except google_service.GoogleNotConnected:
        return {"connected": False, "error": "no tienes Google conectado.", "files": []}
    except Exception:
        return {"error": "no pude buscar en Drive (revisa la conexión de Google).", "files": []}
    return {
        "count": len(files),
        "files": [
            {
                "title": f.get("title"),
                "type": "carpeta" if f.get("is_folder") else "archivo",
                "web_url": f.get("web_url"),
                "modified_at": f.get("modified_at"),
            }
            for f in files[:50]
        ],
    }


async def list_project_documents(db: AsyncSession, user: User, project_name: str) -> dict[str, Any]:
    """Documentos vinculados a un proyecto (subidos, importados de Drive o generados)."""
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return {"error": "no tienes proyectos accesibles.", "documents": []}
    rows = (
        await db.execute(
            select(Project).where(Project.id.in_(pids)).order_by(func.length(Project.name).desc())
        )
    ).scalars().all()
    who = (project_name or "").strip().lower()
    project = next((p for p in rows if who and who in p.name.lower()), None)
    if project is None and not who and len(rows) == 1:
        project = rows[0]
    if project is None:
        return {"error": f"no identifiqué el proyecto «{project_name}».", "documents": []}
    from app.services import knowledge as knowledge_service

    docs = await knowledge_service.list_documents(db, project.id)
    return {
        "project": project.name,
        "count": len(docs),
        "documents": [
            {
                "title": d.title,
                "source": d.source,
                "mime_type": d.mime_type,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ],
    }


async def list_areas(db: AsyncSession, user: User) -> dict[str, Any]:
    """Lista las áreas accesibles por el usuario con su nº de proyectos (admin: todas)."""
    area_ids = await get_user_area_ids(db, user)  # None = admin (sin restricción)
    stmt = select(Area).order_by(Area.name)
    if area_ids is not None:
        stmt = stmt.where(Area.id.in_(area_ids))
    areas = (await db.execute(stmt)).scalars().all()
    out = []
    for a in areas:
        n = (
            await db.execute(select(func.count(Project.id)).where(Project.area_id == a.id))
        ).scalar() or 0
        out.append({"name": a.name, "slug": a.slug, "projects": int(n), "active": a.is_active})
    return {"count": len(out), "areas": out}


async def list_users(db: AsyncSession, user: User) -> dict[str, Any]:
    """Lista los usuarios del sistema (solo administradores)."""
    if user.role != "admin":
        return {"error": "solo un administrador puede listar usuarios.", "users": []}
    rows = (await db.execute(select(User).order_by(User.name))).scalars().all()
    return {
        "count": len(rows),
        "users": [
            {"name": u.name, "email": u.email, "role": u.role, "active": u.is_active} for u in rows
        ],
    }


async def list_sprints(db: AsyncSession, user: User, project_name: str) -> dict[str, Any]:
    """Sprints de un proyecto (nombre, objetivo, fechas, estado)."""
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return {"error": "no tienes proyectos accesibles.", "sprints": []}
    rows = (
        await db.execute(
            select(Project).where(Project.id.in_(pids)).order_by(func.length(Project.name).desc())
        )
    ).scalars().all()
    who = (project_name or "").strip().lower()
    project = next((p for p in rows if who and who in p.name.lower()), None)
    if project is None and not who and len(rows) == 1:
        project = rows[0]
    if project is None:
        return {"error": f"no identifiqué el proyecto «{project_name}».", "sprints": []}
    from app.services import sprints as sprints_svc

    items = await sprints_svc.list_sprints(db, project.id)
    return {
        "project": project.name,
        "count": len(items),
        "sprints": [
            {
                "name": s.name,
                "goal": s.goal,
                "status": s.status,
                "start_date": s.start_date.isoformat() if s.start_date else None,
                "end_date": s.end_date.isoformat() if s.end_date else None,
            }
            for s in items
        ],
    }


async def list_project_members(db: AsyncSession, user: User, project_name: str) -> dict[str, Any]:
    """Miembros de un proyecto (nombre, correo y rol)."""
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return {"error": "no tienes proyectos accesibles.", "members": []}
    rows = (
        await db.execute(
            select(Project).where(Project.id.in_(pids)).order_by(func.length(Project.name).desc())
        )
    ).scalars().all()
    who = (project_name or "").strip().lower()
    project = next((p for p in rows if who and who in p.name.lower()), None)
    if project is None and not who and len(rows) == 1:
        project = rows[0]
    if project is None:
        return {"error": f"no identifiqué el proyecto «{project_name}».", "members": []}
    from app.services import projects as projects_svc

    members = await projects_svc.list_members(db, project.id)
    return {
        "project": project.name,
        "count": len(members),
        "members": [{"name": m.name, "email": m.email, "role": m.role} for m in members],
    }


async def find_meeting_slot(
    db: AsyncSession,
    user: User,
    project_name: str,
    duration_minutes: int = 60,
    days_ahead: int = 7,
) -> dict[str, Any]:
    """Primer hueco común de los miembros del proyecto (free/busy de Calendar), en
    horario laboral (8–17) de lunes a viernes y evitando el almuerzo (12–14).
    Devuelve el inicio sugerido y los correos de los asistentes para create_meeting."""
    pids = await _accessible_project_ids(db, user)
    if not pids:
        return {"found": False, "reason": "no tienes proyectos accesibles."}
    rows = (
        await db.execute(
            select(Project)
            .where(Project.id.in_(pids))
            .order_by(func.length(Project.name).desc())
        )
    ).scalars().all()
    who = (project_name or "").strip().lower()
    project = next((p for p in rows if who and who in p.name.lower()), None)
    if project is None and not who and len(rows) == 1:
        project = rows[0]
    if project is None:
        return {"found": False, "reason": f"no identifiqué el proyecto «{project_name}»."}

    from app.services import scheduling

    result = await scheduling.suggest_slot(db, user, project, duration_minutes, days_ahead)
    result["project"] = project.name
    return result


async def my_meetings(db: AsyncSession, user: User, days: int = 7) -> dict[str, Any]:
    """Próximas reuniones del calendario de Google del usuario (las suyas, no por proyecto)."""
    from app.services import google as google_service

    try:
        events = await google_service.list_my_meetings(db, user, days=days)
    except google_service.GoogleNotConnected:
        return {"connected": False, "events": []}
    except Exception:
        return {
            "connected": True,
            "error": "No se pudo leer el calendario; revisa los permisos de Google.",
            "events": [],
        }
    return {"connected": True, "days": days, "events": events}


async def my_notifications(db: AsyncSession, user: User, limit: int = 10) -> list[dict[str, Any]]:
    """Alertas/notificaciones sin leer del usuario (riesgos detectados, resúmenes)."""
    from app.services import notifications as notif_service

    rows = await notif_service.list_notifications(db, user, limit=50)
    unread = [n for n in rows if n.status == "unread"][:limit]
    return [
        {
            "title": n.title,
            "body": n.body,
            "severity": n.severity,
            "when": n.created_at.date().isoformat() if n.created_at else None,
        }
        for n in unread
    ]
