from datetime import date, timedelta

from tests.factories import create_area, create_user, login


async def test_sprint_crud_counts_and_burndown(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    pid = (await client.post("/api/projects", json={"name": "P", "area_id": area.id})).json()["id"]

    start = date.today().isoformat()
    end = (date.today() + timedelta(days=4)).isoformat()
    sid = (
        await client.post(
            f"/api/projects/{pid}/sprints",
            json={"name": "Sprint 1", "start_date": start, "end_date": end},
        )
    ).json()["id"]

    t1 = (await client.post(f"/api/projects/{pid}/tasks", json={"title": "A"})).json()["id"]
    t2 = (await client.post(f"/api/projects/{pid}/tasks", json={"title": "B"})).json()["id"]
    await client.patch(f"/api/tasks/{t1}", json={"sprint_id": sid})
    await client.patch(f"/api/tasks/{t2}", json={"sprint_id": sid})

    done = (await client.patch(f"/api/tasks/{t1}", json={"status": "done"})).json()
    assert done["completed_at"] is not None
    assert done["sprint_id"] == sid

    sprints = (await client.get(f"/api/projects/{pid}/sprints")).json()
    assert sprints[0]["total"] == 2
    assert sprints[0]["done"] == 1
    assert sprints[0]["completion_pct"] == 50

    burndown = (await client.get(f"/api/sprints/{sid}/burndown")).json()
    assert burndown["total"] == 2
    assert len(burndown["points"]) == 5
    # Hoy ya hay una tarea cerrada -> quedan 1 pendiente.
    assert burndown["points"][0]["remaining"] == 1
    # Días futuros aún no tienen dato real.
    assert burndown["points"][-1]["remaining"] is None


async def test_reopening_task_clears_completed_at(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    pid = (await client.post("/api/projects", json={"name": "P", "area_id": area.id})).json()["id"]
    tid = (await client.post(f"/api/projects/{pid}/tasks", json={"title": "X"})).json()["id"]

    done = (await client.patch(f"/api/tasks/{tid}", json={"status": "done"})).json()
    assert done["completed_at"] is not None
    reopened = (await client.patch(f"/api/tasks/{tid}", json={"status": "in_progress"})).json()
    assert reopened["completed_at"] is None
