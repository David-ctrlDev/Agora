from tests.factories import add_membership, create_area, create_user, login


async def test_areas_requires_auth(client):
    response = await client.get("/api/areas")
    assert response.status_code == 401


async def test_admin_sees_all_areas(client, session):
    await create_area(session, "Producción", "produccion")
    await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)

    response = await client.get("/api/areas")
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_member_sees_only_their_areas(client, session):
    prod = await create_area(session, "Producción", "produccion")
    await create_area(session, "IT", "it")
    user = await create_user(session, "ana@invesa.com", "Ana", role="member")
    await add_membership(session, user.id, prod.id, role="lead")
    await login(client, user.id)

    response = await client.get("/api/areas")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["slug"] == "produccion"


async def test_member_cannot_create_area(client, session):
    user = await create_user(session, "ana@invesa.com", "Ana", role="member")
    await login(client, user.id)

    response = await client.post("/api/areas", json={"name": "Nueva"})
    assert response.status_code == 403


async def test_admin_can_create_area(client, session):
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)

    response = await client.post("/api/areas", json={"name": "Recursos Humanos"})
    assert response.status_code == 201
    assert response.json()["slug"] == "recursos-humanos"
