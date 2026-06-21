from tests.factories import create_area, create_user, login


async def test_economics_roi_computation(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    pid = (await client.post("/api/projects", json={"name": "P", "area_id": area.id})).json()["id"]

    updated = (
        await client.patch(
            f"/api/projects/{pid}/economics",
            json={
                "estimated_cost": 100,
                "actual_cost": 80,
                "expected_benefit": 200,
                "actual_benefit": 150,
                "currency": "usd",
            },
        )
    ).json()
    assert updated["currency"] == "USD"
    assert updated["net_actual"] == 70
    assert updated["roi_actual_pct"] == 87.5
    assert updated["cost_consumption_pct"] == 80.0
    assert updated["benefit_realization_pct"] == 75.0
    assert updated["has_data"] is True

    fetched = (await client.get(f"/api/projects/{pid}/economics")).json()
    assert fetched["roi_expected_pct"] == 100.0  # (200-100)/100


async def test_economics_empty_by_default(client, session):
    area = await create_area(session, "IT", "it")
    admin = await create_user(session, "admin@invesa.com", "Admin", role="admin")
    await login(client, admin.id)
    pid = (await client.post("/api/projects", json={"name": "P", "area_id": area.id})).json()["id"]
    economics = (await client.get(f"/api/projects/{pid}/economics")).json()
    assert economics["has_data"] is False
    assert economics["roi_actual_pct"] is None
    assert economics["currency"] == "COP"
