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
            .where(Task.project_id.in_(pids), Task.assignee_id == user.id, Task.status != "done")
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
            .where(Task.project_id.in_(pids), Task.assignee_id == target.id)
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
