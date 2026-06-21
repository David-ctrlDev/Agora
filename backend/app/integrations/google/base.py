from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class DriveFile:
    external_id: str
    title: str
    mime_type: str
    web_url: str
    modified_at: datetime


@dataclass
class CalendarEvent:
    external_id: str
    title: str
    web_url: str
    starts_at: datetime
    meet_url: str | None = None


class GoogleProvider(Protocol):
    def list_drive_files(self, seed: str) -> list[DriveFile]: ...

    def list_calendar_events(self, seed: str) -> list[CalendarEvent]: ...

    def create_meeting(
        self, title: str, attendees: list[str], starts_at: datetime
    ) -> CalendarEvent: ...
