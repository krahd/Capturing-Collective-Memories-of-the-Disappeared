from fastapi.testclient import TestClient

import app as app_module
from state import SessionStore


def test_two_view_api_flow(tmp_path, monkeypatch):
    app_module.store = SessionStore(tmp_path)

    async def fake_chat(turns):
        assert turns[-1]["text"] == "No me acuerdo bien, creo que era por el 78."
        return "¿Qué es lo que te hace ubicarlo más o menos por esa época?"

    monkeypatch.setattr(app_module.llm, "chat", fake_chat)
    monkeypatch.setattr(type(app_module.llm), "configured", property(lambda self: True))
    monkeypatch.setattr(app_module.llm, "model", "test-model")

    client = TestClient(app_module.app)
    created = client.post("/api/sessions", json={}).json()
    session_id = created["id"]
    assert created["turns"][0]["text"].startswith("Podés empezar")

    reply = client.post(
        f"/api/sessions/{session_id}/turns",
        json={"text": "No me acuerdo bien, creo que era por el 78."},
    )
    assert reply.status_code == 200
    session = reply.json()["session"]
    user_turn = [t for t in session["turns"] if t["role"] == "user"][0]
    assert session["turns"][-1]["text"] == "¿Qué es lo que te hace ubicarlo más o menos por esa época?"

    annotation = client.post(
        f"/api/sessions/{session_id}/annotations",
        json={"source_turn_ids": [user_turn["id"]], "label": "uncertain", "note": "Fecha aproximada"},
    )
    assert annotation.status_code == 200

    derived = client.post(
        f"/api/sessions/{session_id}/derived",
        json={"source_turn_ids": [user_turn["id"]], "kind": "time", "text": "Alrededor de 1978, según recuerdo incierto"},
    )
    assert derived.status_code == 200
    derived_id = derived.json()["id"]

    md = client.get(f"/api/sessions/{session_id}/export.md")
    assert md.status_code == 200
    assert user_turn["id"] in md.text
    assert "No me acuerdo bien, creo que era por el 78." in md.text

    deleted = client.delete(f"/api/sessions/{session_id}/derived/{derived_id}")
    assert deleted.status_code == 200
    after = client.get(f"/api/sessions/{session_id}").json()
    assert after["derived_items"] == []
    assert any(t["id"] == user_turn["id"] and t["text"] == "No me acuerdo bien, creo que era por el 78." for t in after["turns"])
