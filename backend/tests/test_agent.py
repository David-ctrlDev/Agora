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
