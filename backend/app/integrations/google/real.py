"""Adaptador real de Google Workspace (Drive/Calendar). No se usa en modo mock.

Se activaría con `settings.google_provider == "real"` usando los tokens OAuth
del usuario (cifrados en `oauth_tokens`) y llamadas con httpx/SDK de Google.
Esqueleto para no realizar peticiones externas en desarrollo.
"""
from datetime import datetime

from app.integrations.google.base import CalendarEvent, DriveFile


class RealGoogleProvider:  # pragma: no cover
    def list_drive_files(self, seed: str) -> list[DriveFile]:
        raise NotImplementedError("Requiere credenciales y red; usa el proveedor mock.")

    def list_calendar_events(self, seed: str) -> list[CalendarEvent]:
        raise NotImplementedError("Requiere credenciales y red; usa el proveedor mock.")

    def create_meeting(
        self, title: str, attendees: list[str], starts_at: datetime
    ) -> CalendarEvent:
        raise NotImplementedError("Requiere credenciales y red; usa el proveedor mock.")
