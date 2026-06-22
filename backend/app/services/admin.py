"""Servicios de administración (solo admin global)."""
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Area
from app.models.user import User
from app.models.user_area import UserArea
from app.schemas.admin import (
    AdminAreaMembership,
    AdminUserCreate,
    AdminUserRead,
    AdminUserUpdate,
    AreaAssignment,
)

_ROLES = {"admin", "member"}
_AREA_ROLES = {"lead", "member"}


class EmailExists(Exception):
    pass


async def _areas_by_user(db: AsyncSession) -> dict[int, list[AdminAreaMembership]]:
    rows = (
        await db.execute(
            select(UserArea.user_id, UserArea.area_id, UserArea.area_role, Area.name).join(
                Area, Area.id == UserArea.area_id
            )
        )
    ).all()
    out: dict[int, list[AdminAreaMembership]] = {}
    for uid, area_id, area_role, name in rows:
        out.setdefault(uid, []).append(
            AdminAreaMembership(area_id=area_id, name=name, area_role=area_role)
        )
    return out


def _to_read(user: User, areas: list[AdminAreaMembership]) -> AdminUserRead:
    return AdminUserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        twofa_enabled=user.totp_enabled,
        areas=areas,
    )


async def list_users(db: AsyncSession) -> list[AdminUserRead]:
    users = (await db.execute(select(User).order_by(User.role, User.name))).scalars().all()
    by_user = await _areas_by_user(db)
    return [_to_read(u, by_user.get(u.id, [])) for u in users]


async def _read_one(db: AsyncSession, user: User) -> AdminUserRead:
    by_user = await _areas_by_user(db)
    return _to_read(user, by_user.get(user.id, []))


async def create_user(db: AsyncSession, payload: AdminUserCreate) -> AdminUserRead:
    email = payload.email.strip().lower()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        raise EmailExists()
    role = payload.role if payload.role in _ROLES else "member"
    user = User(
        email=email,
        name=payload.name.strip(),
        role=role,
        is_active=True,
        default_area_id=payload.area_ids[0] if payload.area_ids else None,
    )
    db.add(user)
    await db.flush()
    for area_id in payload.area_ids:
        db.add(UserArea(user_id=user.id, area_id=area_id, area_role="member"))
    await db.commit()
    await db.refresh(user)
    return await _read_one(db, user)


async def update_user(db: AsyncSession, user: User, payload: AdminUserUpdate) -> AdminUserRead:
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.role in _ROLES:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    return await _read_one(db, user)


async def set_user_areas(
    db: AsyncSession, user: User, areas: list[AreaAssignment]
) -> AdminUserRead:
    await db.execute(delete(UserArea).where(UserArea.user_id == user.id))
    for a in areas:
        role = a.area_role if a.area_role in _AREA_ROLES else "member"
        db.add(UserArea(user_id=user.id, area_id=a.area_id, area_role=role))
    if areas and user.default_area_id is None:
        user.default_area_id = areas[0].area_id
    await db.commit()
    await db.refresh(user)
    return await _read_one(db, user)
