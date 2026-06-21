from datetime import date, timedelta

from tests.factories import add_membership, create_area, create_user, login


async def test_detection_inbox_and_idempotency(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    carlos = await create_user(session, "carlos@invesa.com", "Carlos", role="member")
    await add_membership(session, carlos.id, area.id, role="lead")

    await login(client, admin.id)
    pid = (await client.post("/api/projects", json={"name": "P", "area_id": area.id})).json()["id"]
    past = (date.today() - timedelta(days=3)).isoformat()
    await client.post(f"/api/projects/{pid}/tasks", json={"title": "Vencida", "due_date": past})
    await client.post(f"/api/projects/{pid}/tasks", json={"title": "Bloqueada", "status": "blocked"})

    created = (await client.post("/api/notifications/run")).json()["created"]
    assert created >= 2
    assert (await client.post("/api/notifications/run")).json()["created"] == 0  # idempotente

    admin_types = {n["type"] for n in (await client.get("/api/notifications")).json()}
    assert "overdue_tasks" in admin_types
    assert "blocked_tasks" in admin_types

    # El lead del área también recibe las alertas (segmentación por área).
    await login(client, carlos.id)
    assert len((await client.get("/api/notifications")).json()) >= 2

    await client.post("/api/notifications/read-all")
    assert (await client.get("/api/notifications/unread-count")).json()["count"] == 0


async def test_run_requires_admin(client, session):
    member = await create_user(session, "m@invesa.com", "M", role="member")
    await login(client, member.id)
    assert (await client.post("/api/notifications/run")).status_code == 403
