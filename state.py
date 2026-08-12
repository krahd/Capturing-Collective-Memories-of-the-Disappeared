from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import re
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _as_text(value: Any) -> str:
    """Render a changed field for the revision record without losing information."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(str(x) for x in value)
    return str(value)


def preview(text: str, limit: int = 70) -> str:
    """Short quotable fragment for the session record, never a replacement for the turn."""
    collapsed = " ".join(text.split())
    return collapsed if len(collapsed) <= limit else f"{collapsed[:limit].rstrip()}…"


# Who performed an action. The distinction is the point: participant speech,
# researcher interpretation and model output must never be indistinguishable.
ACTOR_PARTICIPANT = "participante"
ACTOR_RESEARCHER = "investigador"
ACTOR_MODEL = "modelo"
ACTOR_SYSTEM = "sistema"

ORIGIN_RESEARCHER = ACTOR_RESEARCHER
ORIGIN_MODEL = ACTOR_MODEL

# Readable names for record entries, also used when an entry is redacted.
ACTION_TITLES = {
    "sesion_creada": "Sesión iniciada",
    "turno_registrado": "Turno preservado",
    "anotacion_agregada": "Anotación",
    "interpretacion_creada": "Interpretación creada",
    "interpretacion_editada": "Edición registrada",
    "interpretacion_retirada": "Retiro",
    "interpretacion_eliminada": "Eliminación",
    "relacion_agregada": "Relación",
    "extraccion_ejecutada": "Extracción automática",
    "entrada_clasificada": "Clasificación de entrada",
    "operacion_protocolo": "Operación de protocolo",
    "estado_sesion_cambiado": "Estado de la sesión",
    "audio_preservado": "Audio preservado",
    "transcripcion_asr_creada": "Transcripción ASR",
}


@dataclass
class Turn:
    id: str
    role: str
    text: str
    created_at: str = field(default_factory=now_iso)
    # A participant utterance can remain in the immutable transcript without
    # being treated as testimony by extraction or the interviewing model.
    record_kind: str = "testimony"
    intent: str = ""
    input_mode: str = "text"
    audio_id: str = ""
    transcription_detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioRecord:
    """Participant-produced audio and its machine-derived transcript."""

    id: str
    storage_path: str
    mime_type: str
    byte_length: int
    transcript: str
    asr_detail: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)


@dataclass
class Revision:
    """One recorded change to a derived item. Append-only."""

    at: str
    field: str
    before: str
    after: str


@dataclass
class Event:
    """One entry in the append-only session record."""

    id: str
    at: str
    actor: str
    action: str
    summary: str
    target_id: str = ""
    target_kind: str = ""
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Annotation:
    id: str
    source_turn_ids: list[str]
    label: str
    note: str = ""
    created_at: str = field(default_factory=now_iso)


@dataclass
class DerivedItem:
    id: str
    kind: str
    text: str
    source_turn_ids: list[str]
    status: str = "provisional"
    note: str = ""
    created_at: str = field(default_factory=now_iso)
    # No interpretation is anonymous: every derived item says who produced it,
    # and a model-produced one carries the exact model and sampling settings.
    origin: str = ORIGIN_RESEARCHER
    origin_detail: dict[str, Any] = field(default_factory=dict)
    revisions: list[Revision] = field(default_factory=list)
    withdrawn: bool = False
    withdrawn_at: str = ""
    withdrawn_reason: str = ""


@dataclass
class Relation:
    id: str
    relation_type: str
    source_id: str
    target_id: str
    note: str = ""
    created_at: str = field(default_factory=now_iso)


@dataclass
class Session:
    id: str
    title: str = "Conversación sin título"
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    turns: list[Turn] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    derived_items: list[DerivedItem] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    audio_records: list[AudioRecord] = field(default_factory=list)
    status: str = "active"
    # True only for the researcher-authored example transcript. It is never a
    # live conversation and the interface must say so.
    is_recorded: bool = False

    def touch(self) -> None:
        self.updated_at = now_iso()

    def record(
        self,
        actor: str,
        action: str,
        summary: str,
        target_id: str = "",
        target_kind: str = "",
        detail: dict[str, Any] | None = None,
    ) -> Event:
        """Append one entry to the session record. Entries are never rewritten."""
        event = Event(
            id=new_id("ev"),
            at=now_iso(),
            actor=actor,
            action=action,
            summary=summary,
            target_id=target_id,
            target_kind=target_kind,
            detail=detail or {},
        )
        self.events.append(event)
        return event

    def add_turn(
        self,
        role: str,
        text: str,
        actor: str | None = None,
        *,
        record_kind: str | None = None,
        intent: str = "",
        input_mode: str = "text",
        audio_id: str = "",
        transcription_detail: dict[str, Any] | None = None,
    ) -> Turn:
        if not text.strip():
            raise ValueError("El turno no puede estar vacío")
        # Preserve the submitted turn byte-for-byte at the string level;
        # normalisation belongs only in derived/editable layers.
        kind = record_kind or ("testimony" if role == "user" else "system_intervention")
        turn = Turn(
            id=new_id("turn"),
            role=role,
            text=text,
            record_kind=kind,
            intent=intent,
            input_mode=input_mode,
            audio_id=audio_id,
            transcription_detail=dict(transcription_detail or {}),
        )
        self.turns.append(turn)
        speaker = actor or (ACTOR_PARTICIPANT if role == "user" else ACTOR_MODEL)
        self.record(
            speaker,
            "turno_registrado",
            f"Turno preservado: «{preview(text)}»",
            target_id=turn.id,
            target_kind="turn",
        )
        self.touch()
        return turn

    def classify_turn(self, turn_id: str, intent: str, record_kind: str) -> Turn:
        turn = next((candidate for candidate in self.turns if candidate.id == turn_id), None)
        if turn is None:
            raise ValueError(f"Turno desconocido: {turn_id}")
        turn.intent = intent
        turn.record_kind = record_kind
        self.record(
            ACTOR_SYSTEM,
            "entrada_clasificada",
            f"Entrada clasificada como {intent}; capa: {record_kind}",
            target_id=turn.id,
            target_kind="turn",
            detail={"intent": intent, "record_kind": record_kind},
        )
        self.touch()
        return turn

    def add_audio_record(
        self,
        storage_path: str,
        mime_type: str,
        byte_length: int,
        transcript: str,
        asr_detail: dict[str, Any],
        record_id: str | None = None,
    ) -> AudioRecord:
        record = AudioRecord(
            id=record_id or new_id("audio"),
            storage_path=storage_path,
            mime_type=mime_type,
            byte_length=byte_length,
            transcript=transcript,
            asr_detail=dict(asr_detail),
        )
        self.audio_records.append(record)
        self.record(
            ACTOR_PARTICIPANT,
            "audio_preservado",
            f"Audio original preservado ({byte_length} bytes)",
            target_id=record.id,
            target_kind="audio",
            detail={"mime_type": mime_type, "storage_path": storage_path},
        )
        self.record(
            ACTOR_MODEL,
            "transcripcion_asr_creada",
            f"Transcripción automática creada: «{preview(transcript)}»",
            target_id=record.id,
            target_kind="audio",
            detail=dict(asr_detail),
        )
        self.touch()
        return record

    def set_status(self, status: str, operation: str = "") -> None:
        if status not in {"active", "paused", "stopped", "revocation_requested"}:
            raise ValueError(f"Estado de sesión desconocido: {status}")
        before = self.status
        self.status = status
        self.record(
            ACTOR_SYSTEM,
            "estado_sesion_cambiado",
            f"Estado de la sesión: {before} → {status}",
            target_id=self.id,
            target_kind="session",
            detail={"before": before, "after": status, "operation": operation},
        )
        self.touch()

    def add_annotation(
        self,
        source_turn_ids: list[str],
        label: str,
        note: str = "",
        actor: str = ACTOR_RESEARCHER,
    ) -> Annotation:
        self._validate_turn_ids(source_turn_ids)
        annotation = Annotation(
            id=new_id("ann"),
            source_turn_ids=list(dict.fromkeys(source_turn_ids)),
            label=label.strip(),
            note=note.strip(),
        )
        self.annotations.append(annotation)
        self.record(
            actor,
            "anotacion_agregada",
            f"Anotación «{annotation.label}» sobre {len(annotation.source_turn_ids)} turno(s)",
            target_id=annotation.id,
            target_kind="annotation",
            detail={"source_turn_ids": list(annotation.source_turn_ids), "note": annotation.note},
        )
        self.touch()
        return annotation

    def add_derived_item(
        self,
        kind: str,
        text: str,
        source_turn_ids: list[str],
        note: str = "",
        origin: str = ORIGIN_RESEARCHER,
        origin_detail: dict[str, Any] | None = None,
    ) -> DerivedItem:
        self._validate_turn_ids(source_turn_ids)
        blocked = [
            turn.id
            for turn in self.turns
            if turn.id in source_turn_ids and turn.record_kind == "non_testimony/control"
        ]
        if blocked:
            raise ValueError(
                "Una entrada de control/no testimonial no puede entrar al material derivado: "
                + ", ".join(blocked)
            )
        item = DerivedItem(
            id=new_id("item"),
            kind=kind.strip(),
            text=text.strip(),
            source_turn_ids=list(dict.fromkeys(source_turn_ids)),
            note=note.strip(),
            origin=origin,
            origin_detail=dict(origin_detail or {}),
        )
        self.derived_items.append(item)
        by = "El modelo" if origin == ORIGIN_MODEL else "El investigador"
        self.record(
            origin,
            "interpretacion_creada",
            f"{by} creó una interpretación provisional ({item.kind}): «{preview(item.text)}»",
            target_id=item.id,
            target_kind="derived",
            detail={"source_turn_ids": list(item.source_turn_ids), **item.origin_detail},
        )
        self.touch()
        return item

    def update_derived_item(self, item_id: str, **changes: Any) -> DerivedItem:
        item = self._find_item(item_id)
        allowed = {"kind", "text", "status", "note", "source_turn_ids"}
        applied: list[Revision] = []
        for key, value in changes.items():
            if key not in allowed or value is None:
                continue
            if key == "source_turn_ids":
                self._validate_turn_ids(value)
                value = list(dict.fromkeys(value))
            if isinstance(value, str):
                value = value.strip()
            previous = getattr(item, key)
            if previous == value:
                continue
            # An edit never destroys what was there before.
            revision = Revision(
                at=now_iso(),
                field=key,
                before=_as_text(previous),
                after=_as_text(value),
            )
            item.revisions.append(revision)
            applied.append(revision)
            setattr(item, key, value)
        if applied:
            fields = ", ".join(revision.field for revision in applied)
            self.record(
                ACTOR_RESEARCHER,
                "interpretacion_editada",
                f"El investigador editó una interpretación ({fields})",
                target_id=item.id,
                target_kind="derived",
                detail={"cambios": [asdict(revision) for revision in applied]},
            )
        self.touch()
        return item

    def withdraw_derived_item(self, item_id: str, reason: str = "") -> DerivedItem:
        """Retire an interpretation without erasing it. The record keeps everything."""
        item = self._find_item(item_id)
        item.withdrawn = True
        item.withdrawn_at = now_iso()
        item.withdrawn_reason = reason.strip()
        item.status = "withdrawn"
        self.record(
            ACTOR_RESEARCHER,
            "interpretacion_retirada",
            f"Interpretación retirada, no eliminada: «{preview(item.text)}»"
            + (f" — motivo: {item.withdrawn_reason}" if item.withdrawn_reason else ""),
            target_id=item.id,
            target_kind="derived",
            detail={"motivo": item.withdrawn_reason, "texto_retenido": item.text},
        )
        self.touch()
        return item

    def delete_derived_item(self, item_id: str) -> DerivedItem:
        item = self._find_item(item_id)
        self.derived_items = [candidate for candidate in self.derived_items if candidate.id != item_id]
        # Relations are working structures, not source records. Remove dangling
        # relations when a provisional derived item is deliberately discarded.
        self.relations = [
            relation
            for relation in self.relations
            if relation.source_id != item_id and relation.target_id != item_id
        ]
        # Deliberate destruction stays destructive. Earlier entries quoted the
        # text, so they are redacted too — otherwise "eliminar" would be a
        # false promise. The redaction is itself recorded: entries are never
        # removed from the record, and the fact that one was redacted, when,
        # and by whom remains visible.
        redacted = self._redact_events_for(item.id)
        self.record(
            ACTOR_RESEARCHER,
            "interpretacion_eliminada",
            f"Interpretación eliminada definitivamente ({item.kind}). "
            f"El texto no se conserva; {redacted} entrada(s) previa(s) del registro fueron redactadas.",
            target_id=item.id,
            target_kind="derived",
            detail={"kind": item.kind, "origin": item.origin, "entradas_redactadas": redacted},
        )
        self.touch()
        return item

    def _redact_events_for(self, item_id: str) -> int:
        """Strip retained text from earlier entries about a purged item."""
        count = 0
        for event in self.events:
            if event.target_id != item_id or event.detail.get("redactado"):
                continue
            event.summary = f"{ACTION_TITLES.get(event.action, event.action)} (texto redactado)"
            for key in ("texto_retenido", "cambios", "motivo"):
                event.detail.pop(key, None)
            event.detail["redactado"] = True
            count += 1
        return count

    def add_relation(self, relation_type: str, source_id: str, target_id: str, note: str = "") -> Relation:
        known = {t.id for t in self.turns} | {a.id for a in self.annotations} | {i.id for i in self.derived_items}
        if source_id not in known or target_id not in known:
            raise ValueError("La relación debe apuntar a elementos existentes")
        relation = Relation(
            id=new_id("rel"),
            relation_type=relation_type.strip(),
            source_id=source_id,
            target_id=target_id,
            note=note.strip(),
        )
        self.relations.append(relation)
        self.record(
            ACTOR_RESEARCHER,
            "relacion_agregada",
            f"Relación «{relation.relation_type}» entre dos elementos",
            target_id=relation.id,
            target_kind="relation",
            detail={"source_id": source_id, "target_id": target_id, "note": relation.note},
        )
        self.touch()
        return relation

    def summary(self) -> dict[str, Any]:
        """Counts used by the Auditoría panel and the Markdown export."""
        active = [item for item in self.derived_items if not item.withdrawn]
        return {
            "turnos": len(self.turns),
            "turnos_participante": sum(1 for t in self.turns if t.role == "user"),
            "interpretaciones": len(active),
            "interpretaciones_investigador": sum(1 for i in active if i.origin == ORIGIN_RESEARCHER),
            "interpretaciones_modelo": sum(1 for i in active if i.origin == ORIGIN_MODEL),
            "retiradas": sum(1 for i in self.derived_items if i.withdrawn),
            "ediciones": sum(len(i.revisions) for i in self.derived_items),
            "anotaciones": len(self.annotations),
            "relaciones": len(self.relations),
            "eventos": len(self.events),
            "audios": len(self.audio_records),
            "estado": self.status,
        }

    def _validate_turn_ids(self, ids: list[str]) -> None:
        if not ids:
            raise ValueError("Se necesita por lo menos un turno fuente")
        known = {t.id for t in self.turns}
        missing = [turn_id for turn_id in ids if turn_id not in known]
        if missing:
            raise ValueError(f"Turnos fuente desconocidos: {', '.join(missing)}")

    def _find_item(self, item_id: str) -> DerivedItem:
        for item in self.derived_items:
            if item.id == item_id:
                return item
        raise ValueError(f"Elemento derivado desconocido: {item_id}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        return cls(
            id=data["id"],
            title=data.get("title", "Conversación sin título"),
            created_at=data.get("created_at", now_iso()),
            updated_at=data.get("updated_at", now_iso()),
            turns=[Turn(**x) for x in data.get("turns", [])],
            annotations=[Annotation(**x) for x in data.get("annotations", [])],
            derived_items=[_derived_from_dict(x) for x in data.get("derived_items", [])],
            relations=[Relation(**x) for x in data.get("relations", [])],
            events=[Event(**x) for x in data.get("events", [])],
            audio_records=[AudioRecord(**x) for x in data.get("audio_records", [])],
            status=data.get("status", "active"),
            is_recorded=bool(data.get("is_recorded", False)),
        )


def _derived_from_dict(data: dict[str, Any]) -> DerivedItem:
    """Load a derived item, tolerating sessions written before the audit layer existed."""
    fields = dict(data)
    fields["revisions"] = [Revision(**x) for x in fields.get("revisions", [])]
    fields.setdefault("origin", ORIGIN_RESEARCHER)
    fields.setdefault("origin_detail", {})
    fields.setdefault("withdrawn", False)
    fields.setdefault("withdrawn_at", "")
    fields.setdefault("withdrawn_reason", "")
    return DerivedItem(**fields)


def load_recorded_session(path: str | Path) -> Session:
    """Load the researcher-authored example transcript under a fresh session id.

    The material is authored, not captured from a participant, and not generated
    live. `is_recorded` forces the interface to say so.
    """
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    session = Session.from_dict(json.loads(source.read_text(encoding="utf-8")))
    session.id = new_id("session")
    session.is_recorded = True
    session.created_at = now_iso()
    session.touch()
    return session


class SessionStore:
    def __init__(self, root: str | Path = "data/sessions") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, Session] = {}

    def create(self, title: str | None = None) -> Session:
        session = Session(id=new_id("session"), title=(title or "Conversación sin título").strip())
        session.record(ACTOR_SYSTEM, "sesion_creada", f"Sesión iniciada: {session.title}")
        self._sessions[session.id] = session
        self.save(session)
        return session

    def adopt(self, session: Session) -> Session:
        """Register an externally constructed session, such as the recorded example."""
        self._sessions[session.id] = session
        self.save(session)
        return session

    def get(self, session_id: str) -> Session:
        if session_id in self._sessions:
            return self._sessions[session_id]
        path = self.root / f"{safe_filename(session_id)}.json"
        if not path.exists():
            raise KeyError(session_id)
        session = Session.from_dict(json.loads(path.read_text(encoding="utf-8")))
        self._sessions[session_id] = session
        return session

    def save(self, session: Session) -> None:
        path = self.root / f"{safe_filename(session.id)}.json"
        path.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def list(self) -> list[Session]:
        found: dict[str, Session] = dict(self._sessions)
        for path in self.root.glob("session_*.json"):
            try:
                session = Session.from_dict(json.loads(path.read_text(encoding="utf-8")))
                found.setdefault(session.id, session)
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        return sorted(found.values(), key=lambda x: x.updated_at, reverse=True)


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", value)
    return cleaned[:120]


def export_markdown(session: Session) -> str:
    counts = session.summary()
    lines = [f"# {session.title}", "", f"Session: `{session.id}`", ""]
    if session.is_recorded:
        lines.extend(["> **Transcripción grabada.** No es una conversación en vivo.", ""])
    lines.extend([
        " · ".join([
            f"{counts['turnos']} turnos preservados",
            f"{counts['interpretaciones']} interpretaciones "
            f"({counts['interpretaciones_investigador']} del investigador, "
            f"{counts['interpretaciones_modelo']} del modelo)",
            f"{counts['retiradas']} {'retirada' if counts['retiradas'] == 1 else 'retiradas'}",
            f"{counts['ediciones']} {'edición' if counts['ediciones'] == 1 else 'ediciones'} registrada"
            + ("" if counts["ediciones"] == 1 else "s"),
        ]),
        "",
        "## Transcript",
        "",
    ])
    for turn in session.turns:
        if turn.role == "user" and turn.record_kind == "non_testimony/control":
            speaker = f"Participante · control/no testimonial · {turn.intent or 'sin clasificar'}"
        else:
            speaker = "Participante" if turn.role == "user" else "Conversación"
        lines.extend([f"### {speaker} · `{turn.id}`", "", turn.text, ""])
        if turn.audio_id:
            lines.extend(
                [
                    f"> Entrada por voz. Audio original: `{turn.audio_id}`; el texto es una transcripción ASR derivada.",
                    "",
                ]
            )

    if session.audio_records:
        lines.extend(["## Capas de audio y transcripción", ""])
        for audio in session.audio_records:
            model = audio.asr_detail.get("model", "whisper.cpp")
            language = audio.asr_detail.get("language", "")
            lines.append(
                f"- `{audio.id}` — audio original `{audio.storage_path}` "
                f"({audio.mime_type}, {audio.byte_length} bytes); "
                f"transcripción derivada por {model}{f' · {language}' if language else ''}: "
                f"«{audio.transcript}»"
            )
        lines.append("")

    if session.annotations:
        lines.extend(["## Anotaciones", ""])
        for ann in session.annotations:
            refs = ", ".join(f"`{x}`" for x in ann.source_turn_ids)
            lines.append(f"- **{ann.label}** ({refs}): {ann.note or '—'}")
        lines.append("")

    if session.derived_items:
        lines.extend(["## Material derivado provisional", ""])
        for item in session.derived_items:
            refs = ", ".join(f"`{x}`" for x in item.source_turn_ids)
            by = "modelo" if item.origin == ORIGIN_MODEL else "investigador"
            model_id = item.origin_detail.get("model")
            attribution = f"{by} · {model_id}" if model_id else by
            mark = "~~" if item.withdrawn else ""
            lines.append(
                f"- **{item.kind} / {item.status}** [{attribution}]: "
                f"{mark}{item.text}{mark} — fuentes: {refs}"
            )
            if item.withdrawn:
                motive = f": {item.withdrawn_reason}" if item.withdrawn_reason else ""
                lines.append(f"  - Retirada, no eliminada{motive}")
            if item.note:
                lines.append(f"  - Nota: {item.note}")
            for revision in item.revisions:
                lines.append(
                    f"  - Revisión ({revision.field}): «{revision.before}» → «{revision.after}»"
                )
        lines.append("")

    if session.relations:
        lines.extend(["## Relaciones", ""])
        for rel in session.relations:
            lines.append(f"- `{rel.source_id}` — **{rel.relation_type}** → `{rel.target_id}`{': ' + rel.note if rel.note else ''}")
        lines.append("")

    if session.events:
        lines.extend(["## Registro de la sesión", ""])
        for event in session.events:
            lines.append(f"- `{event.at}` · **{event.actor}** · {event.summary}")
        lines.append("")

    lines.extend([
        "---",
        "El material derivado de la conversación es provisional. La transcripción exacta permanece como fuente primaria del prototipo.",
        "Cada interpretación indica quién la produjo. El material retirado se conserva marcado como retirado, no se borra.",
        "",
    ])
    return "\n".join(lines)
