from app.agent import actions
from tests.factories import create_area, create_user, login


async def test_create_task_self_assign_and_accent_insensitive(client, session):
    area = await create_area(session, "Producción", "produccion")
    admin = await create_user(session, "admin@invesa.com", "Admin Uno", role="admin")
    await login(client, admin.id)
    pid = (
        await client.post("/api/projects", json={"name": "Renovación planta", "area_id": area.id})
    ).json()["id"]

    # Nombre de proyecto SIN tilde y responsable "mí": debe resolver ambos.
    result = await actions.execute_create_task(
        session, admin, {"title": "Tarea X", "project_name": "renovacion planta", "assignee": "mí"}
    )
    assert result["ok"] is True, result
    assert result["assignee"] == "Admin Uno"

    tasks = (await client.get(f"/api/projects/{pid}/tasks")).json()
    task = next(t for t in tasks if t["title"] == "Tarea X")
    assert task["assignee_id"] == admin.id


async def test_create_task_assign_to_other_person(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    ana = await create_user(session, "ana@invesa.com", "Ana Gómez", role="member")
    await login(client, admin.id)
    pid = (await client.post("/api/projects", json={"name": "ERP", "area_id": area.id})).json()["id"]

    result = await actions.execute_create_task(
        session, admin, {"title": "Configurar", "project_name": "ERP", "assignee": "ana"}
    )
    assert result["ok"] is True
    assert result["assignee"] == "Ana Gómez"

    tasks = (await client.get(f"/api/projects/{pid}/tasks")).json()
    assert next(t for t in tasks if t["title"] == "Configurar")["assignee_id"] == ana.id
