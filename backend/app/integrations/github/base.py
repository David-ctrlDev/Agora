from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class GitHubActivityEvent:
    external_id: str
    event_type: str  # push | pull_request | release | issues
    title: str
    author: str | None
    html_url: str | None
    occurred_at: datetime


class GitHubProvider(Protocol):
    def fetch_activity(self, full_name: str) -> list[GitHubActivityEvent]:
        """Devuelve la actividad reciente de un repositorio (owner/repo)."""
        ...
