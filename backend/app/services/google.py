from datetime import datetime, timedelta, timezone

from sqlalchemy import nullslast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import decrypt, encrypt
from app.integrations.google import oauth as google_oauth
from app.integrations.google import real_api
from app.integrations.google.factory import get_google_provider
from app.models.google_document import GoogleDocument
from app.models.oauth_token import OAuthToken
from app.models.user import User
from app.rag.extract import UnsupportedFile, extract_text

DEV_SCOPES = "drive.readonly calendar.events"


class GoogleNotConnected(Exception):
    """El usuario no ha conectado su cuenta de Google."""


async def get_token(db: AsyncSession, user_id: int) -> OAuthToken | None:
    result = await db.execute(
        select(OAuthToken).where(OAuthToken.user_id == user_id, OAuthToken.provider == "google")
    )
    return result.scalar_one_or_none()


async def status(db: AsyncSession, user: User) -> dict[str, object]:
    token = await get_token(db, user.id)
    return {
        "connected": token is not None,
        "scopes": token.scopes if token else None,
        "provider": settings.google_provider,
    }


async def connect_dev(db: AsyncSession, user: User) -> None:
    """Conexión simulada (solo desarrollo / proveedor mock)."""
    token = await get_token(db, user.id)
    if token is None:
        db.add(
            OAuthToken(
                user_id=user.id,
                provider="google",
                access_token=encrypt("dev-mock-access-token"),
                refresh_token=encrypt("dev-mock-refresh-token"),
                scopes=DEV_SCOPES,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
    else:
        token.access_token = encrypt("dev-mock-access-token")
        token.scopes = DEV_SCOPES
    await db.commit()


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


async def get_access_token(db: AsyncSession, user: User) -> str | None:
    """Devuelve un access token válido, refrescándolo si está por expirar."""
    token = await get_token(db, user.id)
    if token is None:
        return None
    access = decrypt(token.access_token)
    expired = token.expires_at is not None and token.expires_at <= datetime.now(timezone.utc) + timedelta(seconds=30)
    if expired and token.refresh_token:
        refresh = decrypt(token.refresh_token)
        if refresh:
            try:
                data = await google_oauth.refresh_access_token(refresh)
                access = data["access_token"]
                token.access_token = encrypt(access)
                token.expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=int(data.get("expires_in", 3600))
                )
                await db.commit()
            except Exception:
                pass
    return access


async def disconnect(db: AsyncSession, user: User) -> None:
    token = await get_token(db, user.id)
    if token is not None:
        await db.delete(token)
        await db.commit()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


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


async def sync_project(db: AsyncSession, user: User, project_id: int, project_name: str) -> int:
    new = 0
    if settings.google_provider == "real":
        access = await get_access_token(db, user)
        if not access:
            raise GoogleNotConnected()
        for f in await real_api.list_drive_files(access):
            if await _upsert_doc(
                db, project_id, "drive", f["external_id"], f["title"], f["mime_type"],
                f["web_url"], _parse_dt(f.get("modified_at")),
            ):
                new += 1
        for e in await real_api.list_calendar_events(access):
            if await _upsert_doc(
                db, project_id, "calendar", e["external_id"], e["title"], "event",
                e["web_url"], _parse_dt(e.get("starts_at")),
            ):
                new += 1
        await db.commit()
        return new

    provider = get_google_provider()
    for drive_file in provider.list_drive_files(project_name):
        if await _upsert_doc(
            db, project_id, "drive", drive_file.external_id, drive_file.title,
            drive_file.mime_type, drive_file.web_url, drive_file.modified_at,
        ):
            new += 1
    for event in provider.list_calendar_events(project_name):
        if await _upsert_doc(
            db, project_id, "calendar", event.external_id, event.title, "event",
            event.web_url, event.starts_at,
        ):
            new += 1
    await db.commit()
    return new


async def create_meeting(
    db: AsyncSession,
    user: User,
    project_id: int,
    title: str,
    attendees: list[str],
    when: str | None,
) -> dict[str, object]:
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
    end = starts_at + timedelta(hours=1)
    clean_attendees = [a.strip() for a in attendees if a.strip()]

    if settings.google_provider == "real":
        access = await get_access_token(db, user)
        if not access:
            raise GoogleNotConnected()
        event = await real_api.create_meeting(
            access, title.strip(), clean_attendees, starts_at.isoformat(), end.isoformat()
        )
        await _upsert_doc(
            db, project_id, "calendar", event.get("external_id") or event["title"],
            event["title"], "event", event.get("web_url"), starts_at,
        )
        await db.commit()
        return {
            "title": event["title"],
            "meet_url": event.get("meet_url"),
            "web_url": event.get("web_url"),
            "starts_at": starts_at,
        }

    provider = get_google_provider()
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


async def list_directory(db: AsyncSession, user: User) -> list[dict]:
    """Personas para invitar: directorio real de Workspace, o usuarios de la app (mock)."""
    if settings.google_provider == "real":
        access = await get_access_token(db, user)
        if access:
            try:
                people = await real_api.list_directory_people(access)
                if people:
                    return people
            except Exception:
                # p. ej. People API sin habilitar: caemos al directorio interno.
                pass
    rows = (await db.execute(select(User).where(User.is_active.is_(True)).order_by(User.name))).scalars().all()
    return [{"name": u.name, "email": u.email} for u in rows]


async def browse_drive(
    db: AsyncSession, user: User, folder_id: str | None, query: str | None, shared: bool = False
) -> list[dict]:
    """Carpetas y archivos de Drive para navegar/buscar (no persiste nada)."""
    if settings.google_provider == "real":
        access = await get_access_token(db, user)
        if not access:
            raise GoogleNotConnected()
        return await real_api.browse_drive(access, folder_id, query, shared)
    provider = get_google_provider()
    return [
        {
            "external_id": f.external_id,
            "title": f.title,
            "mime_type": f.mime_type,
            "web_url": f.web_url,
            "modified_at": f.modified_at.isoformat() if f.modified_at else None,
            "is_folder": False,
        }
        for f in provider.list_drive_files(query or "")
    ]


async def import_drive_documents(
    db: AsyncSession, user: User, project_id: int, items: list[dict]
) -> dict[str, int]:
    """Vincula los archivos de Drive elegidos e indexa su contenido en el RAG.

    Cada archivo queda como enlace (panel de Google) y, si su contenido es texto
    extraíble, también se trocea/embebe para que el agente pueda buscarlo y citarlo.
    """
    from app.models.document import Document
    from app.services import knowledge as knowledge_service

    access = await get_access_token(db, user) if settings.google_provider == "real" else None
    existing = set(
        (await db.execute(select(Document.title).where(Document.project_id == project_id)))
        .scalars()
        .all()
    )
    new = 0
    indexed = 0
    for it in items:
        title = it.get("title") or "(sin nombre)"
        if await _upsert_doc(
            db, project_id, "drive", it["external_id"], title,
            it.get("mime_type"), it.get("web_url"), _parse_dt(it.get("modified_at")),
        ):
            new += 1
        if access and title not in existing:
            try:
                name, mime, data = await real_api.fetch_drive_file_content(access, it["external_id"])
                text = extract_text(name, mime, data)
                if text.strip():
                    await knowledge_service.ingest_document(
                        db, project_id, title, text, source="drive", file_name=name, mime_type=mime
                    )
                    existing.add(title)
                    indexed += 1
            except Exception:
                # Binarios no extraíbles (p. ej. .pbix) u otros errores: solo queda el enlace.
                pass
    await db.commit()
    return {"new_documents": new, "indexed": indexed}


async def read_drive_file(db: AsyncSession, user: User, file_id: str) -> tuple[str, str]:
    """Devuelve (nombre, texto) del contenido de un archivo de Drive."""
    if settings.google_provider == "real":
        access = await get_access_token(db, user)
        if not access:
            raise GoogleNotConnected()
        name, mime, data = await real_api.fetch_drive_file_content(access, file_id)
        return name, extract_text(name, mime, data)
    return f"Documento de Drive {file_id}", (
        f"(Contenido simulado del archivo {file_id} de Drive para pruebas locales.)"
    )


async def free_busy(
    db: AsyncSession, user: User, emails: list[str], time_min: str, time_max: str
) -> dict[str, list[dict]]:
    """Disponibilidad (ocupado/libre) de las personas indicadas en una ventana."""
    cleaned = [e.strip() for e in emails if e.strip()]
    if not cleaned:
        return {}
    if settings.google_provider == "real":
        access = await get_access_token(db, user)
        if not access:
            raise GoogleNotConnected()
        return await real_api.free_busy(access, cleaned, time_min, time_max)
    return {e: [] for e in cleaned}


async def list_documents(db: AsyncSession, project_id: int) -> list[GoogleDocument]:
    result = await db.execute(
        select(GoogleDocument)
        .where(GoogleDocument.project_id == project_id)
        .order_by(nullslast(GoogleDocument.occurred_at.desc()))
    )
    return list(result.scalars().all())
