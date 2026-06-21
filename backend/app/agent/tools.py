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
