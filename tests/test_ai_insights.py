import httpx

import app.services.ai_service as ai
from tests.conftest import auth, register


async def _interaction(client, token):
    cid = (await client.post("/api/v1/customers", headers=auth(token), json={"name": "Acme"})).json()["id"]
    return (await client.post(
        "/api/v1/interactions", headers=auth(token),
        json={"customer_id": cid, "type": "meeting", "title": "x", "notes": "notes here",
              "meeting_date": "2026-06-01T10:00:00Z"},
    )).json()["id"]


async def test_regenerate_with_mocked_llm_success(client, monkeypatch):
    token, _ = await register(client, "c@x.com", role="csm")
    iid = await _interaction(client, token)

    async def fake_ok(notes):
        return {"choices": [{"message": {"content":
            '{"summary":"Great QBR.","sentiment":"positive","action_items":["Send recap"],"risks":["Budget review"]}'}}]}

    monkeypatch.setattr(ai.settings, "ai_api_key", "sk-test")
    monkeypatch.setattr(ai, "_call_llm", fake_ok)

    r = await client.post(f"/api/v1/interactions/{iid}/insights", headers=auth(token))
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "success"
    assert body["summary"] == "Great QBR."
    assert body["action_items"] == ["Send recap"]
    assert body["risks"] == ["Budget review"]


async def test_regenerate_falls_back_on_llm_failure(client, monkeypatch):
    token, _ = await register(client, "c@x.com", role="csm")
    iid = await _interaction(client, token)

    async def fake_fail(notes):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(ai.settings, "ai_api_key", "sk-test")
    monkeypatch.setattr(ai, "_call_llm", fake_fail)

    r = await client.post(f"/api/v1/interactions/{iid}/insights", headers=auth(token))
    assert r.status_code == 201
    assert r.json()["status"] == "fallback"  # app stays functional


async def test_regenerate_falls_back_on_malformed_json(client, monkeypatch):
    token, _ = await register(client, "c@x.com", role="csm")
    iid = await _interaction(client, token)

    async def fake_bad(notes):
        return {"choices": [{"message": {"content": "not json at all"}}]}

    monkeypatch.setattr(ai.settings, "ai_api_key", "sk-test")
    monkeypatch.setattr(ai, "_call_llm", fake_bad)

    r = await client.post(f"/api/v1/interactions/{iid}/insights", headers=auth(token))
    assert r.status_code == 201
    assert r.json()["status"] == "fallback"
