import hashlib
import hmac
import json

from app.core.config import settings
from tests.factories import create_area, create_user, login


async def _project(client, area_id: int) -> int:
    return (await client.post("/api/projects", json={"name": "P", "area_id": area_id})).json()["id"]


async def test_github_link_sync_activity(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    pid = await _project(client, area.id)

    linked = await client.post(f"/api/projects/{pid}/github/repos", json={"full_name": "invesa/agora"})
    assert linked.status_code == 201
    repo_id = linked.json()["id"]

    activity = (await client.get(f"/api/projects/{pid}/github/activity")).json()
    assert len(activity) == 14  # 8 commits + 3 PRs + 1 release + 2 issues

    # Re-sincronizar no duplica.
    resync = await client.post(f"/api/github/repos/{repo_id}/sync")
    assert resync.json()["new_events"] == 0


async def test_github_webhook_signature(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    pid = await _project(client, area.id)
    await client.post(f"/api/projects/{pid}/github/repos", json={"full_name": "invesa/agora"})

    body = json.dumps(
        {
            "repository": {"full_name": "invesa/agora"},
            "head_commit": {"id": "hook1", "message": "hook commit", "url": "u"},
            "pusher": {"name": "ana"},
        }
    ).encode()
    secret = settings.github_webhook_secret or "dev-webhook-secret"
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    ok = await client.post(
        "/api/github/webhook",
        content=body,
        headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": signature},
    )
    assert ok.status_code == 200
    assert ok.json()["stored"] == 1

    bad = await client.post(
        "/api/github/webhook",
        content=body,
        headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": "sha256=bad"},
    )
    assert bad.status_code == 401
