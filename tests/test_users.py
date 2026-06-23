from tests.conftest import auth, register


async def test_admin_can_list_users(client):
    admin, _ = await register(client, "admin@x.com", role="admin")
    await register(client, "csm@x.com", role="csm")
    r = await client.get("/api/v1/users", headers=auth(admin))
    assert r.status_code == 200
    assert r.json()["total"] == 2


async def test_non_admin_cannot_list_users(client):
    csm, _ = await register(client, "csm@x.com", role="csm")
    r = await client.get("/api/v1/users", headers=auth(csm))
    assert r.status_code == 403


async def test_admin_can_change_a_users_role(client):
    admin, _ = await register(client, "admin@x.com", role="admin")
    _, csm_id = await register(client, "csm@x.com", role="csm")
    r = await client.patch(f"/api/v1/users/{csm_id}", headers=auth(admin), json={"role": "manager"})
    assert r.status_code == 200 and r.json()["role"] == "manager"


async def test_admin_cannot_demote_self(client):
    admin, admin_id = await register(client, "admin@x.com", role="admin")
    r = await client.patch(f"/api/v1/users/{admin_id}", headers=auth(admin), json={"role": "csm"})
    assert r.status_code == 400


async def test_non_admin_cannot_update_users(client):
    csm, _ = await register(client, "csm@x.com", role="csm")
    _, other = await register(client, "other@x.com", role="csm")
    r = await client.patch(f"/api/v1/users/{other}", headers=auth(csm), json={"role": "admin"})
    assert r.status_code == 403
