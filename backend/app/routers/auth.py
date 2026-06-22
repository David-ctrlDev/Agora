import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core import totp
from app.core.crypto import decrypt, encrypt
from app.core.security import (
    create_pending_2fa_token,
    create_session_token,
    decode_pending_2fa_token,
    decode_session_token,
)
from app.integrations.google import oauth as google_oauth
from app.models.user import User
from app.schemas.auth import (
    AreaMembership,
    CurrentUser,
    DevLoginRequest,
    DevUser,
    LoginResponse,
    TwoFactorCode,
    TwoFactorSetup,
)
from app.services import auth as auth_service
from app.services import google as google_service

PENDING_2FA_COOKIE = "g_2fa"

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
        twofa_enabled=user.totp_enabled,
    )


def _set_pending_2fa_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        key=PENDING_2FA_COOKIE,
        value=create_pending_2fa_token(user_id),
        max_age=600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
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


@router.post("/dev-login", response_model=LoginResponse)
async def dev_login(
    payload: DevLoginRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    if not settings.is_development:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user = await db.get(User, payload.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if user.totp_enabled:
        _set_pending_2fa_cookie(response, user.id)
        return LoginResponse(needs_2fa=True)
    _set_session_cookie(response, user.id)
    return LoginResponse(user=await _current_user_payload(db, user))


# --- Inicio de sesión y conexión con Google (OAuth real) ---


@router.get("/login/google")
async def login_google() -> RedirectResponse:
    """Inicia sesión con Google: autentica y conecta el Workspace del usuario."""
    if settings.google_provider != "real" or not settings.google_client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google no configurado")
    state = secrets.token_urlsafe(24)
    response = RedirectResponse(google_oauth.authorize_url(state))
    response.set_cookie(
        "g_login_state", state, max_age=600, httponly=True,
        secure=settings.session_cookie_secure, samesite="lax", path="/",
    )
    return response


@router.get("/google/login")
async def google_connect(user: User = Depends(get_current_user)) -> RedirectResponse:
    """Conecta Google a la sesión actual (usuario ya autenticado)."""
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
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    login_state = request.cookies.get("g_login_state")
    connect_state = request.cookies.get("g_oauth_state")
    is_login = bool(state) and state == login_state
    is_connect = bool(state) and state == connect_state
    if not code or not (is_login or is_connect):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estado OAuth inválido")
    token = await google_oauth.exchange_code(code)

    if is_login:
        info = await google_oauth.userinfo(token["access_token"])
        email = (info.get("email") or "").lower()
        if not email:
            resp = RedirectResponse("/login?error=google")
            resp.delete_cookie("g_login_state", path="/")
            return resp
        if settings.google_allowed_hd and info.get("hd") != settings.google_allowed_hd:
            resp = RedirectResponse("/login?error=domain")
            resp.delete_cookie("g_login_state", path="/")
            return resp
        user = await auth_service.resolve_google_user(
            db,
            email=email,
            sub=info.get("sub"),
            name=info.get("name"),
            avatar_url=info.get("picture"),
        )
        if user is None:
            resp = RedirectResponse("/login?error=not_registered")
            resp.delete_cookie("g_login_state", path="/")
            return resp
        await google_service.store_real_token(db, user, token)
        if user.totp_enabled:
            resp = RedirectResponse("/login?2fa=1")
            resp.delete_cookie("g_login_state", path="/")
            _set_pending_2fa_cookie(resp, user.id)
            return resp
        resp = RedirectResponse("/inicio")
        resp.delete_cookie("g_login_state", path="/")
        _set_session_cookie(resp, user.id)
        return resp

    # Conexión: requiere una sesión vigente.
    session = request.cookies.get(settings.session_cookie_name)
    uid = decode_session_token(session) if session else None
    user = await db.get(User, uid) if uid else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    await google_service.store_real_token(db, user, token)
    resp = RedirectResponse("/inicio")
    resp.delete_cookie("g_oauth_state", path="/")
    return resp


# --- Autenticación en dos pasos (TOTP) ---


@router.post("/2fa/setup", response_model=TwoFactorSetup)
async def twofa_setup(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> TwoFactorSetup:
    if user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El 2FA ya está activo")
    secret = totp.generate_secret()
    user.totp_secret = encrypt(secret)
    await db.commit()
    return TwoFactorSetup(secret=secret, otpauth_uri=totp.provisioning_uri(secret, user.email))


@router.post("/2fa/enable", response_model=CurrentUser)
async def twofa_enable(
    payload: TwoFactorCode,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    if not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Genera primero el código")
    if not totp.verify(decrypt(user.totp_secret), payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código inválido")
    user.totp_enabled = True
    await db.commit()
    return await _current_user_payload(db, user)


@router.post("/2fa/disable", response_model=CurrentUser)
async def twofa_disable(
    payload: TwoFactorCode,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    if user.totp_enabled and not totp.verify(decrypt(user.totp_secret or ""), payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código inválido")
    user.totp_enabled = False
    user.totp_secret = None
    await db.commit()
    return await _current_user_payload(db, user)


@router.post("/2fa/verify", response_model=CurrentUser)
async def twofa_verify(
    payload: TwoFactorCode,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    pending = request.cookies.get(PENDING_2FA_COOKIE)
    uid = decode_pending_2fa_token(pending) if pending else None
    user = await db.get(User, uid) if uid else None
    if user is None or not user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión 2FA inválida")
    if not totp.verify(decrypt(user.totp_secret or ""), payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código inválido")
    _set_session_cookie(response, user.id)
    response.delete_cookie(PENDING_2FA_COOKIE, path="/")
    return await _current_user_payload(db, user)
