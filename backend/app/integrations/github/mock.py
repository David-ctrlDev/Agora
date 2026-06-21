import random
from datetime import datetime, timedelta, timezone

from app.integrations.github.base import GitHubActivityEvent

_COMMITS = [
    "Fix null check in sync",
    "Refactor service layer",
    "Add unit tests for scoping",
    "Bump dependencies",
    "Improve structured logging",
    "Handle edge case in parser",
    "Tidy imports",
    "Optimize area query",
    "Document API endpoints",
    "Fix typo in README",
]
_PRS = [
    "Add area filtering",
    "Improve dashboard layout",
    "Migrate to async sessions",
    "Wire proactive notifications",
    "Refactor auth dependency",
]
_ISSUES = [
    "Slow load on large projects",
    "Timezone bug in due dates",
    "Add CSV export",
    "Improve error messages",
]
_AUTHORS = ["ana", "carlos", "wilder", "dev-bot"]


class MockGitHubProvider:
    """Genera actividad determinista por repositorio, sin tocar la red."""

    def fetch_activity(self, full_name: str) -> list[GitHubActivityEvent]:
        rng = random.Random(full_name)
        now = datetime.now(timezone.utc)
        base = f"https://github.com/{full_name}"
        events: list[GitHubActivityEvent] = []

        for i in range(8):
            events.append(
                GitHubActivityEvent(
                    external_id=f"{full_name}@commit#{i}",
                    event_type="push",
                    title=rng.choice(_COMMITS),
                    author=rng.choice(_AUTHORS),
                    html_url=f"{base}/commit/{i}",
                    occurred_at=now - timedelta(days=rng.randint(0, 29), hours=rng.randint(0, 23)),
                )
            )
        for n in range(1, 4):
            events.append(
                GitHubActivityEvent(
                    external_id=f"{full_name}@pr#{n}",
                    event_type="pull_request",
                    title=f"PR #{n}: {rng.choice(_PRS)}",
                    author=rng.choice(_AUTHORS),
                    html_url=f"{base}/pull/{n}",
                    occurred_at=now - timedelta(days=rng.randint(0, 20)),
                )
            )
        events.append(
            GitHubActivityEvent(
                external_id=f"{full_name}@release#1",
                event_type="release",
                title=f"v1.{rng.randint(0, 9)}.0",
                author=rng.choice(_AUTHORS),
                html_url=f"{base}/releases",
                occurred_at=now - timedelta(days=rng.randint(1, 40)),
            )
        )
        for n in range(1, 3):
            events.append(
                GitHubActivityEvent(
                    external_id=f"{full_name}@issue#{n}",
                    event_type="issues",
                    title=f"Issue #{n}: {rng.choice(_ISSUES)}",
                    author=rng.choice(_AUTHORS),
                    html_url=f"{base}/issues/{n}",
                    occurred_at=now - timedelta(days=rng.randint(0, 25)),
                )
            )
        return events
