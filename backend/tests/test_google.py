from sqlalchemy import select

from app.core.crypto import decrypt
from app.models.oauth_token import OAuthToken
from tests.factories import create_area, create_user, login


async def test_google_connect_encrypts_token(client, session):
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)

    assert (await client.get("/api/google/status")).json()["connected"] is False

    connected = await client.post("/api/google/connect")
    assert connected.status_code == 200
    assert connected.json()["connected"] is True

    token = (
        await session.execute(select(OAuthToken).where(OAuthToken.user_id == admin.id))
    ).scalar_one()
    # Guardado cifrado en reposo (Fernet); nunca en claro.
    assert token.access_token.startswith("gAAAA")
    assert token.access_token != "dev-mock-access-token"
    assert decrypt(token.access_token) == "dev-mock-access-token"


async def test_google_sync_documents(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    pid = (await client.post("/api/projects", json={"name": "P", "area_id": area.id})).json()["id"]

    synced = await client.post(f"/api/projects/{pid}/google/sync")
    assert synced.json()["new_documents"] == 7  # 4 Drive + 3 Calendar

    docs = (await client.get(f"/api/projects/{pid}/google/documents")).json()
    assert len(docs) == 7
    assert {d["source"] for d in docs} == {"drive", "calendar"}
