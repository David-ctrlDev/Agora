from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationRead
from app.services import notifications as svc

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Notification]:
    return await svc.list_notifications(db, user)


@router.get("/unread-count")
async def unread_count(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, int]:
    return {"count": await svc.unread_count(db, user)}


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Notification:
    notification = await svc.get_notification(db, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrada")
    await svc.mark_read(db, notification)
    return notification


@router.post("/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, bool]:
    await svc.mark_all_read(db, user)
    return {"ok": True}


@router.post("/run")
async def run_detection(
    request: Request,
    x_run_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Dispara la detección de riesgos. Acepta token (para n8n) o sesión de admin."""
    token = settings.notifications_run_token
    if not (token and x_run_token == token):
        user = await get_current_user(request, db)
        if user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere admin")
    return {"created": await svc.run_detection(db)}
