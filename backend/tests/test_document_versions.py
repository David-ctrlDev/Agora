from tests.factories import create_area, create_user, login


async def test_document_versioning_and_reindex(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    pid = (await client.post("/api/projects", json={"name": "P", "area_id": area.id})).json()["id"]

    doc = (
        await client.post(
            f"/api/projects/{pid}/documents",
            json={"title": "Acta", "content": "Version uno del acta."},
        )
    ).json()
    did = doc["id"]
    assert (await client.get(f"/api/documents/{did}/versions")).json() == []

    updated = await client.post(
        f"/api/documents/{did}/versions",
        data={"content": "Version dos del acta.", "title": "Acta v2"},
    )
    assert updated.status_code == 201, updated.text

    detail = (await client.get(f"/api/documents/{did}")).json()
    assert detail["title"] == "Acta v2"
    assert "Version dos" in detail["content_text"]

    versions = (await client.get(f"/api/documents/{did}/versions")).json()
    assert len(versions) == 1
    assert versions[0]["version_no"] == 1

    download = await client.get(f"/api/document-versions/{versions[0]['id']}/download")
    assert download.status_code == 200
    assert b"Version uno" in download.content

    results = (await client.post("/api/knowledge/search", json={"query": "version dos"})).json()
    assert any("version dos" in r["content"].lower() for r in results)
