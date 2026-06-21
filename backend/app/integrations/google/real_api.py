"""Llamadas reales a las APIs de Google con el token OAuth del usuario."""
import base64
import uuid
from email.message import EmailMessage

import httpx

_TIMEOUT = 25


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
