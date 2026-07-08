"""Onboarding self-service de áreas: catálogo, solicitudes de unión y de área nueva,
y aprobación por el líder del área (area_role='lead') o un admin global.
"""
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import is_superadmin
from app.models.area import Area
from app.models.area_request import AreaJoinRequest
from app.models.notification import Notification
from app.models.user import User
from app.models.user_area import UserArea
from app.schemas.area import AreaCreate
from app.schemas.area_request import AreaCatalogItem, AreaRequestRead


class AreaNotFound(Exception): ...
class AlreadyMember(Exception): ...
class RequestNotFound(Exception): ...
class AlreadyDecided(Exception): ...
class NotAllowed(Exception): ...


# ─────────────────────────── lectura ───────────────────────────
async def catalog(db: AsyncSession, user: User) -> list[AreaCatalogItem]:
    areas = (
        await db.execute(select(Area).where(Area.is_active.is_(True)).order_by(Area.name))
    ).scalars().all()
    rows = (
        await db.execute(
            select(UserArea.area_id, UserArea.area_role, User.id, User.name).join(
                User, User.id == UserArea.user_id
            )
        )
    ).all()
    members: dict[int, list[tuple[int, str, str]]] = defaultdict(list)
    for area_id, role, uid, name in rows:
        members[area_id].append((uid, role, name))
    pending = set(
        (
            await db.execute(
                select(AreaJoinRequest.area_id).where(
                    AreaJoinRequest.user_id == user.id,
                    AreaJoinRequest.kind == "join",
                    AreaJoinRequest.status == "pending",
                )
            )
        ).scalars().all()
    )
    out: list[AreaCatalogItem] = []
    for a in areas:
        ms = members.get(a.id, [])
        out.append(
            AreaCatalogItem(
                id=a.id, name=a.name, description=a.description,
                member_count=len(ms),
                leads=[n for (_, r, n) in ms if r == "lead"],
                is_member=any(uid == user.id for (uid, _, _) in ms),
                pending=a.id in pending,
            )
        )
    return out


async def _to_read(db: AsyncSession, req: AreaJoinRequest) -> AreaRequestRead:
    requester = await db.get(User, req.user_id)
    area_name = None
    if req.area_id:
        area = await db.get(Area, req.area_id)
        area_name = area.name if area else None
    return AreaRequestRead(
        id=req.id, kind=req.kind, status=req.status, area_id=req.area_id, area_name=area_name,
        proposed_name=req.proposed_name, proposed_description=req.proposed_description,
        requester_id=req.user_id,
        requester_name=requester.name if requester else None,
        requester_email=requester.email if requester else None,
        note=req.note, created_at=req.created_at, decided_at=req.decided_at,
    )


async def my_requests(db: AsyncSession, user: User) -> list[AreaRequestRead]:
    reqs = (
        await db.execute(
            select(AreaJoinRequest)
            .where(AreaJoinRequest.user_id == user.id)
            .order_by(AreaJoinRequest.created_at.desc())
        )
    ).scalars().all()
    return [await _to_read(db, r) for r in reqs]


async def _lead_area_ids(db: AsyncSession, user: User) -> list[int]:
    return list(
        (
            await db.execute(
                select(UserArea.area_id).where(
                    UserArea.user_id == user.id, UserArea.area_role == "lead"
                )
            )
        ).scalars().all()
    )


async def pending_for(db: AsyncSession, user: User) -> list[AreaRequestRead]:
    """Solicitudes que ESTE usuario puede aprobar."""
    stmt = select(AreaJoinRequest).where(AreaJoinRequest.status == "pending")
    if user.role != "admin":
        lead_ids = await _lead_area_ids(db, user)
        if not lead_ids:
            return []
        stmt = stmt.where(AreaJoinRequest.kind == "join", AreaJoinRequest.area_id.in_(lead_ids))
    reqs = (await db.execute(stmt.order_by(AreaJoinRequest.created_at))).scalars().all()
    return [await _to_read(db, r) for r in reqs]


# ─────────────────────────── solicitudes ───────────────────────────
async def request_join(db: AsyncSession, user: User, area_id: int) -> AreaRequestRead:
    area = await db.get(Area, area_id)
    if area is None or not area.is_active:
        raise AreaNotFound()
    if await db.get(UserArea, {"user_id": user.id, "area_id": area_id}):
        raise AlreadyMember()
    existing = (
        await db.execute(
            select(AreaJoinRequest).where(
                AreaJoinRequest.user_id == user.id,
                AreaJoinRequest.area_id == area_id,
                AreaJoinRequest.kind == "join",
                AreaJoinRequest.status == "pending",
            )
        )
    ).scalars().first()
    if existing is not None:
        return await _to_read(db, existing)
    req = AreaJoinRequest(user_id=user.id, kind="join", area_id=area_id, status="pending")
    db.add(req)
    await db.commit()
    await db.refresh(req)
    await _notify_join_approvers(db, req, area, user)
    return await _to_read(db, req)


async def request_new_area(
    db: AsyncSession, user: User, name: str, description: str | None
) -> AreaRequestRead:
    req = AreaJoinRequest(
        user_id=user.id, kind="new_area", status="pending",
        proposed_name=name.strip()[:120], proposed_description=(description or None),
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    await _notify_admins_new_area(db, req, user)
    return await _to_read(db, req)


# ─────────────────────────── decisiones ───────────────────────────
async def _can_approve(db: AsyncSession, approver: User, req: AreaJoinRequest) -> bool:
    if is_superadmin(approver):
        return True
    if req.kind == "join" and req.area_id is not None:
        ua = await db.get(UserArea, {"user_id": approver.id, "area_id": req.area_id})
        return ua is not None and ua.area_role == "lead"
    return False  # new_area solo lo aprueba un admin global


async def approve(db: AsyncSession, approver: User, request_id: int) -> AreaRequestRead:
    req = await db.get(AreaJoinRequest, request_id)
    if req is None:
        raise RequestNotFound()
    if req.status != "pending":
        raise AlreadyDecided()
    if not await _can_approve(db, approver, req):
        raise NotAllowed()

    if req.kind == "join":
        if not await db.get(UserArea, {"user_id": req.user_id, "area_id": req.area_id}):
            db.add(UserArea(user_id=req.user_id, area_id=req.area_id, area_role="member"))
    else:  # new_area: el admin crea el área y el solicitante queda como LEAD
        from app.services import areas as areas_service

        area = await areas_service.create_area(
            db, AreaCreate(name=req.proposed_name or "Área", description=req.proposed_description)
        )
        req.area_id = area.id
        db.add(UserArea(user_id=req.user_id, area_id=area.id, area_role="lead"))

    req.status = "approved"
    req.decided_by = approver.id
    req.decided_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(req)
    await _notify_requester(db, req, approved=True)
    return await _to_read(db, req)


async def reject(
    db: AsyncSession, approver: User, request_id: int, note: str | None = None
) -> AreaRequestRead:
    req = await db.get(AreaJoinRequest, request_id)
    if req is None:
        raise RequestNotFound()
    if req.status != "pending":
        raise AlreadyDecided()
    if not await _can_approve(db, approver, req):
        raise NotAllowed()
    req.status = "rejected"
    req.note = note
    req.decided_by = approver.id
    req.decided_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(req)
    await _notify_requester(db, req, approved=False)
    return await _to_read(db, req)


# ─────────────────────────── avisos in-app ───────────────────────────
async def _notify(db: AsyncSession, user_ids: list[int], area_id: int | None, ntype: str, title: str, body: str) -> None:
    for uid in set(user_ids):
        db.add(
            Notification(
                user_id=uid, area_id=area_id, project_id=None,
                type=ntype, title=title, body=body, severity="info",
            )
        )
    if user_ids:
        await db.commit()


async def _admin_ids(db: AsyncSession) -> list[int]:
    emails = list(settings.superadmin_email_set)
    if not emails:
        return []
    rows = await db.execute(select(User.id).where(func.lower(User.email).in_(emails)))
    return list(rows.scalars().all())


async def _notify_join_approvers(db: AsyncSession, req: AreaJoinRequest, area: Area, requester: User) -> None:
    leads = list(
        (
            await db.execute(
                select(UserArea.user_id).where(
                    UserArea.area_id == area.id, UserArea.area_role == "lead"
                )
            )
        ).scalars().all()
    )
    approvers = leads or await _admin_ids(db)  # si el área no tiene líder, deciden los admins
    await _notify(
        db, approvers, area.id, "area_join_request",
        f"Solicitud de acceso: {area.name}",
        f"{requester.name} solicita unirse al área «{area.name}». Revísalo en Solicitudes.",
    )


async def _notify_admins_new_area(db: AsyncSession, req: AreaJoinRequest, requester: User) -> None:
    await _notify(
        db, await _admin_ids(db), None, "new_area_request",
        f"Propuesta de área nueva: {req.proposed_name}",
        f"{requester.name} propone crear el área «{req.proposed_name}». Revísalo en Solicitudes.",
    )


async def _notify_requester(db: AsyncSession, req: AreaJoinRequest, approved: bool) -> None:
    label = req.proposed_name if req.kind == "new_area" else None
    if not label and req.area_id:
        area = await db.get(Area, req.area_id)
        label = area.name if area else "el área"
    if approved:
        title, body = (
            f"Acceso aprobado: {label}",
            f"Tu solicitud para «{label}» fue aprobada. Ya tienes acceso.",
        )
    else:
        title, body = (
            f"Solicitud rechazada: {label}",
            f"Tu solicitud para «{label}» fue rechazada." + (f" Nota: {req.note}" if req.note else ""),
        )
    await _notify(db, [req.user_id], req.area_id, "area_request_decided", title, body)
