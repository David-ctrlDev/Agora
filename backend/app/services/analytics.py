"""Métricas de avance por proyecto y resumen global, filtradas por área."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Area
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.analytics import AreaStat, Overview, OverviewTotals, ProjectAnalytics
from app.services import projects as projects_svc

_STATUSES = ["todo", "in_progress", "blocked", "done"]
_PRIORITIES = ["high", "medium", "low"]


def _health(total: int, done: int, overdue: int, blocked: int) -> str:
    if total == 0:
        return "sin_tareas"
    if done == total:
        return "completado"
    if overdue > 0:
        return "en_riesgo"
    if blocked > 0:
        return "atencion"
    return "en_curso"


def _metrics(project: Project, tasks: list[Task], today: date) -> ProjectAnalytics:
    by_status = {s: 0 for s in _STATUSES}
    by_priority = {p: 0 for p in _PRIORITIES}
    overdue = 0
    for task in tasks:
        by_status[task.status] = by_status.get(task.status, 0) + 1
        by_priority[task.priority] = by_priority.get(task.priority, 0) + 1
        if task.due_date is not None and task.due_date < today and task.status != "done":
            overdue += 1
    total = len(tasks)
    done = by_status["done"]
    blocked = by_status["blocked"]
    return ProjectAnalytics(
        project_id=project.id,
        name=project.name,
        status=project.status,
        total=total,
        done=done,
        open=total - done,
        blocked=blocked,
        overdue=overdue,
        completion_pct=round(done / total * 100) if total else 0,
        by_status=by_status,
        by_priority=by_priority,
        health=_health(total, done, overdue, blocked),
        due_date=project.due_date,
        due_in_days=(project.due_date - today).days if project.due_date else None,
        category=project.category,
        criticality=project.criticality,
        project_type=project.project_type,
        initiative=project.initiative,
        process=project.process,
    )


async def project_metrics(db: AsyncSession, project: Project) -> ProjectAnalytics:
    tasks = list(
        (await db.execute(select(Task).where(Task.project_id == project.id))).scalars().all()
    )
    return _metrics(project, tasks, date.today())


async def overview(db: AsyncSession, user: User) -> Overview:
    project_ids = await projects_svc.accessible_project_ids(db, user)
    if not project_ids:
        return Overview(
            projects=[],
            totals=OverviewTotals(
                projects=0,
                active_projects=0,
                total_tasks=0,
                done_tasks=0,
                completion_pct=0,
                overdue_tasks=0,
                at_risk_projects=0,
            ),
        )
    projects = list(
        (await db.execute(select(Project).where(Project.id.in_(project_ids)))).scalars().all()
    )
    tasks = list(
        (await db.execute(select(Task).where(Task.project_id.in_(project_ids)))).scalars().all()
    )
    today = date.today()
    grouped: dict[int, list[Task]] = {p.id: [] for p in projects}
    for task in tasks:
        grouped.setdefault(task.project_id, []).append(task)
    items = [_metrics(p, grouped.get(p.id, []), today) for p in projects]
    # Proyectos en riesgo primero, luego por nombre.
    items.sort(key=lambda m: (m.health != "en_riesgo", m.name.lower()))

    total_tasks = sum(m.total for m in items)
    done_tasks = sum(m.done for m in items)
    totals = OverviewTotals(
        projects=len(items),
        active_projects=sum(1 for p in projects if p.status == "active"),
        total_tasks=total_tasks,
        done_tasks=done_tasks,
        completion_pct=round(done_tasks / total_tasks * 100) if total_tasks else 0,
        overdue_tasks=sum(m.overdue for m in items),
        at_risk_projects=sum(1 for m in items if m.health == "en_riesgo"),
    )

    # --- Agregados para el dashboard ---
    area_rows = (
        await db.execute(select(Area.id, Area.name).where(Area.id.in_([p.area_id for p in projects])))
    ).all()
    area_name = {aid: name for aid, name in area_rows}
    item_by_id = {m.project_id: m for m in items}

    area_agg: dict[int, dict[str, int]] = {}
    for p in projects:
        m = item_by_id[p.id]
        m.area_name = area_name.get(p.area_id)
        agg = area_agg.setdefault(p.area_id, {"projects": 0, "done": 0, "total": 0, "at_risk": 0})
        agg["projects"] += 1
        agg["done"] += m.done
        agg["total"] += m.total
        if m.health == "en_riesgo":
            agg["at_risk"] += 1
    by_area = sorted(
        (
            AreaStat(
                area=area_name.get(aid, "—"),
                projects=agg["projects"],
                completion_pct=round(agg["done"] / agg["total"] * 100) if agg["total"] else 0,
                at_risk=agg["at_risk"],
            )
            for aid, agg in area_agg.items()
        ),
        key=lambda a: -a.projects,
    )

    task_by_status = {s: 0 for s in _STATUSES}
    for m in items:
        for s, count in m.by_status.items():
            task_by_status[s] = task_by_status.get(s, 0) + count

    project_by_status: dict[str, int] = {}
    by_criticality: dict[str, int] = {}
    for p in projects:
        project_by_status[p.status] = project_by_status.get(p.status, 0) + 1
        crit = (p.criticality or "").strip().upper() or "Sin definir"
        by_criticality[crit] = by_criticality.get(crit, 0) + 1

    return Overview(
        projects=items,
        totals=totals,
        by_area=by_area,
        task_by_status=task_by_status,
        project_by_status=project_by_status,
        by_criticality=by_criticality,
    )
