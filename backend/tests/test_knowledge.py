from tests.factories import add_membership, create_area, create_user, login


async def test_knowledge_ingest_and_search_ranking(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    pid = (await client.post("/api/projects", json={"name": "P", "area_id": area.id})).json()["id"]

    await client.post(
        f"/api/projects/{pid}/documents",
        json={
            "title": "Permisos",
            "content": "Los permisos municipales son el principal riesgo del proyecto.",
        },
    )
    await client.post(
        f"/api/projects/{pid}/documents",
        json={
            "title": "Presupuesto",
            "content": "El presupuesto aprobado para la maquinaria es de mil millones.",
        },
    )

    docs = (await client.get(f"/api/projects/{pid}/documents")).json()
    assert len(docs) == 2

    results = (
        await client.post("/api/knowledge/search", json={"query": "riesgo de permisos"})
    ).json()
    assert len(results) >= 1
    assert results[0]["document_title"] == "Permisos"  # el más relevante primero


async def test_knowledge_search_scoped_by_area(client, session):
    prod = await create_area(session, "Producción", "produccion")
    it = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    bob = await create_user(session, "bob@invesa.com", "Bob", role="member")
    await add_membership(session, bob.id, it.id)

    await login(client, admin.id)
    pid = (
        await client.post("/api/projects", json={"name": "Secreto", "area_id": prod.id})
    ).json()["id"]
    await client.post(
        f"/api/projects/{pid}/documents",
        json={"title": "Confidencial", "content": "informacion sensible de produccion"},
    )

    # Bob (de IT) no debe recuperar documentos de un proyecto de Producción.
    await login(client, bob.id)
    results = (
        await client.post("/api/knowledge/search", json={"query": "informacion sensible"})
    ).json()
    assert all(r["project_id"] != pid for r in results)
