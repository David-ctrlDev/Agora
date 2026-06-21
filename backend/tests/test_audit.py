from tests.factories import create_area, create_user, login


async def test_audit_records_task_and_project_changes(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    pid = (await client.post("/api/projects", json={"name": "P", "area_id": area.id})).json()["id"]
    tid = (await client.post(f"/api/projects/{pid}/tasks", json={"title": "Hacer X"})).json()["id"]

    await client.patch(f"/api/tasks/{tid}", json={"status": "done"})
    await client.patch(f"/api/projects/{pid}", json={"status": "active"})

    audit = (await client.get(f"/api/projects/{pid}/audit")).json()
    actions = [a["action"] for a in audit]
    assert "created" in actions
    assert "updated" in actions
    assert "status_changed" in actions
    assert any(a["actor_name"] == "Admin" for a in audit)
    assert any("estado todo→done" in a["summary"] for a in audit)
