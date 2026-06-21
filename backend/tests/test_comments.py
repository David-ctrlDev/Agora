from tests.factories import add_membership, create_area, create_user, login


async def _project_and_task(client, area_id: int) -> int:
    pid = (await client.post("/api/projects", json={"name": "P", "area_id": area_id})).json()["id"]
    return (await client.post(f"/api/projects/{pid}/tasks", json={"title": "T"})).json()["id"]


async def test_comments_flow(client, session):
    prod = await create_area(session, "Producción", "produccion")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    task_id = await _project_and_task(client, prod.id)

    assert (await client.get(f"/api/tasks/{task_id}/comments")).json() == []

    created = await client.post(f"/api/tasks/{task_id}/comments", json={"body": "Hola"})
    assert created.status_code == 201
    assert created.json()["author_name"] == "Admin"

    comments = (await client.get(f"/api/tasks/{task_id}/comments")).json()
    assert len(comments) == 1
    assert comments[0]["body"] == "Hola"


async def test_outsider_cannot_comment(client, session):
    prod = await create_area(session, "Producción", "produccion")
    it = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    bob = await create_user(session, "bob@invesa.com", "Bob", role="member")
    await add_membership(session, bob.id, it.id)

    await login(client, admin.id)
    task_id = await _project_and_task(client, prod.id)

    await login(client, bob.id)
    assert (await client.get(f"/api/tasks/{task_id}/comments")).status_code == 404
    assert (
        await client.post(f"/api/tasks/{task_id}/comments", json={"body": "x"})
    ).status_code == 404
