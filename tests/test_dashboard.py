from tests.conftest import auth, register


async def test_dashboard_metrics_correctness(client):
    token, _ = await register(client, "a@x.com", role="admin")
    for name, st in [("A", "active"), ("B", "at_risk"), ("C", "active"), ("D", "churned")]:
        await client.post("/api/v1/customers", headers=auth(token), json={"name": name, "status": st})
    cid = (await client.get("/api/v1/customers", headers=auth(token))).json()["items"][0]["id"]
    await client.post("/api/v1/interactions", headers=auth(token), json={
        "customer_id": cid, "type": "meeting", "title": "g", "notes": "very happy renew",
        "meeting_date": "2026-06-20T10:00:00Z"})
    await client.post("/api/v1/interactions", headers=auth(token), json={
        "customer_id": cid, "type": "call", "title": "b", "notes": "frustrated bug cancel",
        "meeting_date": "2026-06-21T10:00:00Z"})

    m = (await client.get("/api/v1/dashboard/metrics", headers=auth(token))).json()
    assert m["total_customers"] == 4
    assert m["customers_by_status"]["active"] == 2
    assert m["at_risk_count"] == 1
    assert m["total_interactions"] == 2
    assert m["sentiment_breakdown"]["positive"] == 1
    assert m["sentiment_breakdown"]["negative"] == 1


async def test_dashboard_cache_hit_then_invalidation(client, fake_redis):
    token, _ = await register(client, "a@x.com", role="admin")
    await client.post("/api/v1/customers", headers=auth(token), json={"name": "A", "status": "active"})

    # MISS on first call
    first = (await client.get("/api/v1/dashboard/metrics", headers=auth(token))).json()
    assert first["cached"] is False

    # HIT on second call
    second = (await client.get("/api/v1/dashboard/metrics", headers=auth(token))).json()
    assert second["cached"] is True

    # a write invalidates the cache -> MISS again, with fresh data
    await client.post("/api/v1/customers", headers=auth(token), json={"name": "B", "status": "active"})
    third = (await client.get("/api/v1/dashboard/metrics", headers=auth(token))).json()
    assert third["cached"] is False
    assert third["total_customers"] == 2


async def test_csm_dashboard_is_scoped(client):
    csm1, _ = await register(client, "c1@x.com", role="csm")
    csm2, _ = await register(client, "c2@x.com", role="csm")
    await client.post("/api/v1/customers", headers=auth(csm1), json={"name": "A"})
    await client.post("/api/v1/customers", headers=auth(csm2), json={"name": "B"})
    m1 = (await client.get("/api/v1/dashboard/metrics", headers=auth(csm1))).json()
    assert m1["total_customers"] == 1 and m1["scope"].startswith("user:")
