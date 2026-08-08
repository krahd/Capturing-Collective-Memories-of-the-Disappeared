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


@dataclass
class Turn:
    id: str
    role: str
    text: str
    created_at: str = field(default_factory=now_iso)


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

    def touch(self) -> None:
        self.updated_at = now_iso()

    def add_turn(self, role: str, text: str) -> Turn:
        if not text.strip():
            raise ValueError("El turno no puede estar vacío")
        # Preserve the submitted turn byte-for-byte at the string level;
        # normalisation belongs only in derived/editable layers.
        turn = Turn(id=new_id("turn"), role=role, text=text)
        self.turns.append(turn)
        self.touch()
        return turn

    def add_annotation(self, source_turn_ids: list[str], label: str, note: str = "") -> Annotation:
        self._validate_turn_ids(source_turn_ids)
        annotation = Annotation(
            id=new_id("ann"),
            source_turn_ids=list(dict.fromkeys(source_turn_ids)),
            label=label.strip(),
            note=note.strip(),
        )
        self.annotations.append(annotation)
        self.touch()
        return annotation

    def add_derived_item(self, kind: str, text: str, source_turn_ids: list[str], note: str = "") -> DerivedItem:
        self._validate_turn_ids(source_turn_ids)
        item = DerivedItem(
            id=new_id("item"),
            kind=kind.strip(),
            text=text.strip(),
            source_turn_ids=list(dict.fromkeys(source_turn_ids)),
            note=note.strip(),
        )
        self.derived_items.append(item)
        self.touch()
        return item

    def update_derived_item(self, item_id: str, **changes: Any) -> DerivedItem:
        item = self._find_item(item_id)
        allowed = {"kind", "text", "status", "note", "source_turn_ids"}
        for key, value in changes.items():
            if key not in allowed or value is None:
                continue
            if key == "source_turn_ids":
                self._validate_turn_ids(value)
                value = list(dict.fromkeys(value))
            if isinstance(value, str):
                value = value.strip()
            setattr(item, key, value)
        self.touch()
        return item

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
        self.touch()
        return relation

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
            derived_items=[DerivedItem(**x) for x in data.get("derived_items", [])],
            relations=[Relation(**x) for x in data.get("relations", [])],
        )


class SessionStore:
    def __init__(self, root: str | Path = "data/sessions") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, Session] = {}

    def create(self, title: str | None = None) -> Session:
        session = Session(id=new_id("session"), title=(title or "Conversación sin título").strip())
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
    lines = [f"# {session.title}", "", f"Session: `{session.id}`", "", "## Transcript", ""]
    for turn in session.turns:
        speaker = "Participante" if turn.role == "user" else "Conversación"
        lines.extend([f"### {speaker} · `{turn.id}`", "", turn.text, ""])

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
            lines.append(f"- **{item.kind} / {item.status}**: {item.text} — fuentes: {refs}")
            if item.note:
                lines.append(f"  - Nota: {item.note}")
        lines.append("")

    if session.relations:
        lines.extend(["## Relaciones", ""])
        for rel in session.relations:
            lines.append(f"- `{rel.source_id}` — **{rel.relation_type}** → `{rel.target_id}`{': ' + rel.note if rel.note else ''}")
        lines.append("")

    lines.extend([
        "---",
        "El material derivado de la conversación es provisional. La transcripción exacta permanece como fuente primaria del prototipo.",
        "",
    ])
    return "\n".join(lines)
