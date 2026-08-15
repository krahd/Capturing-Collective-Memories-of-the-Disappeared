from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from controller import InterviewMove, guard_interview_move, safe_interview_fallback
from memory_field import build_memory_field, build_timeline, normalise
from state import ORIGIN_MODEL, SessionStore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "evaluation" / "deferred-significance-scenarios.json"
DEFAULT_RESULTS = ROOT / "evaluation" / "results" / "deferred-significance-latest.json"
DEFAULT_REPORT = ROOT / "evaluation" / "results" / "deferred-significance-latest.md"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _node_id(kind: str, label: str) -> str:
    return f"{kind}:{normalise(label)}"


def _add_items(session, turn, items: list[list[str]]) -> None:
    for kind, text in items:
        session.add_derived_item(kind, text, [turn.id], origin=ORIGIN_MODEL)


def run_convergence_case(case: dict[str, Any], root: Path) -> dict[str, Any]:
    store = SessionStore(root / case["id"])
    session_specs = case["sessions"]
    first_spec = session_specs[0]

    first = store.create(first_spec["title"])
    first_turn = first.add_turn("user", first_spec["text"])
    source_hash_before = _hash(first_turn.text)

    field_source_only = build_memory_field([first])
    target_id = _node_id(case["target_kind"], case["target_label"])
    target_before_interpretation = any(
        node["id"] == target_id for node in field_source_only["nodes"]
    )
    recollection_before_interpretation = any(
        node["id"] == f"rec:{first_turn.id}" for node in field_source_only["nodes"]
    )

    _add_items(first, first_turn, first_spec["items"])
    sessions = [first]
    target_conversation_counts: list[int] = []
    shared_counts: list[int] = []

    field = build_memory_field(sessions)
    target = next(node for node in field["nodes"] if node["id"] == target_id)
    target_conversation_counts.append(len(target["conversations"]))
    shared_counts.append(field["counts"]["compartidas"])

    for spec in session_specs[1:]:
        session = store.create(spec["title"])
        turn = session.add_turn("user", spec["text"])
        _add_items(session, turn, spec["items"])
        sessions.append(session)
        field = build_memory_field(sessions)
        target = next(node for node in field["nodes"] if node["id"] == target_id)
        target_conversation_counts.append(len(target["conversations"]))
        shared_counts.append(field["counts"]["compartidas"])

    first_after = next(
        turn for turn in first.turns if turn.id == first_turn.id
    )
    source_hash_after = _hash(first_after.text)

    final_target = next(node for node in field["nodes"] if node["id"] == target_id)
    final_recollection = next(
        node for node in field["nodes"] if node["id"] == f"rec:{first_turn.id}"
    )
    passed = all(
        [
            recollection_before_interpretation,
            not target_before_interpretation,
            target_conversation_counts == [1, 2, 3],
            source_hash_before == source_hash_after,
            final_recollection["label"] == first_spec["text"],
            len(final_target["conversations"]) == 3,
        ]
    )

    return {
        "id": case["id"],
        "pass": passed,
        "target_id": target_id,
        "recollection_exists_before_interpretation": recollection_before_interpretation,
        "target_exists_before_interpretation": target_before_interpretation,
        "target_conversation_counts": target_conversation_counts,
        "shared_entity_counts": shared_counts,
        "source_sha256_before": source_hash_before,
        "source_sha256_after": source_hash_after,
        "source_unchanged": source_hash_before == source_hash_after,
        "final_source_text": final_recollection["label"],
    }


def _make_sessions(store: SessionStore, specs: list[dict[str, Any]]):
    sessions = []
    turns = []
    for spec in specs:
        session = store.create(spec["title"])
        turn = session.add_turn("user", spec["text"])
        _add_items(session, turn, spec["items"])
        sessions.append(session)
        turns.append(turn)
    return sessions, turns


def run_noncollapse_case(case: dict[str, Any], root: Path) -> dict[str, Any]:
    store = SessionStore(root / case["id"])
    sessions, turns = _make_sessions(store, case["sessions"])
    field = build_memory_field(sessions)
    result: dict[str, Any] = {"id": case["id"]}

    if "expected_time_labels" in case:
        observed = sorted(
            node["label"] for node in field["nodes"] if node["type"] == "time"
        )
        expected = sorted(case["expected_time_labels"])
        result.update(
            {
                "pass": observed == expected,
                "expected_time_labels": expected,
                "observed_time_labels": observed,
            }
        )
    elif "expected_undated_labels" in case:
        timeline = build_timeline(sessions)
        observed = sorted(item["label"] for item in timeline["undated"])
        expected = sorted(case["expected_undated_labels"])
        result.update(
            {
                "pass": observed == expected,
                "expected_undated_labels": expected,
                "observed_undated_labels": observed,
            }
        )
    elif "expected_marks" in case:
        recollection = next(
            node for node in field["nodes"] if node["id"] == f"rec:{turns[0].id}"
        )
        observed = sorted(recollection["marks"])
        expected = sorted(case["expected_marks"])
        result.update(
            {
                "pass": observed == expected,
                "expected_marks": expected,
                "observed_marks": observed,
            }
        )
    else:
        raise ValueError(f"Unknown non-collapse case schema: {case['id']}")
    return result


def run_guard_probe() -> list[dict[str, Any]]:
    known = {
        "turn_a": "Había uno al que le decían Tito, que a veces aparecía por casa."
    }
    uncertain = {"turn_u": "Capaz que era él, pero no estoy seguro. De lejos se parecía."}
    cases = [
        {
            "id": "packed-question",
            "known": known,
            "recent": [],
            "candidate": InterviewMove("FOLLOW_UP", "¿Quién era Tito, y dónde vivía?", "turn_a"),
            "expected_guard": "fallback",
        },
        {
            "id": "unsupported-specificity",
            "known": known,
            "recent": [],
            "candidate": InterviewMove("FOLLOW_UP", "¿Era Julio el Tito que mencionás?", "turn_a"),
            "expected_guard": "fallback",
        },
        {
            "id": "generic-acknowledgement",
            "known": known,
            "recent": [],
            "candidate": InterviewMove("ACKNOWLEDGE", "Te sigo.", "turn_a"),
            "expected_guard": "fallback",
        },
        {
            "id": "grounded-acknowledgement",
            "known": known,
            "recent": [],
            "candidate": InterviewMove("ACKNOWLEDGE", "Mencionás a Tito y que aparecía por casa.", "turn_a"),
            "expected_guard": "accepted",
        },
        {
            "id": "minimal-floor-yield",
            "known": known,
            "recent": [],
            "candidate": InterviewMove("INVITE_CONTINUE", "Contame.", "turn_a"),
            "expected_guard": "accepted",
        },
        {
            "id": "single-grounded-probe",
            "known": known,
            "recent": [],
            "candidate": InterviewMove("FOLLOW_UP", "¿Quién era Tito?", "turn_a"),
            "expected_guard": "accepted",
        },
        {
            "id": "uncertainty-hardening",
            "known": uncertain,
            "recent": [],
            "candidate": InterviewMove("ACKNOWLEDGE", "Era él, entonces.", "turn_u"),
            "expected_guard": "fallback",
        },
        {
            "id": "repetitive-backchannel",
            "known": known,
            "recent": ["Ajá."],
            "candidate": InterviewMove("BACKCHANNEL", "Ajá.", "turn_a"),
            "expected_guard": "fallback",
        },
    ]

    results = []
    for case in cases:
        guarded = guard_interview_move(
            case["candidate"], case["known"], case["recent"]
        )
        if guarded:
            observed_guard = "accepted"
            move, utterance = guarded
        else:
            observed_guard = "fallback"
            move, utterance = safe_interview_fallback(case["recent"])
        results.append(
            {
                "id": case["id"],
                "pass": observed_guard == case["expected_guard"],
                "expected_guard": case["expected_guard"],
                "observed_guard": observed_guard,
                "candidate": {
                    "move": case["candidate"].move,
                    "utterance": case["candidate"].utterance,
                },
                "delivered": {"move": move, "utterance": utterance},
            }
        )
    return results


def run(cases_path: Path) -> dict[str, Any]:
    spec = json.loads(cases_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="deferred-significance-") as temp:
        root = Path(temp)
        convergence = [
            run_convergence_case(case, root / "convergence")
            for case in spec["convergence_cases"]
        ]
        noncollapse = [
            run_noncollapse_case(case, root / "noncollapse")
            for case in spec["noncollapse_cases"]
        ]
    guard = run_guard_probe()
    all_results = [*convergence, *noncollapse, *guard]
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_level": 0,
        "scenario_version": spec["version"],
        "scenario_source": str(cases_path.relative_to(ROOT)),
        "claim_boundary": (
            "Mechanical and researcher-authored evidence only. This run verifies implemented "
            "storage/representation/guard properties and the benchmark harness; it does not "
            "measure a language model's interviewing quality, human recollection, participant "
            "experience, or historical truth."
        ),
        "summary": {
            "total_checks": len(all_results),
            "passed": sum(1 for result in all_results if result["pass"]),
            "failed": sum(1 for result in all_results if not result["pass"]),
            "convergence_cases": len(convergence),
            "convergence_passed": sum(1 for result in convergence if result["pass"]),
            "noncollapse_cases": len(noncollapse),
            "noncollapse_passed": sum(1 for result in noncollapse if result["pass"]),
            "guard_cases": len(guard),
            "guard_passed": sum(1 for result in guard if result["pass"]),
        },
        "convergence": convergence,
        "noncollapse": noncollapse,
        "guard": guard,
    }


def markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    lines = [
        "# Deferred-significance experiment result",
        "",
        f"**Created:** {payload['created_at']}",
        f"**Evidence level:** {payload['evidence_level']} (mechanical / researcher-authored)",
        "",
        payload["claim_boundary"],
        "",
        "## Summary",
        "",
        f"- total checks: {s['passed']}/{s['total_checks']} passed",
        f"- convergence: {s['convergence_passed']}/{s['convergence_cases']} passed",
        f"- non-collapse: {s['noncollapse_passed']}/{s['noncollapse_cases']} passed",
        f"- controller guard probes: {s['guard_passed']}/{s['guard_cases']} passed",
        "",
        "## Cross-session convergence",
        "",
        "| Case | Pass | Target conversation counts | Source unchanged |",
        "|---|---:|---|---:|",
    ]
    for result in payload["convergence"]:
        lines.append(
            f"| {result['id']} | {'yes' if result['pass'] else 'NO'} | "
            f"{result['target_conversation_counts']} | "
            f"{'yes' if result['source_unchanged'] else 'NO'} |"
        )
    lines.extend(
        [
            "",
            "## Non-collapse checks",
            "",
            "| Case | Pass |",
            "|---|---:|",
        ]
    )
    for result in payload["noncollapse"]:
        lines.append(f"| {result['id']} | {'yes' if result['pass'] else 'NO'} |")
    lines.extend(
        [
            "",
            "## Controller guard probes",
            "",
            "| Case | Expected | Observed | Pass | Delivered |",
            "|---|---|---|---:|---|",
        ]
    )
    for result in payload["guard"]:
        delivered = result["delivered"]["utterance"].replace("|", "\\|")
        lines.append(
            f"| {result['id']} | {result['expected_guard']} | {result['observed_guard']} | "
            f"{'yes' if result['pass'] else 'NO'} | {delivered} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "A passing convergence case means the participant recollection exists before any derived target exists, later sessions can make an exact-label relation visible across conversations, and the original source text remains byte-for-byte unchanged. A passing non-collapse case means the tested ambiguity or contradiction remains represented rather than being silently normalised away. A passing guard probe means the deterministic controller accepted or rejected a researcher-authored candidate intervention as specified.",
            "",
            "These checks do not establish that the model will choose the desired move. That is a Level 1 model experiment and must be run against a configured model using the companion protocol.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the reproducible Level-0 deferred-significance experiment."
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    payload = run(args.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], sort_keys=True))
    print(args.output)
    print(args.report)
    return 1 if payload["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
