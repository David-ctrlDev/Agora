from tests.factories import create_area, create_user, login


async def test_upload_text_file_indexes_and_downloads(client, session):
    area = await create_area(session, "Ambiental", "ambiental")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    pid = (await client.post("/api/projects", json={"name": "P", "area_id": area.id})).json()["id"]

    files = {"file": ("acta.txt", "Los permisos ambientales vencen en agosto.".encode(), "text/plain")}
    created = await client.post(
        f"/api/projects/{pid}/documents/upload", files=files, data={"title": "Acta"}
    )
    assert created.status_code == 201, created.text
    doc = created.json()
    assert doc["source"] == "file"
    assert doc["file_name"] == "acta.txt"

    detail = (await client.get(f"/api/documents/{doc['id']}")).json()
    assert "permisos ambientales" in detail["content_text"]

    results = (
        await client.post("/api/knowledge/search", json={"query": "permisos ambientales"})
    ).json()
    assert any("permiso" in r["content"].lower() for r in results)

    download = await client.get(f"/api/documents/{doc['id']}/download")
    assert download.status_code == 200
    assert b"permisos ambientales" in download.content


async def test_unsupported_binary_is_rejected(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    pid = (await client.post("/api/projects", json={"name": "P", "area_id": area.id})).json()["id"]

    files = {"file": ("x.bin", b"\x00\x01\x02\xff\xfe", "application/octet-stream")}
    resp = await client.post(f"/api/projects/{pid}/documents/upload", files=files)
    assert resp.status_code == 415
