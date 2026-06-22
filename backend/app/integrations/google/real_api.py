"""Llamadas reales a las APIs de Google con el token OAuth del usuario."""
import base64
import uuid
from email.message import EmailMessage

import httpx

_TIMEOUT = 25
_FOLDER_MIME = "application/vnd.google-apps.folder"
# Cómo exportar a texto cada tipo de documento nativo de Google.
_GOOGLE_EXPORT = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def list_directory_people(access_token: str, limit: int = 300) -> list[dict]:
    people: list[dict] = []
    page_token: str | None = None
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        while len(people) < limit:
            params = {
                "readMask": "names,emailAddresses",
                "sources": "DIRECTORY_SOURCE_TYPE_DOMAIN_PROFILE",
                "pageSize": 100,
            }
            if page_token:
                params["pageToken"] = page_token
            r = await client.get(
                "https://people.googleapis.com/v1/people:listDirectoryPeople",
                params=params,
                headers=_headers(access_token),
            )
            r.raise_for_status()
            data = r.json()
            for p in data.get("people", []):
                emails = p.get("emailAddresses") or []
                if not emails:
                    continue
                names = p.get("names") or []
                people.append(
                    {
                        "name": names[0]["displayName"] if names else emails[0]["value"],
                        "email": emails[0]["value"],
                    }
                )
            page_token = data.get("nextPageToken")
            if not page_token:
                break
    seen: set[str] = set()
    out: list[dict] = []
    for p in sorted(people, key=lambda x: x["name"].lower()):
        if p["email"] not in seen:
            seen.add(p["email"])
            out.append(p)
    return out[:limit]


async def list_drive_files(access_token: str, limit: int = 25) -> list[dict]:
    params = {
        "pageSize": limit,
        "fields": "files(id,name,mimeType,webViewLink,modifiedTime)",
        "orderBy": "modifiedTime desc",
        "q": "trashed=false",
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(
            "https://www.googleapis.com/drive/v3/files", params=params, headers=_headers(access_token)
        )
        r.raise_for_status()
        data = r.json()
    return [
        {
            "external_id": f["id"],
            "title": f.get("name", "(sin nombre)"),
            "mime_type": f.get("mimeType"),
            "web_url": f.get("webViewLink"),
            "modified_at": f.get("modifiedTime"),
        }
        for f in data.get("files", [])
    ]


def _drive_entry(f: dict) -> dict:
    mime = f.get("mimeType")
    return {
        "external_id": f["id"],
        "title": f.get("name", "(sin nombre)"),
        "mime_type": mime,
        "web_url": f.get("webViewLink"),
        "modified_at": f.get("modifiedTime"),
        "is_folder": mime == _FOLDER_MIME,
    }


async def browse_drive(
    access_token: str,
    folder_id: str | None = None,
    query: str | None = None,
    shared: bool = False,
    limit: int = 100,
) -> list[dict]:
    """Lista carpetas y archivos: por carpeta, por búsqueda, o lo compartido conmigo."""
    query = (query or "").strip()
    if query:
        safe = query.replace("\\", "\\\\").replace("'", "\\'")
        q = f"name contains '{safe}' and trashed = false"
    elif shared and not folder_id:
        # Raíz de "Compartido conmigo": archivos/carpetas que otros compartieron.
        q = "sharedWithMe = true and trashed = false"
    else:
        parent = folder_id or "root"
        q = f"'{parent}' in parents and trashed = false"
    params = {
        "pageSize": limit,
        "fields": "files(id,name,mimeType,webViewLink,modifiedTime)",
        "orderBy": "folder,name",
        "q": q,
        # Incluir elementos de unidades compartidas además de Mi unidad.
        "includeItemsFromAllDrives": "true",
        "supportsAllDrives": "true",
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(
            "https://www.googleapis.com/drive/v3/files", params=params, headers=_headers(access_token)
        )
        r.raise_for_status()
        data = r.json()
    return [_drive_entry(f) for f in data.get("files", [])]


async def fetch_drive_file_content(access_token: str, file_id: str) -> tuple[str, str, bytes]:
    """Devuelve (nombre, mime_type, bytes) de un archivo de Drive.

    Los documentos nativos de Google (Docs/Sheets/Slides) se exportan a texto;
    los binarios (PDF, Word, etc.) se descargan tal cual para extraer su texto luego.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        meta = await client.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={"fields": "id,name,mimeType"},
            headers=_headers(access_token),
        )
        meta.raise_for_status()
        info = meta.json()
        name = info.get("name", "documento")
        mime = info.get("mimeType", "")
        if mime in _GOOGLE_EXPORT:
            export_mime = _GOOGLE_EXPORT[mime]
            resp = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}/export",
                params={"mimeType": export_mime},
                headers=_headers(access_token),
            )
            resp.raise_for_status()
            return name, export_mime, resp.content
        resp = await client.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={"alt": "media"},
            headers=_headers(access_token),
        )
        resp.raise_for_status()
        return name, mime, resp.content


async def list_calendar_events(access_token: str, limit: int = 15) -> list[dict]:
    from datetime import datetime, timezone

    params = {
        "maxResults": limit,
        "orderBy": "startTime",
        "singleEvents": "true",
        "timeMin": datetime.now(timezone.utc).isoformat(),
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            params=params,
            headers=_headers(access_token),
        )
        r.raise_for_status()
        data = r.json()
    out = []
    for e in data.get("items", []):
        start = e.get("start") or {}
        out.append(
            {
                "external_id": e["id"],
                "title": e.get("summary", "(sin título)"),
                "web_url": e.get("htmlLink"),
                "starts_at": start.get("dateTime") or start.get("date"),
                "meet_url": e.get("hangoutLink"),
            }
        )
    return out


async def create_meeting(
    access_token: str, title: str, attendees: list[str], start_iso: str, end_iso: str
) -> dict:
    body = {
        "summary": title,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
        "attendees": [{"email": a} for a in attendees],
        "conferenceData": {
            "createRequest": {
                "requestId": uuid.uuid4().hex,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    params = {"conferenceDataVersion": 1, "sendUpdates": "all"}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            params=params,
            json=body,
            headers=_headers(access_token),
        )
        r.raise_for_status()
        e = r.json()
    return {
        "external_id": e.get("id"),
        "title": e.get("summary", title),
        "web_url": e.get("htmlLink"),
        "meet_url": e.get("hangoutLink"),
        "starts_at": (e.get("start") or {}).get("dateTime"),
    }


async def free_busy(
    access_token: str, emails: list[str], time_min: str, time_max: str
) -> dict[str, list[dict]]:
    """Intervalos ocupados de cada persona en una ventana (Calendar freeBusy)."""
    body = {"timeMin": time_min, "timeMax": time_max, "items": [{"id": e} for e in emails]}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(
            "https://www.googleapis.com/calendar/v3/freeBusy",
            json=body,
            headers=_headers(access_token),
        )
        r.raise_for_status()
        data = r.json()
    out: dict[str, list[dict]] = {}
    for email, info in (data.get("calendars") or {}).items():
        out[email] = [
            {"start": b.get("start"), "end": b.get("end")} for b in (info.get("busy") or [])
        ]
    return out


async def send_email(access_token: str, to: list[str], subject: str, body: str) -> dict:
    message = EmailMessage()
    message["To"] = ", ".join(to)
    message["Subject"] = subject
    message.set_content(body)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            json={"raw": raw},
            headers=_headers(access_token),
        )
        r.raise_for_status()
        return r.json()
