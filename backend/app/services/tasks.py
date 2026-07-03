from datetime import date, datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.deps import get_user_area_ids
from app.models.area import Area
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskGroupStat,
    TaskRead,
    TaskSummary,
    TaskSummaryItem,
    TaskUpdate,
)


def _to_read(
    task: Task, assignee_name: str | None = None, project_name: str | None = None
) -> TaskRead:
    return TaskRead(
        id=task.id,
        project_id=task.project_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        assignee_id=task.assignee_id,
        due_date=task.due_date,
        sprint_id=task.sprint_id,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        assignee_name=assignee_name,
        project_name=project_name,
    )


async def list_project_tasks(db: AsyncSession, project_id: int) -> list[TaskRead]:
    rows = (
        await db.execute(
            select(Task, User.name)
            .outerjoin(User, User.id == Task.assignee_id)
            .where(Task.project_id == project_id)
            .order_by(Task.created_at)
        )
    ).all()
    return [_to_read(task, assignee_name) for (task, assignee_name) in rows]


async def get_task(db: AsyncSession, task_id: int) -> Task | None:
    return await db.get(Task, task_id)


async def _single_read(db: AsyncSession, task: Task) -> TaskRead:
    assignee = await db.get(User, task.assignee_id) if task.assignee_id else None
    return _to_read(task, assignee.name if assignee else None)


async def create_task(
    db: AsyncSession, project_id: int, payload: TaskCreate, actor: User | None = None
) -> TaskRead:
    task = Task(
        project_id=project_id,
        title=payload.title.strip(),
        description=payload.description or None,
        status=payload.status,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        due_date=payload.due_date,
        sprint_id=payload.sprint_id,
        completed_at=datetime.now(timezone.utc) if payload.status == "done" else None,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    await _notify_assignment(db, task, actor, previous_assignee=None)
    return await _single_read(db, task)


async def update_task(
    db: AsyncSession, task: Task, payload: TaskUpdate, actor: User | None = None
) -> TaskRead:
    previous_assignee = task.assignee_id
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(task, key, value)
    if task.status == "done" and task.completed_at is None:
        task.completed_at = datetime.now(timezone.utc)
    elif task.status != "done":
        task.completed_at = None
    await db.commit()
    await db.refresh(task)
    if "assignee_id" in data:
        await _notify_assignment(db, task, actor, previous_assignee=previous_assignee)
    return await _single_read(db, task)


async def _notify_assignment(
    db: AsyncSession, task: Task, actor: User | None, previous_assignee: int | None
) -> None:
    """Avisa al nuevo responsable (in-app + correo del actor). Best-effort."""
    if actor is None or not task.assignee_id:
        return
    if task.assignee_id == previous_assignee or task.assignee_id == actor.id:
        return
    from app.services import notifications as notif

    assignee = await db.get(User, task.assignee_id)
    project = await db.get(Project, task.project_id)
    if assignee is not None and project is not None:
        await notif.notify_task_assigned(db, actor, assignee, task.title, project)


async def delete_task(db: AsyncSession, task: Task) -> None:
    await db.delete(task)
    await db.commit()


async def list_my_tasks(db: AsyncSession, user: User) -> list[TaskRead]:
    stmt = (
        select(Task, User.name, Project.name)
        .join(Project, Project.id == Task.project_id)
        .outerjoin(User, User.id == Task.assignee_id)
        .where(Task.assignee_id == user.id)
    )
    area_ids = await get_user_area_ids(db, user)
    if area_ids is not None:
        member_pids = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
        stmt = stmt.where(or_(Project.area_id.in_(area_ids), Project.id.in_(member_pids)))
    stmt = stmt.where(Task.status != "done").order_by(Task.due_date.is_(None), Task.due_date)
    rows = (await db.execute(stmt)).all()
    return [_to_read(task, assignee_name, project_name) for (task, assignee_name, project_name) in rows]


async def task_summary(db: AsyncSession, project_ids: list[int] | None) -> TaskSummary:
    """Resumen de tareas: a quién, en qué proyecto y área, con agregados por
    responsable, área y estado. `project_ids=None` -> todas (uso admin);
    una lista -> acota a esos proyectos (p. ej. los que lidera un dueño)."""
    empty = TaskSummary(
        total=0, open=0, done=0, overdue=0, unassigned=0,
        by_assignee=[], by_area=[], by_status={}, items=[],
    )
    if project_ids is not None and not project_ids:
        return empty

    assignee = aliased(User)
    stmt = (
        select(
            Task.id, Task.title, Task.status, Task.priority, Task.due_date,
            Task.assignee_id, assignee.name, Task.project_id, Project.name, Area.name,
        )
        .join(Project, Project.id == Task.project_id)
        .join(Area, Area.id == Project.area_id)
        .outerjoin(assignee, assignee.id == Task.assignee_id)
    )
    if project_ids is not None:
        stmt = stmt.where(Task.project_id.in_(project_ids))
    rows = (await db.execute(stmt)).all()

    today = date.today()
    items: list[TaskSummaryItem] = []
    for tid, title, st, prio, due, aid, aname, pid, pname, arname in rows:
        overdue = due is not None and due < today and st != "done"
        items.append(
            TaskSummaryItem(
                id=tid, title=title, status=st, priority=prio, due_date=due,
                assignee_id=aid, assignee_name=aname, project_id=pid,
                project_name=pname, area_name=arname, overdue=overdue,
            )
        )
    # Vencidas primero, luego por fecha (sin fecha al final), luego por título.
    items.sort(key=lambda t: (not t.overdue, t.due_date is None, t.due_date or date.max, t.title.lower()))

    done = sum(1 for t in items if t.status == "done")
    by_status: dict[str, int] = {}
    for t in items:
        by_status[t.status] = by_status.get(t.status, 0) + 1

    def group(key_of) -> list[TaskGroupStat]:
        agg: dict[str, dict[str, int]] = {}
        for t in items:
            k = key_of(t)
            d = agg.setdefault(k, {"count": 0, "open": 0, "overdue": 0})
            d["count"] += 1
            if t.status != "done":
                d["open"] += 1
            if t.overdue:
                d["overdue"] += 1
        return sorted(
            (TaskGroupStat(key=k, **v) for k, v in agg.items()),
            key=lambda s: (-s.count, s.key),
        )

    return TaskSummary(
        total=len(items),
        open=len(items) - done,
        done=done,
        overdue=sum(1 for t in items if t.overdue),
        unassigned=sum(1 for t in items if t.assignee_id is None),
        by_assignee=group(lambda t: t.assignee_name or "Sin asignar"),
        by_area=group(lambda t: t.area_name),
        by_status=by_status,
        items=items,
    )
