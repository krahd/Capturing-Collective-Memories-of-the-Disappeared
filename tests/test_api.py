import asyncio

import httpx

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

    async def run_flow():
        transport = httpx.ASGITransport(app=app_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = (await client.post("/api/sessions", json={})).json()
            session_id = created["id"]
            assert created["turns"][0]["text"].startswith("Podés empezar")

            reply = await client.post(
                f"/api/sessions/{session_id}/turns",
                json={"text": "No me acuerdo bien, creo que era por el 78."},
            )
            assert reply.status_code == 200
            session = reply.json()["session"]
            user_turn = [t for t in session["turns"] if t["role"] == "user"][0]
            assert session["turns"][-1]["text"] == "¿Qué es lo que te hace ubicarlo más o menos por esa época?"

            annotation = await client.post(
                f"/api/sessions/{session_id}/annotations",
                json={"source_turn_ids": [user_turn["id"]], "label": "uncertain", "note": "Fecha aproximada"},
            )
            assert annotation.status_code == 200

            derived = await client.post(
                f"/api/sessions/{session_id}/derived",
                json={"source_turn_ids": [user_turn["id"]], "kind": "time", "text": "Alrededor de 1978, según recuerdo incierto"},
            )
            assert derived.status_code == 200
            derived_id = derived.json()["id"]

            md = await client.get(f"/api/sessions/{session_id}/export.md")
            assert md.status_code == 200
            assert user_turn["id"] in md.text
            assert "No me acuerdo bien, creo que era por el 78." in md.text

            deleted = await client.delete(f"/api/sessions/{session_id}/derived/{derived_id}")
            assert deleted.status_code == 200
            after = (await client.get(f"/api/sessions/{session_id}")).json()
            assert after["derived_items"] == []
            assert any(
                t["id"] == user_turn["id"] and t["text"] == "No me acuerdo bien, creo que era por el 78."
                for t in after["turns"]
            )

    asyncio.run(run_flow())


def test_withdraw_and_audit_endpoints(tmp_path, monkeypatch):
    app_module.store = SessionStore(tmp_path)

    async def run_flow():
        transport = httpx.ASGITransport(app=app_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            session_id = (await client.post("/api/sessions", json={})).json()["id"]
            session = (await client.get(f"/api/sessions/{session_id}")).json()
            turn_id = session["turns"][0]["id"]

            item = (
                await client.post(
                    f"/api/sessions/{session_id}/derived",
                    json={"source_turn_ids": [turn_id], "kind": "event", "text": "Una inferencia de más"},
                )
            ).json()

            withdrawn = await client.post(
                f"/api/sessions/{session_id}/derived/{item['id']}/withdraw",
                json={"reason": "La persona no dijo esto."},
            )
            assert withdrawn.status_code == 200
            assert withdrawn.json()["withdrawn"] is True
            # Retained, not deleted.
            assert withdrawn.json()["text"] == "Una inferencia de más"

            audit = (await client.get(f"/api/sessions/{session_id}/audit")).json()
            assert audit["summary"]["retiradas"] == 1
            assert audit["summary"]["interpretaciones"] == 0
            actions = [e["action"] for e in audit["events"]]
            assert "interpretacion_retirada" in actions
            assert "sesion_creada" in actions

    asyncio.run(run_flow())


def test_recorded_example_session_loads_and_refuses_new_turns(tmp_path):
    app_module.store = SessionStore(tmp_path)

    async def run_flow():
        transport = httpx.ASGITransport(app=app_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post("/api/sessions/demo")
            assert created.status_code == 200
            session = created.json()
            assert session["is_recorded"] is True
            assert len(session["turns"]) > 1
            # Both origins are present, which is the point of the example.
            origins = {i["origin"] for i in session["derived_items"]}
            assert origins == {"investigador", "modelo"}
            assert any(i["withdrawn"] for i in session["derived_items"])

            blocked = await client.post(
                f"/api/sessions/{session['id']}/turns", json={"text": "Hola"}
            )
            assert blocked.status_code == 409

    asyncio.run(run_flow())
