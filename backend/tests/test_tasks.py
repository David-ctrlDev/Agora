from tests.factories import add_membership, create_area, create_user, login


async def _project(client, area_id: int) -> int:
    response = await client.post("/api/projects", json={"name": "P", "area_id": area_id})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_tasks_crud_and_my_tasks(client, session):
    prod = await create_area(session, "Producción", "produccion")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    ana = await create_user(session, "ana@invesa.com", "Ana", role="member")
    await add_membership(session, ana.id, prod.id)

    await login(client, admin.id)
    pid = await _project(client, prod.id)
    created = await client.post(
        f"/api/projects/{pid}/tasks",
        json={"title": "T1", "assignee_id": ana.id, "priority": "high"},
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    tasks = (await client.get(f"/api/projects/{pid}/tasks")).json()
    assert len(tasks) == 1
    assert tasks[0]["assignee_name"] == "Ana"

    # Cerrar la tarea -> sale de "mis tareas" (pendientes).
    await client.patch(f"/api/tasks/{task_id}", json={"status": "done"})
    await login(client, ana.id)
    assert len((await client.get("/api/tasks/mine")).json()) == 0

    # Reabrir -> vuelve a aparecer.
    await login(client, admin.id)
    await client.patch(f"/api/tasks/{task_id}", json={"status": "in_progress"})
    await login(client, ana.id)
    mine = (await client.get("/api/tasks/mine")).json()
    assert len(mine) == 1
    assert mine[0]["project_name"] == "P"


async def test_outsider_cannot_access_project_tasks(client, session):
    prod = await create_area(session, "Producción", "produccion")
    it = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    bob = await create_user(session, "bob@invesa.com", "Bob", role="member")
    await add_membership(session, bob.id, it.id)

    await login(client, admin.id)
    pid = await _project(client, prod.id)

    await login(client, bob.id)
    assert (await client.get(f"/api/projects/{pid}/tasks")).status_code == 404
    assert (
        await client.post(f"/api/projects/{pid}/tasks", json={"title": "x"})
    ).status_code == 404
