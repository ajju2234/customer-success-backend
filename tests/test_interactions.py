from tests.conftest import auth, register


async def _customer(client, token, name="Acme"):
    return (await client.post("/api/v1/customers", headers=auth(token), json={"name": name})).json()["id"]


async def test_create_interaction_generates_insight_via_fallback(client):
    csm, _ = await register(client, "c@x.com", role="csm")
    cid = await _customer(client, csm)
    r = await client.post(
        "/api/v1/interactions",
        headers=auth(csm),
        json={
            "customer_id": cid, "type": "meeting", "title": "Kickoff",
            "notes": "Client very happy, excited to renew.",
            "meeting_date": "2026-06-01T10:00:00Z",
        },
    )
    assert r.status_code == 201
    insight = r.json()["insight"]
    assert insight is not None
    assert insight["sentiment"] == "positive"   # heuristic fallback
    assert insight["status"] == "fallback"


async def test_interaction_ownership_403(client):
    csm1, _ = await register(client, "c1@x.com", role="csm")
    csm2, _ = await register(client, "c2@x.com", role="csm")
    cid = await _customer(client, csm1)
    iid = (await client.post(
        "/api/v1/interactions", headers=auth(csm1),
        json={"customer_id": cid, "type": "call", "title": "x", "meeting_date": "2026-06-01T10:00:00Z"},
    )).json()["id"]
    assert (await client.get(f"/api/v1/interactions/{iid}", headers=auth(csm2))).status_code == 403


async def test_interaction_filters(client):
    csm, _ = await register(client, "c@x.com", role="csm")
    cid = await _customer(client, csm)
    for t in ("meeting", "call"):
        await client.post(
            "/api/v1/interactions", headers=auth(csm),
            json={"customer_id": cid, "type": t, "title": t, "meeting_date": "2026-06-01T10:00:00Z"},
        )
    assert (await client.get(f"/api/v1/interactions?type=call", headers=auth(csm))).json()["total"] == 1
