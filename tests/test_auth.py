from tests.conftest import auth, register


async def test_register_login_me_flow(client):
    token, user_id = await register(client, "admin@x.com", role="admin")

    # duplicate email -> 409
    r = await client.post(
        "/api/v1/auth/register",
        json={"name": "dup", "email": "admin@x.com", "password": "password123"},
    )
    assert r.status_code == 409

    # /me with token
    r = await client.get("/api/v1/auth/me", headers=auth(token))
    assert r.status_code == 200 and r.json()["email"] == "admin@x.com"


async def test_me_requires_token(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_login_wrong_password(client):
    await register(client, "u@x.com")
    r = await client.post("/api/v1/auth/login", json={"email": "u@x.com", "password": "nope"})
    assert r.status_code == 401


async def test_refresh_rotates_token(client):
    await register(client, "u@x.com")
    await client.post("/api/v1/auth/login", json={"email": "u@x.com", "password": "password123"})
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 200 and r.json()["access_token"]


async def test_invalid_password_too_short(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"name": "x", "email": "short@x.com", "password": "123"},
    )
    assert r.status_code == 422  # validation


async def test_forgot_then_reset_password(client):
    await register(client, "u@x.com", password="password123")

    # request a reset → demo returns the token
    r = await client.post("/api/v1/auth/forgot-password", json={"email": "u@x.com"})
    assert r.status_code == 200
    token = r.json()["reset_token"]
    assert token

    # old password should no longer work after reset; new one should
    r = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "newpass456"}
    )
    assert r.status_code == 204

    assert (await client.post("/api/v1/auth/login", json={"email": "u@x.com", "password": "password123"})).status_code == 401
    assert (await client.post("/api/v1/auth/login", json={"email": "u@x.com", "password": "newpass456"})).status_code == 200


async def test_forgot_password_unknown_email_is_generic(client):
    r = await client.post("/api/v1/auth/forgot-password", json={"email": "nobody@x.com"})
    assert r.status_code == 200 and r.json()["reset_token"] is None


async def test_reset_with_bad_token_fails(client):
    r = await client.post(
        "/api/v1/auth/reset-password", json={"token": "not-a-token", "new_password": "whatever12"}
    )
    assert r.status_code == 400
