from tests.factories import add_membership, create_area, create_user, login


async def test_project_and_overview_analytics(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    pid = (await client.post("/api/projects", json={"name": "P", "area_id": area.id})).json()["id"]
    await client.post(f"/api/projects/{pid}/tasks", json={"title": "T1", "status": "done"})
    await client.post(f"/api/projects/{pid}/tasks", json={"title": "T2", "status": "todo"})

    metrics = (await client.get(f"/api/projects/{pid}/analytics")).json()
    assert metrics["total"] == 2
    assert metrics["done"] == 1
    assert metrics["completion_pct"] == 50
    assert metrics["by_status"]["done"] == 1

    overview = (await client.get("/api/analytics/overview")).json()
    assert overview["totals"]["total_tasks"] == 2
    assert overview["totals"]["completion_pct"] == 50
    assert any(p["project_id"] == pid for p in overview["projects"])


async def test_analytics_scoped_by_area(client, session):
    it = await create_area(session, "IT", "it")
    amb = await create_area(session, "Ambiental", "ambiental")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    hidden = (await client.post("/api/projects", json={"name": "Secreto", "area_id": amb.id})).json()["id"]

    member = await create_user(session, "m@invesa.com", "M", role="member")
    await add_membership(session, member.id, it.id)
    await login(client, member.id)
    overview = (await client.get("/api/analytics/overview")).json()
    assert all(p["project_id"] != hidden for p in overview["projects"])
    assert (await client.get(f"/api/projects/{hidden}/analytics")).status_code == 404
