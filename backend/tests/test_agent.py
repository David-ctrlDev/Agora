from tests.factories import create_area, create_user, login


async def test_agent_read_tool_and_action_flow(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    await client.post("/api/projects", json={"name": "Migración ERP", "area_id": area.id})

    conv_id = (await client.post("/api/agent/conversations", json={})).json()["id"]

    # Tool de lectura (sin acción).
    read = await client.post(
        f"/api/agent/conversations/{conv_id}/messages",
        json={"content": "como van mis proyectos"},
    )
    assert read.status_code == 200
    assert "Estado de tus proyectos" in read.json()["content"]
    assert read.json()["action"] is None

    # Acción: queda pendiente (no se ejecuta sin confirmación).
    action_msg = await client.post(
        f"/api/agent/conversations/{conv_id}/messages",
        json={"content": "crea una reunion con ana@invesa.com sobre el cierre"},
    )
    action = action_msg.json()["action"]
    assert action is not None
    assert action["action_type"] == "create_meeting"
    assert action["status"] == "pending"

    # Confirmación humana -> se ejecuta.
    confirmed = await client.post(f"/api/agent/actions/{action['id']}/confirm")
    assert confirmed.status_code == 200
    assert "meet.google.com" in confirmed.json()["content"]

    statuses = [
        m["action"]["status"]
        for m in (await client.get(f"/api/agent/conversations/{conv_id}/messages")).json()
        if m["action"]
    ]
    assert "executed" in statuses


async def test_agent_conversations_are_private(client, session):
    user_a = await create_user(session, "a@invesa.com", "A", role="admin")
    user_b = await create_user(session, "b@invesa.com", "B", role="admin")

    await login(client, user_a.id)
    conv_id = (await client.post("/api/agent/conversations", json={})).json()["id"]

    await login(client, user_b.id)
    assert (await client.get(f"/api/agent/conversations/{conv_id}/messages")).status_code == 404


async def test_agent_creates_project_and_task(client, session):
    await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    conv = (await client.post("/api/agent/conversations", json={})).json()["id"]

    created = await client.post(
        f"/api/agent/conversations/{conv}/messages",
        json={"content": "crea el proyecto Innovacion en IT"},
    )
    action = created.json()["action"]
    assert action["action_type"] == "create_project"
    confirmed = await client.post(f"/api/agent/actions/{action['id']}/confirm")
    assert "creado en IT" in confirmed.json()["content"]
    assert any(p["name"] == "Innovacion" for p in (await client.get("/api/projects")).json())

    task_msg = await client.post(
        f"/api/agent/conversations/{conv}/messages",
        json={"content": "crea una tarea Revisar contratos en el proyecto Innovacion"},
    )
    task_action = task_msg.json()["action"]
    assert task_action["action_type"] == "create_task"
    task_confirmed = await client.post(f"/api/agent/actions/{task_action['id']}/confirm")
    assert "Tarea" in task_confirmed.json()["content"]

