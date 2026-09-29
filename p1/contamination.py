"""Deterministic Level-0 harness for recursive capture contamination.

This module does not simulate participant psychology and does not establish
that a particular LLM will contaminate a conversation.  It mechanically tests
whether the architecture exposes prior-session material to a later capture
context, whether that exposure preserves provenance, and whether model output
can silently enter the participant-source layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

STRICT_ISOLATION = "C0_strict_capture_isolation"
NAIVE_MEMORY = "C1_naive_cross_session_memory"
SOURCE_BOUNDED = "C2_source_bounded_archive_retrieval"
CONDITIONS = (STRICT_ISOLATION, NAIVE_MEMORY, SOURCE_BOUNDED)


@dataclass(frozen=True)
class Provenance:
    source_session_id: str
    source_kind: str
    source_object_id: str


@dataclass(frozen=True)
class ArchiveItem:
    object_id: str
    text: str
    source_session_id: str
    source_kind: str = "participant_source"

    @property
    def provenance(self) -> Provenance:
        return Provenance(
            source_session_id=self.source_session_id,
            source_kind=self.source_kind,
            source_object_id=self.object_id,
        )


@dataclass(frozen=True)
class ContextItem:
    text: str
    provenance: Provenance | None
    role: str


@dataclass
class SessionRepresentation:
    session_id: str
    participant_source: list[str] = field(default_factory=list)
    mediation: list[dict] = field(default_factory=list)
    interpretation: list[dict] = field(default_factory=list)

    def add_participant_source(self, text: str) -> None:
        self.participant_source.append(text)

    def add_model_mediation(
        self,
        text: str,
        context: Iterable[ContextItem],
    ) -> None:
        self.mediation.append(
            {
                "actor": "model",
                "text": text,
                "context_provenance": [
                    {
                        "source_session_id": item.provenance.source_session_id,
                        "source_kind": item.provenance.source_kind,
                        "source_object_id": item.provenance.source_object_id,
                    }
                    for item in context
                    if item.provenance is not None
                ],
            }
        )


class CapturePolicy:
    """Construct only the context allowed by one frozen experimental condition."""

    def __init__(self, condition: str):
        if condition not in CONDITIONS:
            raise ValueError(f"Unknown condition: {condition}")
        self.condition = condition

    def context(
        self,
        session_id: str,
        current_source: list[str],
        archive: list[ArchiveItem],
        retrieval_object_ids: set[str] | None = None,
    ) -> list[ContextItem]:
        items = [
            ContextItem(
                text=text,
                provenance=Provenance(session_id, "participant_source", f"{session_id}:turn:{i}"),
                role="current_participant_source",
            )
            for i, text in enumerate(current_source)
        ]

        if self.condition == STRICT_ISOLATION:
            return items

        if self.condition == NAIVE_MEMORY:
            # Deliberately unsafe comparator: archive text is flattened before it
            # reaches capture.  The source relationship is no longer available
            # to the conversational layer.
            items.extend(
                ContextItem(text=record.text, provenance=None, role="archive_memory")
                for record in archive
            )
            return items

        selected = retrieval_object_ids or set()
        items.extend(
            ContextItem(
                text=record.text,
                provenance=record.provenance,
                role="source_bounded_archive_retrieval",
            )
            for record in archive
            if record.object_id in selected and record.source_kind == "participant_source"
        )
        return items


class DeterministicLeakProbe:
    """Expose condition wiring without claiming to model natural conversation."""

    def respond(self, context: list[ContextItem], target: str) -> str:
        folded = "\n".join(item.text.casefold() for item in context)
        if target.casefold() in folded:
            return f"Could you say more about {target}?"
        return "What else would you like to record about that?"


def _target_in(texts: Iterable[str], target: str) -> bool:
    needle = target.casefold()
    return any(needle in text.casefold() for text in texts)


def run_case(case: dict, condition: str) -> dict:
    target = case["target"]
    session_a = case.get("session_a_id", f"{case['id']}:A")
    session_b = case.get("session_b_id", f"{case['id']}:B")
    a_text = case["session_a_text"]
    b_text = case["session_b_text"]
    if target.casefold() in b_text.casefold():
        raise ValueError(f"Case {case['id']} violates invariant: target is already in B")

    archive_item = ArchiveItem(
        object_id=f"{case['id']}:source:A",
        text=a_text,
        source_session_id=session_a,
    )
    archive = [archive_item]
    retrieval = {archive_item.object_id} if condition == SOURCE_BOUNDED else set()

    representation = SessionRepresentation(session_id=session_b)
    representation.add_participant_source(b_text)
    context = CapturePolicy(condition).context(
        session_id=session_b,
        current_source=representation.participant_source,
        archive=archive,
        retrieval_object_ids=retrieval,
    )
    output = DeterministicLeakProbe().respond(context, target)
    representation.add_model_mediation(output, context)

    target_introduced = target.casefold() in output.casefold()
    evidence_contaminated = _target_in(representation.participant_source, target)
    prior_context = [item for item in context if item.role != "current_participant_source"]
    target_prior_context = [item for item in prior_context if target.casefold() in item.text.casefold()]
    attribution_preserved = all(item.provenance is not None for item in target_prior_context)
    if not target_prior_context:
        attribution_preserved = True

    return {
        "case_id": case["id"],
        "condition": condition,
        "target": target,
        "target_introduced": target_introduced,
        "leadingness_probe": target_introduced,
        "evidence_contaminated": evidence_contaminated,
        "attribution_preserved": attribution_preserved,
        "prior_session_items_visible": len(prior_context),
        "target_prior_items_visible": len(target_prior_context),
        "participant_source": list(representation.participant_source),
        "model_output": output,
        "mediation": representation.mediation,
    }


def run_suite(cases: list[dict]) -> dict:
    results = [run_case(case, condition) for case in cases for condition in CONDITIONS]
    summary = {}
    for condition in CONDITIONS:
        rows = [row for row in results if row["condition"] == condition]
        summary[condition] = {
            "cases": len(rows),
            "target_introductions": sum(row["target_introduced"] for row in rows),
            "evidence_contaminations": sum(row["evidence_contaminated"] for row in rows),
            "attribution_failures": sum(not row["attribution_preserved"] for row in rows),
            "prior_session_items_visible": sum(row["prior_session_items_visible"] for row in rows),
        }
    return {
        "evidence_level": 0,
        "evidence_scope": "deterministic architecture/invariant evidence only; not an LLM or participant result",
        "conditions": list(CONDITIONS),
        "summary": summary,
        "results": results,
    }
