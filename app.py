from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from controller import (
    CORRECTION,
    FIXED_PROTOCOL_RESPONSES,
    FIXED_REDIRECT,
    OFF_TOPIC,
    deterministic_intent,
    guard_interview_move,
    protocol_status,
    record_kind_for_intent,
    safe_interview_fallback,
)
from memory_field import build_memory_field, build_timeline
from model import LLMClient, opening_message
from state import (
    ACTOR_MODEL,
    ACTOR_SYSTEM,
    ORIGIN_MODEL,
    SessionStore,
    export_markdown,
    load_recorded_session,
    new_id,
    safe_filename,
)
from voice import VoiceService, audio_suffix

ROOT = Path(__file__).resolve().parent
store = SessionStore(ROOT / "data" / "sessions")
llm = LLMClient()
voice = VoiceService()
app = FastAPI(title="Collective Memories Prototype", version="0.1.0")


class RevalidatedStatics(StaticFiles):
    """Serve static files that must always be revalidated.

    The markup, script and stylesheet change together. A browser holding a
    cached script against fresh markup throws on the first missing element and
    the page silently stops initialising, which is a miserable thing to discover
    during a demo. `no-cache` still allows a 304 via ETag, so this costs a
    conditional request rather than a re-download.
    """

    def file_response(self, *args: Any, **kwargs: Any) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


app.mount("/static", RevalidatedStatics(directory=ROOT / "static"), name="static")


class SessionCreate(BaseModel):
    title: str | None = None


class TurnCreate(BaseModel):
    text: str = Field(min_length=1)
    audio_id: str = ""


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


class SpeechCreate(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/config")
def config() -> dict[str, Any]:
    return {
        "llm_configured": llm.configured,
        "model": llm.model if llm.configured else None,
        "provenance": llm.provenance() if llm.configured else None,
        # Named separately because it may be a different, smaller model, and an
        # interpretation must never be read as the conversational model's.
        "extraction_provenance": llm.provenance(for_extraction=True) if llm.configured else None,
        "voice": voice.config(),
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
async def add_turn(session_id: str, body: TurnCreate, background: BackgroundTasks) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    if session.is_recorded:
        raise HTTPException(409, "Esta es una transcripción grabada; no admite turnos nuevos")
    if session.status != "active":
        raise HTTPException(409, f"La sesión está {session.status}; reanudala o iniciá otra")

    audio_record = next((record for record in session.audio_records if record.id == body.audio_id), None)
    if body.audio_id and audio_record is None:
        raise HTTPException(400, "El audio no pertenece a esta sesión")
    transcription_detail = {}
    if audio_record:
        transcription_detail = {
            **audio_record.asr_detail,
            "original_transcript": audio_record.transcript,
            "participant_edited": body.text != audio_record.transcript,
        }
    user_turn = session.add_turn(
        "user",
        body.text,
        input_mode="voice_asr" if audio_record else "text",
        audio_id=body.audio_id,
        transcription_detail=transcription_detail,
    )
    store.save(session)

    try:
        history = _interview_history(session)
        intent = deterministic_intent(body.text) or await llm.classify(history)
    except Exception as exc:
        # Preserve the participant turn even if classification fails.
        session.classify_turn(user_turn.id, "UNCLASSIFIED", "non_testimony/control")
        store.save(session)
        return JSONResponse(
            status_code=503,
            content={
                "error": str(exc),
                "user_turn": user_turn.__dict__,
                "session": session.to_dict(),
            },
        )

    session.classify_turn(user_turn.id, intent, record_kind_for_intent(intent))

    # The memory field grows on its own. Nobody selects turns or presses extract:
    # the structure is a by-product of speaking, not a curation task.
    if record_kind_for_intent(intent) == "testimony":
        background.add_task(extract_in_background, session.id, user_turn.id)

    if intent == CORRECTION:
        session.add_annotation(
            [user_turn.id],
            "correction",
            "Operación de corrección reconocida por el controlador; requiere vinculación investigadora.",
            actor=ACTOR_SYSTEM,
        )

    if intent == OFF_TOPIC or intent in FIXED_PROTOCOL_RESPONSES:
        assistant_text = FIXED_REDIRECT if intent == OFF_TOPIC else FIXED_PROTOCOL_RESPONSES[intent]
        status = protocol_status(intent)
        if status:
            session.set_status(status, intent)
        session.record(
            ACTOR_SYSTEM,
            "operacion_protocolo",
            f"El controlador aplicó {intent} sin delegar la respuesta al entrevistador",
            target_id=user_turn.id,
            target_kind="turn",
            detail={"intent": intent},
        )
        assistant_turn = session.add_turn(
            "assistant",
            assistant_text,
            actor=ACTOR_SYSTEM,
            record_kind="protocol_response" if intent != OFF_TOPIC else "redirect",
            intent=intent,
            move="REDIRECT" if intent == OFF_TOPIC else "PROTOCOL",
        )
        store.save(session)
        return {
            "intent": intent,
            "move": "REDIRECT" if intent == OFF_TOPIC else intent,
            "user_turn": user_turn.__dict__,
            "assistant_turn": assistant_turn.__dict__,
            "session": session.to_dict(),
        }

    try:
        candidate = await llm.interview(_interview_history(session))
    except Exception as exc:
        store.save(session)
        return JSONResponse(
            status_code=503,
            content={
                "error": str(exc),
                "user_turn": user_turn.__dict__,
                "session": session.to_dict(),
            },
        )

    known_turns = {
        turn.id: turn.text
        for turn in session.turns
        if turn.role == "user" and turn.record_kind == "testimony"
    }
    recent_assistant = [
        turn.text
        for turn in session.turns
        if turn.role == "assistant"
        and turn.record_kind in {"system_intervention", "interview_action", "interview_move", "interview_fallback"}
    ][-4:]
    guarded = guard_interview_move(candidate, known_turns, recent_assistant)
    if guarded:
        move_name, assistant_text = guarded
        actor = ACTOR_MODEL
        turn_kind = "interview_move"
        grounded_in = [candidate.grounded_in]
    else:
        move_name, assistant_text = safe_interview_fallback(recent_assistant)
        actor = ACTOR_SYSTEM
        turn_kind = "interview_fallback"
        grounded_in = [user_turn.id]
        session.record(
            ACTOR_SYSTEM,
            "operacion_protocolo",
            "La salida del entrevistador fue rechazada por el guard y sustituida por una cesión mínima del turno",
            target_id=user_turn.id,
            target_kind="turn",
            detail={
                "intent": intent,
                "guard": "rejected",
                "candidate": {
                    "move": candidate.move,
                    "utterance": candidate.utterance,
                    "grounded_in": candidate.grounded_in,
                },
                "fallback": {"move": move_name, "utterance": assistant_text},
            },
        )

    assistant_turn = session.add_turn(
        "assistant",
        assistant_text,
        actor=actor,
        record_kind=turn_kind,
        move=move_name,
        grounded_in=grounded_in,
    )
    store.save(session)
    return {
        "intent": intent,
        "move": move_name,
        "user_turn": user_turn.__dict__,
        "assistant_turn": assistant_turn.__dict__,
        "session": session.to_dict(),
    }


def _interview_history(session) -> list[dict[str, str]]:
    """Exclude control/off-topic material from the interviewing model's context."""
    return [
        {"id": turn.id, "role": turn.role, "text": turn.text}
        for turn in session.turns
        if (
            turn.role == "user" and turn.record_kind == "testimony"
        )
        or (
            turn.role == "assistant"
            and turn.record_kind in {
                "system_intervention",
                "interview_action",  # sessions written before conversational moves
                "interview_move",
                "interview_fallback",
            }
        )
    ]


@app.post("/api/sessions/{session_id}/resume")
def resume_session(session_id: str) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    if session.status != "paused":
        raise HTTPException(409, "Sólo una sesión pausada puede reanudarse")
    session.set_status("active", "RESUME")
    store.save(session)
    return session.to_dict()


@app.post("/api/sessions/{session_id}/voice/transcribe")
async def transcribe_voice(session_id: str, request: Request) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    if session.is_recorded or session.status != "active":
        raise HTTPException(409, "La sesión no admite una nueva entrada de voz")
    if not voice.asr_configured:
        raise HTTPException(503, "Entrada de voz no configurada; revisá /api/config")
    audio = await request.body()
    if not audio:
        raise HTTPException(400, "El audio está vacío")
    if len(audio) > 25 * 1024 * 1024:
        raise HTTPException(413, "El audio supera el límite de 25 MB")
    mime_type = request.headers.get("content-type", "audio/webm").split(";", 1)[0]
    suffix = audio_suffix(mime_type)
    try:
        transcript, asr_detail = await asyncio.to_thread(voice.transcribe, audio, suffix)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

    audio_id = new_id("audio")
    relative = Path("data") / "audio" / safe_filename(session.id) / f"{audio_id}{suffix}"
    absolute = ROOT / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_bytes(audio)
    record = session.add_audio_record(
        str(relative), mime_type, len(audio), transcript, asr_detail, record_id=audio_id
    )
    store.save(session)
    return {"audio_id": record.id, "text": transcript, "asr": asr_detail}


@app.post("/api/voice/speak")
async def speak_voice(body: SpeechCreate) -> Response:
    if not voice.tts_configured:
        raise HTTPException(503, "Salida de voz no configurada; revisá /api/config")
    try:
        audio = await asyncio.to_thread(voice.synthesize, body.text)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(content=audio, media_type="audio/wav")


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


async def run_extraction(session, turns: list) -> list[dict[str, Any]]:
    """Extract from the given turns and attach the result with full provenance."""
    known = {t.id: t for t in session.turns}
    extracted = await llm.extract([t.__dict__ for t in turns])

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
        detail={**provenance, "source_turn_ids": [t.id for t in turns]},
    )
    store.save(session)
    return created


# Queued extractions run one at a time. Several recollections in quick
# succession would otherwise fire several concurrent analysis calls at a local
# server that can only really do one thing well at once.
extraction_queue = asyncio.Lock()


async def extract_in_background(session_id: str, turn_id: str) -> None:
    """Grow the memory field from one recollection without delaying the reply.

    The participant is talking; extraction must never sit between what they said
    and what the system says back — and on a single local server, "not blocking
    the reply" is not enough. An analysis call issued while the participant is
    typing their next turn still competes for the same weights, so this waits
    for the conversational model to go quiet before asking anything of it.

    The recollection itself is already visible in the field by then: it appears
    the moment the turn is stored, and this only adds what was read out of it.

    Failure here is recorded and otherwise ignored — the transcript is the
    archive, the field is a working surface.
    """
    try:
        session = store.get(session_id)
    except KeyError:
        return
    turn = next((t for t in session.turns if t.id == turn_id), None)
    if turn is None or turn.record_kind != "testimony":
        return
    async with extraction_queue:
        await llm.gate.wait_until_idle()
        try:
            await run_extraction(session, [turn])
        except Exception as exc:  # noqa: BLE001 - a failed extraction must not surface mid-conversation
            session.record(
                ACTOR_MODEL,
                "extraccion_fallida",
                f"La extracción automática falló para un turno: {exc}",
                target_id=turn_id,
                target_kind="turn",
            )
            store.save(session)


@app.get("/api/memory-field")
def memory_field(focus: str = "") -> dict[str, Any]:
    """The accumulated graph across every stored conversation."""
    field = build_memory_field(store.list())
    field["focus"] = focus
    return field


@app.get("/api/timeline")
def timeline() -> dict[str, Any]:
    """A chronology the accumulated material produces without resolving it first.

    Years are read out of the phrases people used; the phrases stay attached and
    a subject dated two ways appears at both years.
    """
    return build_timeline(store.list())


@app.post("/api/sessions/{session_id}/extract")
async def extract(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    source_turn_ids = payload.get("source_turn_ids") or [
        t.id for t in session.turns if t.role == "user" and t.record_kind == "testimony"
    ]
    known = {t.id: t for t in session.turns}
    try:
        turns = [known[x] for x in source_turn_ids]
    except KeyError as exc:
        raise HTTPException(400, f"Turno fuente desconocido: {exc.args[0]}") from exc
    blocked = [turn.id for turn in turns if turn.record_kind == "non_testimony/control"]
    if blocked:
        raise HTTPException(400, "Las entradas de control/no testimoniales no se extraen")
    try:
        created = await run_extraction(session, turns)
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc
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
