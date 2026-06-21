from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_user_area_ids
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate


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


async def create_task(db: AsyncSession, project_id: int, payload: TaskCreate) -> TaskRead:
    task = Task(
        project_id=project_id,
        title=payload.title.strip(),
        description=payload.description or None,
        status=payload.status,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        due_date=payload.due_date,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return await _single_read(db, task)


async def update_task(db: AsyncSession, task: Task, payload: TaskUpdate) -> TaskRead:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    return await _single_read(db, task)


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
