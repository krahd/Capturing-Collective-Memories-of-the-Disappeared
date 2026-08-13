"""The memory field: what many conversations accumulate into.

This module builds one graph across every stored conversation. Its shape encodes
a claim the project cares about, so it is worth stating plainly.

A conventional knowledge graph would read `Person → Event → Place` and would
thereby present testimony as resolved fact. Here **recollections are first-class
nodes**. Entities hang off the recollections that mention them, and a
recollection always belongs to a conversation:

    Conversación 07
        ├── recuerdo r1 ── menciona ──→ Julio
        │                └─ ocurre en ─→ la facultad
        └── recuerdo r2 ── fecha ─────→ 1976

Two recollections may date the same material differently. Both edges are kept.
Nothing here resolves a contradiction into a canonical value; density comes from
recollections converging on shared entities, not from adjudication.

Epistemic qualities the extraction reports — uncertainty, hearsay, correction —
are not separate nodes. They are marks on the recollection that carries them,
because they describe how something was said rather than a thing in the world.
"""

from __future__ import annotations

from typing import Any, Iterable
import re
import unicodedata

from state import ORIGIN_MODEL, Session

# Extraction kinds that name something in the world, and the node type each
# becomes. Anything not listed is either an epistemic mark or is left out.
ENTITY_KINDS = {
    "entity": "person",
    "place": "place",
    "event": "event",
    "time": "time",
    "theme": "theme",
}

# Extraction kinds that describe how a thing was said, not a thing.
EPISTEMIC_KINDS = {"uncertainty", "hearsay", "correction"}

EDGE_LABELS = {
    "person": "menciona",
    "place": "ocurre en",
    "event": "recuerda",
    "time": "fecha",
    "theme": "trata de",
}

# Order the counters and chips are shown in.
NODE_TYPE_LABELS = {
    "person": "Personas",
    "place": "Lugares",
    "event": "Eventos",
    "time": "Fechas",
    "theme": "Temas",
}


# A relational descriptor in front of a name — "mi tío Aníbal" — is how the
# speaker situates a person, not part of the name. Stripping it lets two
# conversations that say "mi tío Aníbal" and "Aníbal" meet at one node. This is
# a linguistic normalisation and it fires only when a name actually follows.
KINSHIP = (
    r"tio|tia|abuelo|abuela|padre|madre|papa|mama|viejo|vieja|hermano|hermana|"
    r"primo|prima|maestro|maestra|vecino|vecina|amigo|amiga"
)
KINSHIP_PREFIX = re.compile(rf"^(?:mi|su|tu|el|la|un|una)\s+(?:{KINSHIP})\s+(?=\S)")


def normalise(text: str) -> str:
    """Fold a label so the same person mentioned in two conversations is one node.

    Deliberately conservative: case, accents, punctuation, leading articles and a
    leading kinship descriptor. It does **not** attempt identity resolution —
    deciding that two differently-named people are the same person is a research
    problem, and doing it silently here would be exactly the collapsing of
    plurality this project exists to avoid.
    """
    lowered = unicodedata.normalize("NFKD", text.strip().lower())
    stripped = "".join(c for c in lowered if not unicodedata.combining(c))
    stripped = re.sub(r"[«»\"'`.,;:!¡?¿()\[\]]", "", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    stripped = KINSHIP_PREFIX.sub("", stripped)
    stripped = re.sub(r"^(el|la|los|las|un|una|unos|unas)\s+(?=\S)", "", stripped)
    return stripped.strip()


class MemoryField:
    """Accumulating graph over many conversations."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self._edge_keys: set[tuple[str, str, str]] = set()

    def _node(self, node_id: str, node_type: str, label: str, **extra: Any) -> dict[str, Any]:
        existing = self.nodes.get(node_id)
        if existing is None:
            existing = {
                "id": node_id,
                "type": node_type,
                "label": label,
                "conversations": [],
                "recollections": [],
                **extra,
            }
            self.nodes[node_id] = existing
        return existing

    def _edge(self, source: str, target: str, label: str, **extra: Any) -> None:
        key = (source, target, label)
        if key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self.edges.append({"source": source, "target": target, "label": label, **extra})

    def add_session(self, session: Session, index: int) -> None:
        conversation_id = f"conv:{session.id}"
        conversation = self._node(
            conversation_id,
            "conversation",
            session.title or f"Conversación {index + 1}",
            session_id=session.id,
            recorded=session.is_recorded,
        )
        conversation["conversations"] = [session.id]

        # Which turns carry epistemic marks, and which entities each turn produced.
        marks: dict[str, set[str]] = {}
        by_turn: dict[str, list[Any]] = {}
        for item in session.derived_items:
            if item.withdrawn:
                # Withdrawn interpretation leaves the field. The transcript and
                # the session record still hold it; the accumulated graph is a
                # working surface, not the archive.
                continue
            for turn_id in item.source_turn_ids:
                if item.kind in EPISTEMIC_KINDS:
                    marks.setdefault(turn_id, set()).add(item.kind)
                elif item.kind in ENTITY_KINDS:
                    by_turn.setdefault(turn_id, []).append(item)

        for turn in session.turns:
            if turn.role != "user" or turn.record_kind != "testimony":
                continue
            items = by_turn.get(turn.id, [])
            turn_marks = sorted(marks.get(turn.id, set()))
            if not items and not turn_marks:
                # A recollection with nothing extracted from it yet still counts:
                # it is testimony that exists and is waiting to be connected.
                pass

            recollection_id = f"rec:{turn.id}"
            recollection = self._node(
                recollection_id,
                "recollection",
                turn.text,
                session_id=session.id,
                turn_id=turn.id,
                marks=turn_marks,
                voice=turn.input_mode == "voice_asr",
            )
            recollection["conversations"] = [session.id]
            recollection["recollections"] = [turn.id]
            self._edge(conversation_id, recollection_id, "recuerda")

            for item in items:
                node_type = ENTITY_KINDS[item.kind]
                entity_id = f"{node_type}:{normalise(item.text)}"
                entity = self._node(entity_id, node_type, item.text.strip())
                if session.id not in entity["conversations"]:
                    entity["conversations"].append(session.id)
                if turn.id not in entity["recollections"]:
                    entity["recollections"].append(turn.id)
                self._edge(
                    recollection_id,
                    entity_id,
                    EDGE_LABELS[node_type],
                    from_model=item.origin == ORIGIN_MODEL,
                )


def build_memory_field(sessions: Iterable[Session]) -> dict[str, Any]:
    """One graph over every conversation, plus the counters shown above it."""
    ordered = sorted(sessions, key=lambda s: s.created_at)
    field = MemoryField()
    for index, session in enumerate(ordered):
        field.add_session(session, index)

    nodes = list(field.nodes.values())
    by_type: dict[str, int] = {}
    for node in nodes:
        by_type[node["type"]] = by_type.get(node["type"], 0) + 1

    # An entity appearing in more than one conversation is where the collective
    # structure actually shows itself, so it is counted separately.
    shared = sum(
        1
        for node in nodes
        if node["type"] in NODE_TYPE_LABELS and len(node["conversations"]) > 1
    )

    return {
        "nodes": nodes,
        "edges": field.edges,
        "counts": {
            "conversaciones": by_type.get("conversation", 0),
            "recuerdos": by_type.get("recollection", 0),
            "entidades": sum(by_type.get(t, 0) for t in NODE_TYPE_LABELS),
            "relaciones": len(field.edges),
            "compartidas": shared,
        },
        "extracted": [
            {"type": node_type, "label": label, "count": by_type.get(node_type, 0)}
            for node_type, label in NODE_TYPE_LABELS.items()
        ],
    }
