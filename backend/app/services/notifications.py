from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.github_event import GitHubEvent
from app.models.github_repo import GitHubRepo
from app.models.notification import Notification
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.user_area import UserArea


async def _recipients(db: AsyncSession, project: Project) -> set[int]:
    """Destinatarios de las alertas de un proyecto: dueño + leads del área."""
    recipients: set[int] = set()
    if project.owner_id is not None:
        recipients.add(project.owner_id)
    rows = await db.execute(
        select(UserArea.user_id).where(
            UserArea.area_id == project.area_id, UserArea.area_role == "lead"
        )
    )
    for (user_id,) in rows.all():
        recipients.add(user_id)
    return recipients


async def _emit(
    db: AsyncSession,
    user_id: int,
    project: Project,
    ntype: str,
    title: str,
    body: str,
    severity: str = "warning",
) -> bool:
    """Crea la notificación si no hay ya una igual sin leer (evita duplicados)."""
    exists = await db.execute(
        select(Notification.id).where(
            Notification.user_id == user_id,
            Notification.type == ntype,
            Notification.project_id == project.id,
            Notification.status == "unread",
        )
    )
    if exists.first() is not None:
        return False
    db.add(
        Notification(
            user_id=user_id,
            area_id=project.area_id,
            project_id=project.id,
            type=ntype,
            title=title,
            body=body,
            severity=severity,
        )
    )
    return True


async def _create_notification(
    db: AsyncSession, user_id: int, project: Project, ntype: str, title: str, body: str,
    severity: str = "info",
) -> None:
    db.add(
        Notification(
            user_id=user_id, area_id=project.area_id, project_id=project.id,
            type=ntype, title=title, body=body, severity=severity,
        )
    )
    await db.commit()


async def notify_task_assigned(
    db: AsyncSession, actor: User | None, assignee: User | None, task_title: str, project: Project
) -> None:
    """Avisa al responsable de una tarea recién asignada: in-app + correo (del actor)."""
    if assignee is None or actor is None or assignee.id == actor.id:
        return
    await _create_notification(
        db, assignee.id, project, "task_assigned",
        f"Nueva tarea asignada: {task_title}",
        f"{actor.name} te asignó la tarea «{task_title}» en el proyecto «{project.name}».",
    )
    if assignee.email:
        from app.services import google as google_service

        await google_service.send_email(
            db, actor, [assignee.email],
            f"[Ágora] Te asignaron una tarea: {task_title}",
            f"Hola {assignee.name},\n\n{actor.name} te asignó la tarea «{task_title}» "
            f"en el proyecto «{project.name}».\n\nIngresa a Ágora para verla.\n",
        )


async def notify_project_member_added(
    db: AsyncSession, actor: User | None, member: User | None, project: Project, role: str = "editor"
) -> None:
    """Avisa a quien fue agregado a un proyecto: in-app + correo (del actor)."""
    if member is None or actor is None or member.id == actor.id:
        return
    await _create_notification(
        db, member.id, project, "project_member_added",
        f"Te agregaron al proyecto: {project.name}",
        f"{actor.name} te agregó al proyecto «{project.name}» como {role}.",
    )
    if member.email:
        from app.services import google as google_service

        await google_service.send_email(
            db, actor, [member.email],
            f"[Ágora] Te agregaron al proyecto: {project.name}",
            f"Hola {member.name},\n\n{actor.name} te agregó al proyecto «{project.name}» "
            f"como {role}.\n\nIngresa a Ágora para verlo.\n",
        )


async def _count(db: AsyncSession, *conditions) -> int:
    value = (await db.execute(select(func.count(Task.id)).where(*conditions))).scalar()
    return int(value or 0)


async def run_detection(db: AsyncSession) -> int:
    """Detecta riesgos y genera notificaciones segmentadas por área."""
    today = date.today()
    now = datetime.now(timezone.utc)
    created = 0
    projects = (await db.execute(select(Project))).scalars().all()
    for project in projects:
        recipients = await _recipients(db, project)
        if not recipients:
            continue

        overdue = await _count(
            db,
            Task.project_id == project.id,
            Task.status != "done",
            Task.due_date.is_not(None),
            Task.due_date < today,
        )
        blocked = await _count(db, Task.project_id == project.id, Task.status == "blocked")

        stale = False
        if project.status == "active" and project.due_date and 0 <= (project.due_date - today).days <= 7:
            last_event = (
                await db.execute(
                    select(func.max(GitHubEvent.occurred_at))
                    .join(GitHubRepo, GitHubRepo.id == GitHubEvent.repo_id)
                    .where(GitHubRepo.project_id == project.id)
                )
            ).scalar()
            if last_event is None or last_event < now - timedelta(days=14):
                stale = True

        for user_id in recipients:
            if overdue and await _emit(
                db,
                user_id,
                project,
                "overdue_tasks",
                f"{overdue} tarea(s) vencida(s) en {project.name}",
                f"El proyecto «{project.name}» tiene {overdue} tarea(s) vencida(s).",
            ):
                created += 1
            if blocked and await _emit(
                db,
                user_id,
                project,
                "blocked_tasks",
                f"{blocked} tarea(s) bloqueada(s) en {project.name}",
                f"El proyecto «{project.name}» tiene {blocked} tarea(s) bloqueada(s).",
            ):
                created += 1
            if stale and await _emit(
                db,
                user_id,
                project,
                "stale_project",
                f"Entrega cercana sin actividad: {project.name}",
                f"«{project.name}» vence pronto y no registra actividad de GitHub reciente.",
            ):
                created += 1

    await db.commit()
    return created


async def list_notifications(db: AsyncSession, user: User, limit: int = 50) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def unread_count(db: AsyncSession, user: User) -> int:
    value = (
        await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user.id, Notification.status == "unread"
            )
        )
    ).scalar()
    return int(value or 0)


async def get_notification(db: AsyncSession, notification_id: int) -> Notification | None:
    return await db.get(Notification, notification_id)


async def mark_read(db: AsyncSession, notification: Notification) -> None:
    notification.status = "read"
    await db.commit()


async def mark_all_read(db: AsyncSession, user: User) -> None:
    rows = (
        await db.execute(
            select(Notification).where(
                Notification.user_id == user.id, Notification.status == "unread"
            )
        )
    ).scalars().all()
    for notification in rows:
        notification.status = "read"
    await db.commit()
