import random
from datetime import datetime, timedelta, timezone

from app.integrations.google.base import CalendarEvent, DriveFile

_DOCS = [
    ("Acta de reunión", "application/vnd.google-apps.document"),
    ("Presupuesto", "application/vnd.google-apps.spreadsheet"),
    ("Plan de proyecto", "application/vnd.google-apps.document"),
    ("Presentación de avance", "application/vnd.google-apps.presentation"),
    ("Especificaciones técnicas", "application/pdf"),
]
_EVENTS = [
    "Reunión de seguimiento",
    "Revisión de avances",
    "Comité de proyecto",
    "Planificación semanal",
]


class MockGoogleProvider:
    """Drive y Calendar simulados de forma determinista por proyecto (sin red)."""

    def list_drive_files(self, seed: str) -> list[DriveFile]:
        rng = random.Random(f"drive:{seed}")
        now = datetime.now(timezone.utc)
        files: list[DriveFile] = []
        for i, (title, mime) in enumerate(rng.sample(_DOCS, k=4)):
            files.append(
                DriveFile(
                    external_id=f"{seed}:file:{i}",
                    title=f"{title} · {seed}",
                    mime_type=mime,
                    web_url=f"https://drive.google.com/file/{seed.replace(' ', '-')}-{i}",
                    modified_at=now - timedelta(days=rng.randint(0, 30)),
                )
            )
        return files

    def list_calendar_events(self, seed: str) -> list[CalendarEvent]:
        rng = random.Random(f"cal:{seed}")
        now = datetime.now(timezone.utc)
        events: list[CalendarEvent] = []
        for i in range(3):
            start = now + timedelta(days=rng.randint(-5, 14), hours=rng.randint(8, 17))
            events.append(
                CalendarEvent(
                    external_id=f"{seed}:event:{i}",
                    title=rng.choice(_EVENTS),
                    web_url=f"https://calendar.google.com/event/{seed.replace(' ', '-')}-{i}",
                    starts_at=start,
                    meet_url=f"https://meet.google.com/mock-{abs(hash(seed)) % 1000}-{i}",
                )
            )
        return events

    def create_meeting(
        self, title: str, attendees: list[str], starts_at: datetime
    ) -> CalendarEvent:
        slug = abs(hash((title, tuple(attendees), starts_at.isoformat()))) % 100000
        return CalendarEvent(
            external_id=f"created:event:{slug}",
            title=title,
            web_url=f"https://calendar.google.com/event/created-{slug}",
            starts_at=starts_at,
            meet_url=f"https://meet.google.com/agora-{slug}",
        )
