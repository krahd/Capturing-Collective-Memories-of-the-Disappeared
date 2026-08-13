"""The memory field: what many conversations accumulate into.

This module builds one graph across every stored conversation. Its shape encodes
a claim the project cares about, so it is worth stating plainly.

A conventional knowledge graph would read `Person → Event → Place` and would
thereby present testimony as resolved fact. Here **recollections are first-class
nodes**. Entities hang off the recollections that mention them, and a
recollection always belongs to a conversation:

    Conversación 07
        ├── recuerdo r1 ── menciona ───────→ Julio
        │                └─ menciona lugar ─→ la facultad
        └── recuerdo r2 ── menciona fecha ──→ 1976

Every edge says `menciona`. That is deliberately weak: extraction establishes
that a recollection referred to something, not that the remembered episode
occurred there or happened then. An edge reading "ocurre en" would assert more
than the material behind it supports.

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
#
# `entity` stays generic on purpose. Extraction is asked for `person` when it
# means a person; anything it can only call an entity — an institution, an
# organisation, an object — must not be silently drawn and labelled as a person.
# Displaying a stronger claim than the extraction made is exactly the kind of
# quiet hardening this project exists to avoid.
ENTITY_KINDS = {
    "person": "person",
    "entity": "entity",
    "place": "place",
    "event": "event",
    "time": "time",
    "theme": "theme",
}

# Extraction kinds that describe how a thing was said, not a thing.
EPISTEMIC_KINDS = {"uncertainty", "hearsay", "correction"}

# What an edge is allowed to assert. Extraction establishes only that a
# recollection *referred to* something; it does not establish that the
# remembered episode occurred in a place or happened on a date. So every edge
# says `menciona`, differentiated by what was mentioned. "Ocurre en" and
# "recuerda" claimed more than the provenance supports.
EDGE_LABELS = {
    "person": "menciona",
    "entity": "menciona",
    "place": "menciona lugar",
    "event": "menciona hecho",
    "time": "menciona fecha",
    "theme": "menciona tema",
}

# Order the counters and chips are shown in.
NODE_TYPE_LABELS = {
    "person": "Personas",
    "entity": "Entidades",
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

    def add_session(
        self,
        session: Session,
        index: int,
        *,
        source_only: bool = False,
    ) -> None:
        conversation_id = f"conv:{session.id}"
        conversation = self._node(
            conversation_id,
            "conversation",
            session.title or f"Conversación {index + 1}",
            session_id=session.id,
            recorded=session.is_recorded,
            session_kind=session.session_kind,
            demo_run_id=session.demo_run_id,
        )
        conversation["conversations"] = [session.id]

        # Which turns carry epistemic marks, and which entities each turn produced.
        marks: dict[str, set[str]] = {}
        by_turn: dict[str, list[Any]] = {}
        for item in ([] if source_only else session.derived_items):
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
                session_kind=session.session_kind,
                demo_run_id=session.demo_run_id,
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


def build_memory_field(
    sessions: Iterable[Session],
    source_only_session_ids: set[str] | None = None,
) -> dict[str, Any]:
    """One graph over every conversation, plus the counters shown above it."""
    ordered = sorted(sessions, key=lambda s: s.created_at)
    field = MemoryField()
    for index, session in enumerate(ordered):
        field.add_session(
            session,
            index,
            source_only=session.id in (source_only_session_ids or set()),
        )

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


# ---------------------------------------------------------------------------
# Cronología: one view the accumulated material can actually produce.
#
# The interesting claim is not that a chronology can be drawn. It is that one
# can be drawn *without first deciding which date is right*. A year here is a
# reading of the words somebody used, never a replacement for them: every point
# carries the exact phrases behind it, and a subject dated two ways appears at
# both years with both sources reachable.
# ---------------------------------------------------------------------------

FULL_YEAR = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
# "el 76", "por el 77, 78", "'79". A bare two-digit number is only read as a
# year when the phrase frames it as one; otherwise "estaba en cuarto" and
# "tendría nueve o diez" would silently become dates.
SHORT_YEAR_FRAME = re.compile(r"(?:\b(?:el|del|en|por|para|hasta|desde|año|años)\b\s*|')'?\d{2}\b")
SHORT_YEAR = re.compile(r"'?\b(\d{2})\b")


def years_in(label: str) -> list[int]:
    """Read the years a time phrase names, keeping every one it names.

    "por el 77, 78, por ahí" names two years and stays two years: narrowing it
    to one would be exactly the adjudication this view exists to avoid.
    """
    years = {int(value) for value in FULL_YEAR.findall(label)}
    if not years and SHORT_YEAR_FRAME.search(label):
        for value in SHORT_YEAR.findall(label):
            number = int(value)
            if 20 <= number <= 99:
                years.add(1900 + number)
    return sorted(years)


def build_timeline(sessions: Iterable[Session]) -> dict[str, Any]:
    """Years, the recollections that date to them, and what is dated two ways."""
    ordered = sorted(sessions, key=lambda s: s.created_at)
    field = MemoryField()
    for index, session in enumerate(ordered):
        field.add_session(session, index)

    recollections = {
        node["turn_id"]: node for node in field.nodes.values() if node["type"] == "recollection"
    }
    conversation_titles = {
        node["session_id"]: node["label"]
        for node in field.nodes.values()
        if node["type"] == "conversation"
    }

    points: dict[int, dict[str, Any]] = {}
    undated: list[dict[str, Any]] = []
    # Which years each recollection was dated to, so a subject's years can be
    # read off the recollections that mention it.
    years_by_turn: dict[str, set[int]] = {}

    for node in field.nodes.values():
        if node["type"] != "time":
            continue
        years = years_in(node["label"])
        if not years:
            undated.append({"label": node["label"], "recollections": list(node["recollections"])})
            continue
        for year in years:
            point = points.setdefault(
                year, {"year": year, "labels": [], "recollections": [], "conversations": []}
            )
            if node["label"] not in point["labels"]:
                point["labels"].append(node["label"])
            for turn_id in node["recollections"]:
                years_by_turn.setdefault(turn_id, set()).add(year)
                source = recollections.get(turn_id)
                if source is None or any(
                    r["turn_id"] == turn_id for r in point["recollections"]
                ):
                    continue
                point["recollections"].append(
                    {
                        "turn_id": turn_id,
                        "session_id": source["session_id"],
                        "conversation": conversation_titles.get(source["session_id"], ""),
                        "text": source["label"],
                        "marks": list(source.get("marks", [])),
                    }
                )
                if source["session_id"] not in point["conversations"]:
                    point["conversations"].append(source["session_id"])

    # A subject reached from recollections dated to different years. Deliberately
    # not called a contradiction: reunions that ran from 1977 to 1979 look the
    # same from here as a move two people date differently. The view shows that
    # it happened and hands over the exact words rather than ruling on them.
    divergences = []
    for node in field.nodes.values():
        if node["type"] not in NODE_TYPE_LABELS or node["type"] == "time":
            continue
        by_year: dict[int, list[str]] = {}
        for turn_id in node["recollections"]:
            for year in years_by_turn.get(turn_id, ()):
                by_year.setdefault(year, []).append(turn_id)
        if len(by_year) > 1:
            divergences.append(
                {
                    "id": node["id"],
                    "subject": node["label"],
                    "type": node["type"],
                    "years": sorted(by_year),
                    "by_year": {str(year): turn_ids for year, turn_ids in sorted(by_year.items())},
                }
            )
    divergences.sort(key=lambda d: (-len(d["years"]), d["subject"]))

    ordered_points = [points[year] for year in sorted(points)]
    return {
        "points": ordered_points,
        "undated": sorted(undated, key=lambda x: x["label"]),
        "divergences": divergences,
        "counts": {
            "años": len(ordered_points),
            "recuerdos_fechados": len(years_by_turn),
            "sin_año": len(undated),
            "fechados_de_varias_maneras": len(divergences),
        },
    }
