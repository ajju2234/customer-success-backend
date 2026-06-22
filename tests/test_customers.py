import uuid

from tests.conftest import auth, register


async def test_csm_ownership_scoping(client):
    csm1, csm1_id = await register(client, "c1@x.com", role="csm")
    csm2, _ = await register(client, "c2@x.com", role="csm")

    r = await client.post("/api/v1/customers", headers=auth(csm1), json={"name": "Acme", "status": "active"})
    assert r.status_code == 201 and r.json()["owner_id"] == csm1_id
    cid = r.json()["id"]

    # csm1 sees it, csm2 does not
    assert (await client.get("/api/v1/customers", headers=auth(csm1))).json()["total"] == 1
    assert (await client.get("/api/v1/customers", headers=auth(csm2))).json()["total"] == 0

    # csm2 cannot access csm1's customer -> 403
    assert (await client.get(f"/api/v1/customers/{cid}", headers=auth(csm2))).status_code == 403
    assert (await client.delete(f"/api/v1/customers/{cid}", headers=auth(csm2))).status_code == 403


async def test_admin_sees_all(client):
    admin, _ = await register(client, "a@x.com", role="admin")
    csm, _ = await register(client, "c@x.com", role="csm")
    await client.post("/api/v1/customers", headers=auth(csm), json={"name": "Acme"})
    assert (await client.get("/api/v1/customers", headers=auth(admin))).json()["total"] == 1


async def test_filters_and_pagination(client):
    csm, _ = await register(client, "c@x.com", role="csm")
    await client.post("/api/v1/customers", headers=auth(csm), json={"name": "Acme", "status": "active"})
    await client.post("/api/v1/customers", headers=auth(csm), json={"name": "Globex", "status": "at_risk"})

    assert (await client.get("/api/v1/customers?status=active", headers=auth(csm))).json()["total"] == 1
    assert (await client.get("/api/v1/customers?q=glob", headers=auth(csm))).json()["total"] == 1
    page = (await client.get("/api/v1/customers?page=1&limit=1", headers=auth(csm))).json()
    assert page["total"] == 2 and len(page["items"]) == 1


async def test_update_and_404(client):
    csm, _ = await register(client, "c@x.com", role="csm")
    cid = (await client.post("/api/v1/customers", headers=auth(csm), json={"name": "Acme"})).json()["id"]
    r = await client.patch(f"/api/v1/customers/{cid}", headers=auth(csm), json={"status": "churned"})
    assert r.status_code == 200 and r.json()["status"] == "churned"
    assert (await client.get(f"/api/v1/customers/{uuid.uuid4()}", headers=auth(csm))).status_code == 404
