import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.security import create_session_token
from app.integrations.google import oauth as google_oauth
from app.models.user import User
from app.schemas.auth import AreaMembership, CurrentUser, DevLoginRequest, DevUser
from app.services import auth as auth_service
from app.services import google as google_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_token(user_id),
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


async def _current_user_payload(db: AsyncSession, user: User) -> CurrentUser:
    areas = await auth_service.accessible_areas(db, user)
    return CurrentUser(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        avatar_url=user.avatar_url,
        areas=[AreaMembership(id=a.id, name=a.name, slug=a.slug, area_role=r) for a, r in areas],
    )


@router.get("/me", response_model=CurrentUser)
async def me(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    return await _current_user_payload(db, user)


@router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"ok": True}


# --- Solo desarrollo: login sin Google ---


@router.get("/dev-users", response_model=list[DevUser])
async def dev_users(db: AsyncSession = Depends(get_db)) -> list[DevUser]:
    if not settings.is_development:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    users = await auth_service.list_users(db)
    out: list[DevUser] = []
    for u in users:
        areas = await auth_service.accessible_areas(db, u)
        labels = ["Todas"] if u.role == "admin" else [a.name for a, _ in areas]
        out.append(DevUser(id=u.id, email=u.email, name=u.name, role=u.role, areas=labels))
    return out


@router.post("/dev-login", response_model=CurrentUser)
async def dev_login(
    payload: DevLoginRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    if not settings.is_development:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user = await db.get(User, payload.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    _set_session_cookie(response, user.id)
    return await _current_user_payload(db, user)


# --- Conexión OAuth real con Google (por usuario) ---


@router.get("/google/login")
async def google_login(user: User = Depends(get_current_user)) -> RedirectResponse:
    if settings.google_provider != "real" or not settings.google_client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google no configurado")
    state = secrets.token_urlsafe(24)
    response = RedirectResponse(google_oauth.authorize_url(state))
    response.set_cookie(
        "g_oauth_state", state, max_age=600, httponly=True,
        secure=settings.session_cookie_secure, samesite="lax", path="/",
    )
    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str = "",
    state: str = "",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if not code or not state or state != request.cookies.get("g_oauth_state"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estado OAuth inválido")
    token = await google_oauth.exchange_code(code)
    await google_service.store_real_token(db, user, token)
    response = RedirectResponse("/inicio")
    response.delete_cookie("g_oauth_state", path="/")
    return response
