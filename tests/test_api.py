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
            user_turn = [turn for turn in session["turns"] if turn["role"] == "user"][0]
            assert session["turns"][-1]["text"] == (
                "¿Qué es lo que te hace ubicarlo más o menos por esa época?"
            )

            annotation = await client.post(
                f"/api/sessions/{session_id}/annotations",
                json={
                    "source_turn_ids": [user_turn["id"]],
                    "label": "uncertain",
                    "note": "Fecha aproximada",
                },
            )
            assert annotation.status_code == 200

            derived = await client.post(
                f"/api/sessions/{session_id}/derived",
                json={
                    "source_turn_ids": [user_turn["id"]],
                    "kind": "time",
                    "text": "Alrededor de 1978, según recuerdo incierto",
                },
            )
            assert derived.status_code == 200
            derived_id = derived.json()["id"]

            md = await client.get(f"/api/sessions/{session_id}/export.md")
            assert md.status_code == 200
            assert user_turn["id"] in md.text
            assert "No me acuerdo bien, creo que era por el 78." in md.text

            deleted = await client.delete(
                f"/api/sessions/{session_id}/derived/{derived_id}"
            )
            assert deleted.status_code == 200
            after = (await client.get(f"/api/sessions/{session_id}")).json()
            assert after["derived_items"] == []
            assert any(
                turn["id"] == user_turn["id"]
                and turn["text"] == "No me acuerdo bien, creo que era por el 78."
                for turn in after["turns"]
            )

    asyncio.run(run_flow())


def test_config_reports_local_model_and_speech_readiness(monkeypatch):
    async def fake_llm_status():
        return {
            "configured": True,
            "ready": True,
            "profile": "mac-performance",
            "provider": "basert",
            "model": "gemma-4-12B",
        }

    async def fake_speech_health():
        return {"ready": True, "endpoint": "http://127.0.0.1:8001/v1"}

    monkeypatch.setattr(app_module.llm, "status", fake_llm_status)
    monkeypatch.setattr(app_module.speech, "health", fake_speech_health)

    async def run():
        transport = httpx.ASGITransport(app=app_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/config")
            assert response.status_code == 200
            data = response.json()
            assert data["llm_configured"] is True
            assert data["llm"]["provider"] == "basert"
            assert data["audio_ready"] is True
            assert data["audio"]["stt_model"] == app_module.speech.config.stt_model

    asyncio.run(run())


def test_audio_endpoints_keep_transcription_provisional(monkeypatch):
    async def fake_transcribe(audio, **kwargs):
        assert audio == b"voice"
        return "Capaz que fue en el 78."

    async def fake_synthesise(text):
        assert text == "Seguí, te escucho."
        return b"RIFF-test", "audio/wav"

    monkeypatch.setattr(app_module.speech, "transcribe", fake_transcribe)
    monkeypatch.setattr(app_module.speech, "synthesise", fake_synthesise)

    async def run():
        transport = httpx.ASGITransport(app=app_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            transcription = await client.post(
                "/api/audio/transcribe",
                files={"file": ("speech.webm", b"voice", "audio/webm")},
            )
            assert transcription.status_code == 200
            assert transcription.json()["text"] == "Capaz que fue en el 78."
            assert transcription.json()["provisional"] is True

            speech = await client.post(
                "/api/audio/speech",
                json={"text": "Seguí, te escucho."},
            )
            assert speech.status_code == 200
            assert speech.content == b"RIFF-test"
            assert speech.headers["content-type"].startswith("audio/wav")

    asyncio.run(run())
