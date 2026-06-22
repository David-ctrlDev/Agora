from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


def create_session_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.session_max_age_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_session_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


def create_pending_2fa_token(user_id: int) -> str:
    """Token corto que acredita haber pasado el primer factor; falta el código 2FA."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "scope": "2fa",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_pending_2fa_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("scope") != "2fa":
            return None
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
