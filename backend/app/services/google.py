from datetime import datetime, timedelta, timezone

from sqlalchemy import nullslast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import encrypt
from app.integrations.google.factory import get_google_provider
from app.models.google_document import GoogleDocument
from app.models.oauth_token import OAuthToken
from app.models.user import User

DEV_SCOPES = "drive.readonly calendar.events"


async def get_token(db: AsyncSession, user_id: int) -> OAuthToken | None:
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user_id, OAuthToken.provider == "google"
        )
    )
    return result.scalar_one_or_none()


async def status(db: AsyncSession, user: User) -> dict[str, object]:
    token = await get_token(db, user.id)
    return {
        "connected": token is not None,
        "scopes": token.scopes if token else None,
        "provider": settings.google_provider,
    }


async def store_real_token(db: AsyncSession, user: User, token_data: dict) -> None:
    """Guarda (cifrado) el token OAuth real del usuario tras autorizar en Google."""
    existing = await get_token(db, user.id)
    access = encrypt(token_data["access_token"])
    refresh_raw = token_data.get("refresh_token")
    scopes = token_data.get("scope", "")
    expires = datetime.now(timezone.utc) + timedelta(seconds=int(token_data.get("expires_in", 3600)))
    if existing is not None:
        existing.access_token = access
        if refresh_raw:
            existing.refresh_token = encrypt(refresh_raw)
        existing.scopes = scopes
        existing.expires_at = expires
    else:
        db.add(
            OAuthToken(
                user_id=user.id,
                provider="google",
                access_token=access,
                refresh_token=encrypt(refresh_raw or ""),
                scopes=scopes,
                expires_at=expires,
            )
        )
    await db.commit()


async def connect_dev(db: AsyncSession, user: User) -> None:
    """Simula la conexión con Google guardando un token CIFRADO (solo desarrollo)."""
    token = await get_token(db, user.id)
    if token is None:
        token = OAuthToken(
            user_id=user.id,
            provider="google",
            access_token=encrypt("dev-mock-access-token"),
            refresh_token=encrypt("dev-mock-refresh-token"),
            scopes=DEV_SCOPES,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(token)
    else:
        token.access_token = encrypt("dev-mock-access-token")
        token.scopes = DEV_SCOPES
    await db.commit()


async def disconnect(db: AsyncSession, user: User) -> None:
    token = await get_token(db, user.id)
    if token is not None:
        await db.delete(token)
        await db.commit()


async def _upsert_doc(
    db: AsyncSession,
    project_id: int,
    source: str,
    external_id: str,
    title: str,
    kind: str | None,
    web_url: str | None,
    occurred_at: datetime | None,
) -> bool:
    existing = await db.execute(
        select(GoogleDocument.id).where(
            GoogleDocument.project_id == project_id,
            GoogleDocument.source == source,
            GoogleDocument.external_id == external_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False
    db.add(
        GoogleDocument(
            project_id=project_id,
            source=source,
            external_id=external_id,
            title=title[:500],
            kind=kind,
            web_url=web_url,
            occurred_at=occurred_at,
        )
    )
    return True


async def sync_project(db: AsyncSession, project_id: int, project_name: str) -> int:
    provider = get_google_provider()
    new = 0
    for drive_file in provider.list_drive_files(project_name):
        if await _upsert_doc(
            db,
            project_id,
            "drive",
            drive_file.external_id,
            drive_file.title,
            drive_file.mime_type,
            drive_file.web_url,
            drive_file.modified_at,
        ):
            new += 1
    for event in provider.list_calendar_events(project_name):
        if await _upsert_doc(
            db,
            project_id,
            "calendar",
            event.external_id,
            event.title,
            "event",
            event.web_url,
            event.starts_at,
        ):
            new += 1
    await db.commit()
    return new


async def create_meeting(
    db: AsyncSession,
    project_id: int,
    title: str,
    attendees: list[str],
    when: str | None,
) -> dict[str, object]:
    provider = get_google_provider()
    if when:
        try:
            starts_at = datetime.fromisoformat(when)
        except ValueError:
            starts_at = datetime.now(timezone.utc) + timedelta(days=1)
        if starts_at.tzinfo is None:
            if starts_at.hour == 0 and starts_at.minute == 0:
                starts_at = starts_at.replace(hour=15)
            starts_at = starts_at.replace(tzinfo=timezone.utc)
    else:
        starts_at = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
            hour=15, minute=0, second=0, microsecond=0
        )
    clean_attendees = [a.strip() for a in attendees if a.strip()]
    event = provider.create_meeting(title.strip(), clean_attendees, starts_at)
    await _upsert_doc(
        db, project_id, "calendar", event.external_id, event.title, "event", event.web_url, event.starts_at
    )
    await db.commit()
    return {
        "title": event.title,
        "meet_url": event.meet_url,
        "web_url": event.web_url,
        "starts_at": event.starts_at,
    }


async def list_documents(db: AsyncSession, project_id: int) -> list[GoogleDocument]:
    result = await db.execute(
        select(GoogleDocument)
        .where(GoogleDocument.project_id == project_id)
        .order_by(nullslast(GoogleDocument.occurred_at.desc()))
    )
    return list(result.scalars().all())
