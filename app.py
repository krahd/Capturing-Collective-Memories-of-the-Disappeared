from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from model import LLMClient, opening_message
from state import (
    ACTOR_MODEL,
    ACTOR_SYSTEM,
    ORIGIN_MODEL,
    SessionStore,
    export_markdown,
    load_recorded_session,
    new_id,
)

ROOT = Path(__file__).resolve().parent
store = SessionStore(ROOT / "data" / "sessions")
llm = LLMClient()
app = FastAPI(title="Collective Memories Prototype", version="0.1.0")
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


class WithdrawRequest(BaseModel):
    reason: str = ""


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/config")
def config() -> dict[str, Any]:
    return {
        "llm_configured": llm.configured,
        "model": llm.model if llm.configured else None,
        "provenance": llm.provenance() if llm.configured else None,
    }


@app.get("/api/sessions")
def sessions() -> list[dict[str, Any]]:
    return [s.to_dict() for s in store.list()]


@app.post("/api/sessions")
def create_session(body: SessionCreate) -> dict[str, Any]:
    session = store.create(body.title)
    # The opening line is scripted, not generated. The record says so.
    session.add_turn("assistant", opening_message(), actor=ACTOR_SYSTEM)
    store.save(session)
    return session.to_dict()


@app.post("/api/sessions/demo")
def create_demo_session() -> dict[str, Any]:
    """Load the researcher-authored example transcript. Never a live conversation."""
    try:
        session = load_recorded_session(ROOT / "demo" / "sesion-ejemplo.json")
    except FileNotFoundError as exc:
        raise HTTPException(404, "No hay sesión de ejemplo disponible") from exc
    return store.adopt(session).to_dict()


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
    if session.is_recorded:
        raise HTTPException(409, "Esta es una transcripción grabada; no admite turnos nuevos")
    user_turn = session.add_turn("user", body.text)
    store.save(session)

    try:
        assistant_text = await llm.chat([{"role": t.role, "text": t.text} for t in session.turns])
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

    assistant_turn = session.add_turn("assistant", assistant_text, actor=ACTOR_MODEL)
    store.save(session)
    return {"user_turn": user_turn.__dict__, "assistant_turn": assistant_turn.__dict__, "session": session.to_dict()}


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
        item = session.add_derived_item(body.kind, body.text, body.source_turn_ids, body.note)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    store.save(session)
    return item.__dict__


@app.patch("/api/sessions/{session_id}/derived/{item_id}")
def update_derived(session_id: str, item_id: str, body: DerivedUpdate) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    try:
        item = session.update_derived_item(item_id, **body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    store.save(session)
    return item.__dict__


@app.post("/api/sessions/{session_id}/derived/{item_id}/withdraw")
def withdraw_derived(session_id: str, item_id: str, body: WithdrawRequest) -> dict[str, Any]:
    """Retire an interpretation while keeping it, and its reason, on the record."""
    session = get_session_or_404(session_id)
    try:
        item = session.withdraw_derived_item(item_id, body.reason)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    store.save(session)
    return item.__dict__


@app.get("/api/sessions/{session_id}/audit")
def audit(session_id: str) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    return {
        "summary": session.summary(),
        "events": [event.__dict__ for event in session.events],
    }


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
        rel = session.add_relation(body.relation_type, body.source_id, body.target_id, body.note)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    store.save(session)
    return rel.__dict__


@app.post("/api/sessions/{session_id}/extract")
async def extract(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    source_turn_ids = payload.get("source_turn_ids") or [t.id for t in session.turns if t.role == "user"]
    known = {t.id: t for t in session.turns}
    try:
        turns = [known[x] for x in source_turn_ids]
    except KeyError as exc:
        raise HTTPException(400, f"Turno fuente desconocido: {exc.args[0]}") from exc
    try:
        extracted = await llm.extract([t.__dict__ for t in turns])
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc

    # Every item from this run carries the same model identity and settings, so
    # a model-produced interpretation can never be mistaken for a human one.
    provenance = {**llm.provenance(for_extraction=True), "run_id": new_id("run")}
    created = []
    for raw in extracted:
        refs = [x for x in raw.get("source_turn_ids", []) if x in known]
        if not refs or not raw.get("text"):
            continue
        try:
            item = session.add_derived_item(
                raw.get("kind", "other"),
                raw["text"],
                refs,
                origin=ORIGIN_MODEL,
                origin_detail=provenance,
            )
            created.append(item.__dict__)
        except ValueError:
            continue
    session.record(
        ACTOR_MODEL,
        "extraccion_ejecutada",
        f"Extracción automática sobre {len(turns)} turno(s): {len(created)} interpretación(es) provisional(es)",
        detail={**provenance, "source_turn_ids": source_turn_ids},
    )
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
