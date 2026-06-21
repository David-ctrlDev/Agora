"""Ejecución de acciones del agente (con efecto externo). Solo tras confirmación."""
from datetime import datetime, timezone
from typing import Any

from app.integrations.google.factory import get_google_provider


def execute_create_meeting(params: dict[str, Any]) -> dict[str, Any]:
    provider = get_google_provider()
    when_raw = params.get("when")
    when = datetime.fromisoformat(when_raw) if when_raw else datetime.now(timezone.utc)
    event = provider.create_meeting(
        params.get("title", "Reunión"), params.get("attendees", []), when
    )
    return {
        "title": event.title,
        "attendees": params.get("attendees", []),
        "starts_at": event.starts_at.isoformat(),
        "meet_url": event.meet_url,
        "web_url": event.web_url,
    }


def execute_send_email(params: dict[str, Any]) -> dict[str, Any]:
    # Outbox de desarrollo: no se envía nada real; se registra para auditoría.
    return {
        "to": params.get("to", []),
        "subject": params.get("subject", ""),
        "body": params.get("body", ""),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
