from tests.factories import add_membership, create_area, create_user, login


async def test_project_scoping_and_permissions(client, session):
    prod = await create_area(session, "Producción", "produccion")
    it = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    ana = await create_user(session, "ana@invesa.com", "Ana", role="member")
    await add_membership(session, ana.id, prod.id, role="lead")

    # Admin crea proyectos en dos áreas distintas.
    await login(client, admin.id)
    r1 = await client.post("/api/projects", json={"name": "P-Prod", "area_id": prod.id})
    assert r1.status_code == 201, r1.text
    r2 = await client.post("/api/projects", json={"name": "P-IT", "area_id": it.id})
    assert r2.status_code == 201, r2.text

    # Admin ve ambos.
    assert len((await client.get("/api/projects")).json()) == 2

    # Ana solo ve el de su área.
    await login(client, ana.id)
    projects = (await client.get("/api/projects")).json()
    assert len(projects) == 1
    assert projects[0]["name"] == "P-Prod"

    # Ana no puede crear en un área ajena.
    forbidden = await client.post("/api/projects", json={"name": "x", "area_id": it.id})
    assert forbidden.status_code == 403


async def test_project_member_grants_cross_area_access(client, session):
    prod = await create_area(session, "Producción", "produccion")
    it = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    bob = await create_user(session, "bob@invesa.com", "Bob", role="member")
    await add_membership(session, bob.id, it.id)

    await login(client, admin.id)
    created = (
        await client.post("/api/projects", json={"name": "Solo Prod", "area_id": prod.id})
    ).json()

    # Bob (de IT) no ve el proyecto de Producción...
    await login(client, bob.id)
    assert len((await client.get("/api/projects")).json()) == 0

    # ...hasta que el admin lo añade como miembro del proyecto.
    await login(client, admin.id)
    add = await client.post(
        f"/api/projects/{created['id']}/members", json={"user_id": bob.id, "role": "viewer"}
    )
    assert add.status_code == 201

    await login(client, bob.id)
    visible = (await client.get("/api/projects")).json()
    assert len(visible) == 1
    assert visible[0]["name"] == "Solo Prod"
