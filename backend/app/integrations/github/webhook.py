import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any

from app.integrations.github.base import GitHubActivityEvent


def verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    """Verifica la firma HMAC-SHA256 (cabecera X-Hub-Signature-256) de GitHub."""
    if not secret or not signature_header:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def parse_webhook(
    event_type: str, payload: dict[str, Any]
) -> tuple[str | None, GitHubActivityEvent | None]:
    """Convierte un payload de webhook en (full_name, evento)."""
    full_name = (payload.get("repository") or {}).get("full_name")
    if not full_name:
        return None, None

    now = datetime.now(timezone.utc)
    base = f"https://github.com/{full_name}"

    if event_type == "push":
        commit = payload.get("head_commit") or {}
        commit_id = commit.get("id") or now.isoformat()
        return full_name, GitHubActivityEvent(
            external_id=f"{full_name}@{commit_id}",
            event_type="push",
            title=commit.get("message", "Push"),
            author=(payload.get("pusher") or {}).get("name"),
            html_url=commit.get("url") or base,
            occurred_at=now,
        )
    if event_type == "pull_request":
        pr = payload.get("pull_request") or {}
        number = pr.get("number", 0)
        return full_name, GitHubActivityEvent(
            external_id=f"{full_name}@pr#{number}",
            event_type="pull_request",
            title=f"PR #{number}: {pr.get('title', '')}",
            author=(pr.get("user") or {}).get("login"),
            html_url=pr.get("html_url") or base,
            occurred_at=now,
        )
    if event_type == "release":
        release = payload.get("release") or {}
        tag = release.get("tag_name", "release")
        return full_name, GitHubActivityEvent(
            external_id=f"{full_name}@release#{tag}",
            event_type="release",
            title=release.get("name") or tag,
            author=(release.get("author") or {}).get("login"),
            html_url=release.get("html_url") or base,
            occurred_at=now,
        )
    if event_type == "issues":
        issue = payload.get("issue") or {}
        number = issue.get("number", 0)
        return full_name, GitHubActivityEvent(
            external_id=f"{full_name}@issue#{number}",
            event_type="issues",
            title=f"Issue #{number}: {issue.get('title', '')}",
            author=(issue.get("user") or {}).get("login"),
            html_url=issue.get("html_url") or base,
            occurred_at=now,
        )
    return None, None
