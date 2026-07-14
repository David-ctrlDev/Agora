from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import admin_area_ids, get_user_area_ids, is_superadmin
from app.models.area import Area
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectMemberRead, ProjectRead, ProjectUpdate


class AreaNotAllowed(Exception):
    """El usuario no pertenece al área del proyecto que intenta crear."""


def _to_read(project: Project, area_name: str | None, owner_name: str | None) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        name=project.name,
        description=project.description,
        area_id=project.area_id,
        status=project.status,
        owner_id=project.owner_id,
        start_date=project.start_date,
        due_date=project.due_date,
        progress=project.progress,
        created_at=project.created_at,
        updated_at=project.updated_at,
        area_name=area_name,
        owner_name=owner_name,
        initiative=project.initiative,
        proposed_by=project.proposed_by,
        project_type=project.project_type,
        category=project.category,
        criticality=project.criticality,
        process=project.process,
        benefits=project.benefits,
        change_management=project.change_management,
        is_development=project.is_development,
    )


async def accessible_project_ids(db: AsyncSession, user: User) -> list[int]:
    """IDs de proyectos accesibles por el usuario (área o membresía de proyecto)."""
    area_ids = await get_user_area_ids(db, user)
    stmt = select(Project.id)
    if area_ids is not None:
        member_pids = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
        stmt = stmt.where(or_(Project.area_id.in_(area_ids), Project.id.in_(member_pids)))
    return [row[0] for row in (await db.execute(stmt)).all()]


async def list_projects(db: AsyncSession, user: User) -> list[ProjectRead]:
    stmt = (
        select(Project, Area.name, User.name)
        .join(Area, Area.id == Project.area_id)
        .outerjoin(User, User.id == Project.owner_id)
    )
    area_ids = await get_user_area_ids(db, user)
    if area_ids is not None:
        member_pids = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
        stmt = stmt.where(or_(Project.area_id.in_(area_ids), Project.id.in_(member_pids)))
    stmt = stmt.order_by(Project.created_at.desc())
    rows = (await db.execute(stmt)).all()
    my_member_ids = set(
        (
            await db.execute(
                select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
            )
        ).scalars().all()
    )
    out: list[ProjectRead] = []
    for (p, area_name, owner_name) in rows:
        read = _to_read(p, area_name, owner_name)
        read.is_mine = p.owner_id == user.id or p.id in my_member_ids
        out.append(read)
    return out


async def get_project(db: AsyncSession, project_id: int) -> Project | None:
    return await db.get(Project, project_id)


async def can_access(db: AsyncSession, user: User, project: Project) -> bool:
    if is_superadmin(user):
        return True
    area_ids = await get_user_area_ids(db, user)
    if area_ids and project.area_id in area_ids:
        return True
    member = await db.get(ProjectMember, {"project_id": project.id, "user_id": user.id})
    return member is not None


async def can_edit(db: AsyncSession, user: User, project: Project) -> bool:
    if is_superadmin(user) or project.owner_id == user.id:
        return True
    # Un administrador del área del proyecto puede editar cualquier proyecto de su área.
    admin_ids = await admin_area_ids(db, user)
    if admin_ids is None or project.area_id in admin_ids:
        return True
    member = await db.get(ProjectMember, {"project_id": project.id, "user_id": user.id})
    return member is not None and member.role in ("owner", "editor")


async def can_manage(db: AsyncSession, user: User, project: Project) -> bool:
    """Administrar el proyecto (borrar, reasignar dueño): super admin, el dueño, o
    un administrador del área del proyecto."""
    if is_superadmin(user) or project.owner_id == user.id:
        return True
    admin_ids = await admin_area_ids(db, user)  # None solo si super admin (ya cubierto)
    return admin_ids is not None and project.area_id in admin_ids


async def to_read(db: AsyncSession, project: Project) -> ProjectRead:
    area = await db.get(Area, project.area_id)
    owner = await db.get(User, project.owner_id) if project.owner_id else None
    return _to_read(project, area.name if area else None, owner.name if owner else None)


async def create_project(db: AsyncSession, user: User, payload: ProjectCreate) -> ProjectRead:
    area_ids = await get_user_area_ids(db, user)
    if area_ids is not None and payload.area_id not in area_ids:
        raise AreaNotAllowed()
    project = Project(
        name=payload.name.strip(),
        description=payload.description or None,
        area_id=payload.area_id,
        status=payload.status,
        owner_id=user.id,
        start_date=payload.start_date,
        due_date=payload.due_date,
        progress=payload.progress,
        category=payload.category or None,
        process=payload.process or None,
        project_type=payload.project_type or None,
        is_development=payload.is_development,
    )
    db.add(project)
    await db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role="owner"))
    await db.commit()
    await db.refresh(project)
    # Se crea un repositorio por debajo (sin UI); el usuario solo verá versiones de documentos.
    from app.services import github as github_svc

    await github_svc.ensure_repo_for_project(db, project)
    # Si el creador tiene Drive conectado (y la feature activa), crea de una la carpeta
    # `Ágora / {Proyecto}` en su Drive y la comparte con los miembros. Best-effort.
    try:
        from app.services import drive_docs

        await drive_docs.ensure_project_folder(db, project)
    except Exception:
        pass
    # Proyecto de desarrollo: inicializa su repo Git interno (pestaña Código).
    if project.is_development:
        try:
            from app.services import coderepo

            await coderepo.ensure_repo(project.id)
        except Exception:
            pass
    from app.services import audit

    await audit.log(
        db,
        project_id=project.id,
        entity_type="project",
        entity_id=project.id,
        action="created",
        summary=f"Proyecto creado: {project.name}",
        actor_id=user.id,
    )
    return await to_read(db, project)


async def update_project(db: AsyncSession, project: Project, payload: ProjectUpdate) -> ProjectRead:
    data = payload.model_dump(exclude_unset=True)
    progress_changed = (
        "progress" in data and data["progress"] is not None and data["progress"] != project.progress
    )
    for key, value in data.items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    # Sella el nuevo avance para el histórico trimestral (solo cuando cambia).
    if progress_changed:
        from app.models.project_progress_snapshot import ProjectProgressSnapshot

        db.add(ProjectProgressSnapshot(project_id=project.id, progress=project.progress))
        await db.commit()
    return await to_read(db, project)


async def delete_project(db: AsyncSession, project: Project) -> None:
    project_id = project.id
    await db.delete(project)
    await db.commit()
    # Limpia el repo Git interno del proyecto (si existía). Best-effort.
    try:
        from app.services import coderepo

        coderepo.remove_repo(project_id)
    except Exception:
        pass


async def list_members(db: AsyncSession, project_id: int) -> list[ProjectMemberRead]:
    rows = (
        await db.execute(
            select(ProjectMember, User)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(User.name)
        )
    ).all()
    return [
        ProjectMemberRead(user_id=u.id, name=u.name, email=u.email, role=pm.role) for (pm, u) in rows
    ]


_ROLE_LABEL = {"owner": "propietario", "editor": "editor", "viewer": "lector"}


async def add_member(
    db: AsyncSession, project_id: int, user_id: int, role: str, actor: User | None = None
) -> None:
    member = await db.get(ProjectMember, {"project_id": project_id, "user_id": user_id})
    is_new = member is None
    if member is not None:
        member.role = role
    else:
        db.add(ProjectMember(project_id=project_id, user_id=user_id, role=role))
    await db.commit()
    if actor is None:
        return
    member_user = await db.get(User, user_id)
    project = await db.get(Project, project_id)
    if member_user is None or project is None:
        return
    # Bitácora: quién agregó/cambió a quién (visible en Auditoría del panel admin).
    from app.services import audit

    label = _ROLE_LABEL.get(role, role)
    await audit.log(
        db,
        project_id=project_id,
        entity_type="member",
        entity_id=user_id,
        action="added" if is_new else "role_changed",
        summary=(
            f"Miembro añadido: {member_user.name} ({label})"
            if is_new
            else f"Rol de miembro actualizado: {member_user.name} → {label}"
        ),
        actor_id=actor.id,
    )
    # Avisa al nuevo miembro (in-app + correo del actor). Solo en alta nueva.
    if is_new and user_id != actor.id:
        from app.services import notifications as notif

        await notif.notify_project_member_added(db, actor, member_user, project, role)


async def remove_member(
    db: AsyncSession, project_id: int, user_id: int, actor: User | None = None
) -> None:
    member = await db.get(ProjectMember, {"project_id": project_id, "user_id": user_id})
    if member is None:
        return
    member_user = await db.get(User, user_id)
    await db.delete(member)
    await db.commit()
    if actor is not None and member_user is not None:
        from app.services import audit

        await audit.log(
            db,
            project_id=project_id,
            entity_type="member",
            entity_id=user_id,
            action="removed",
            summary=f"Miembro retirado: {member_user.name}",
            actor_id=actor.id,
        )
