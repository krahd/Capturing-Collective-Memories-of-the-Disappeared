from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from audio import SpeechService
from local_model import LLMClient
from model import opening_message
from state import SessionStore, export_markdown

ROOT = Path(__file__).resolve().parent
store = SessionStore(ROOT / "data" / "sessions")
llm = LLMClient()
speech = SpeechService()
app = FastAPI(title="Collective Memories Prototype", version="0.2.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


class SessionCreate(BaseModel):
    title: str | None = None


class TurnCreate(BaseModel):
    text: str = Field(min_length=1)


class AnnotationCreate(BaseModel):
    source_turn_ids: list[str]
    label: str = Field(min_length=1)
    note: str = ""


class DerivedCreate(BaseModel):
    kind: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_turn_ids: list[str]
    note: str = ""


class DerivedUpdate(BaseModel):
    kind: str | None = None
    text: str | None = None
    status: str | None = None
    note: str | None = None
    source_turn_ids: list[str] | None = None


class RelationCreate(BaseModel):
    relation_type: str = Field(min_length=1)
    source_id: str
    target_id: str
    note: str = ""


class SpeechCreate(BaseModel):
    text: str = Field(min_length=1)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/config")
async def config() -> dict[str, Any]:
    llm_status = await llm.status()
    audio_status = await speech.health()
    return {
        "llm_configured": bool(llm_status.get("ready")),
        "llm": llm_status,
        "model": llm_status.get("model"),
        "audio_configured": speech.configured,
        "audio_ready": bool(audio_status.get("ready")),
        "audio": {
            **audio_status,
            "stt_model": speech.config.stt_model,
            "tts_model": speech.config.tts_model,
            "tts_voice": speech.config.tts_voice,
        },
    }


@app.post("/api/audio/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> dict[str, Any]:
    audio = await file.read()
    if len(audio) > 25 * 1024 * 1024:
        raise HTTPException(413, "El fragmento de audio es demasiado grande")
    try:
        text = await speech.transcribe(
            audio,
            filename=file.filename or "speech.webm",
            content_type=file.content_type or "application/octet-stream",
        )
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc
    return {
        "text": text,
        "model": speech.config.stt_model,
        "provisional": True,
    }


@app.post("/api/audio/speech")
async def synthesise_speech(body: SpeechCreate) -> Response:
    try:
        audio, content_type = await speech.synthesise(body.text)
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(
        content=audio,
        media_type=content_type,
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/sessions")
def sessions() -> list[dict[str, Any]]:
    return [s.to_dict() for s in store.list()]


@app.post("/api/sessions")
def create_session(body: SessionCreate) -> dict[str, Any]:
    session = store.create(body.title)
    session.add_turn("assistant", opening_message())
    store.save(session)
    return session.to_dict()


def get_session_or_404(session_id: str):
    try:
        return store.get(session_id)
    except KeyError as exc:
        raise HTTPException(404, "Sesión no encontrada") from exc


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    return get_session_or_404(session_id).to_dict()


@app.post("/api/sessions/{session_id}/turns")
async def add_turn(session_id: str, body: TurnCreate) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    user_turn = session.add_turn("user", body.text)
    store.save(session)

    try:
        assistant_text = await llm.chat(
            [{"role": turn.role, "text": turn.text} for turn in session.turns]
        )
    except Exception as exc:
        # Preserve the participant turn even if generation fails.
        return JSONResponse(
            status_code=503,
            content={
                "error": str(exc),
                "user_turn": user_turn.__dict__,
                "session": session.to_dict(),
            },
        )

    assistant_turn = session.add_turn("assistant", assistant_text)
    store.save(session)
    return {
        "user_turn": user_turn.__dict__,
        "assistant_turn": assistant_turn.__dict__,
        "session": session.to_dict(),
    }


@app.post("/api/sessions/{session_id}/annotations")
def add_annotation(session_id: str, body: AnnotationCreate) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    try:
        item = session.add_annotation(body.source_turn_ids, body.label, body.note)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    store.save(session)
    return item.__dict__


@app.post("/api/sessions/{session_id}/derived")
def add_derived(session_id: str, body: DerivedCreate) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    try:
        item = session.add_derived_item(
            body.kind, body.text, body.source_turn_ids, body.note
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    store.save(session)
    return item.__dict__


@app.patch("/api/sessions/{session_id}/derived/{item_id}")
def update_derived(
    session_id: str, item_id: str, body: DerivedUpdate
) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    try:
        item = session.update_derived_item(
            item_id, **body.model_dump(exclude_none=True)
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    store.save(session)
    return item.__dict__


@app.delete("/api/sessions/{session_id}/derived/{item_id}")
def delete_derived(session_id: str, item_id: str) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    try:
        item = session.delete_derived_item(item_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    store.save(session)
    return {"deleted": item.id}


@app.post("/api/sessions/{session_id}/relations")
def add_relation(session_id: str, body: RelationCreate) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    try:
        rel = session.add_relation(
            body.relation_type, body.source_id, body.target_id, body.note
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    store.save(session)
    return rel.__dict__


@app.post("/api/sessions/{session_id}/extract")
async def extract(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    source_turn_ids = payload.get("source_turn_ids") or [
        turn.id for turn in session.turns if turn.role == "user"
    ]
    known = {turn.id: turn for turn in session.turns}
    try:
        turns = [known[turn_id] for turn_id in source_turn_ids]
    except KeyError as exc:
        raise HTTPException(400, f"Turno fuente desconocido: {exc.args[0]}") from exc
    try:
        extracted = await llm.extract([turn.__dict__ for turn in turns])
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc

    created = []
    for raw in extracted:
        refs = [turn_id for turn_id in raw.get("source_turn_ids", []) if turn_id in known]
        if not refs or not raw.get("text"):
            continue
        try:
            item = session.add_derived_item(
                raw.get("kind", "other"), raw["text"], refs
            )
            created.append(item.__dict__)
        except ValueError:
            continue
    store.save(session)
    return {"items": created}


@app.get("/api/sessions/{session_id}/export.json")
def export_json(session_id: str) -> JSONResponse:
    session = get_session_or_404(session_id)
    return JSONResponse(
        content=session.to_dict(),
        headers={"Content-Disposition": f'attachment; filename="{session.id}.json"'},
    )


@app.get("/api/sessions/{session_id}/export.md")
def export_md(session_id: str) -> PlainTextResponse:
    session = get_session_or_404(session_id)
    return PlainTextResponse(
        export_markdown(session),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{session.id}.md"'},
    )
