from __future__ import annotations

from scripts.run_rtca_experiment_b2 import _parse_candidate, summarise_model


def _item(*, source: str, accepted_attempt: int | None, attempts: int, utterance: str, packed: bool = False):
    return {
        "delivery_source": source,
        "accepted_attempt": accepted_attempt,
        "attempt_count": attempts,
        "delivered_utterance": utterance,
        "automatic_screen": {
            "question_packing": packed,
            "over_specification": False,
            "premature_redirection": False,
            "floor_closure": False,
            "generic_acknowledgement": False,
            "uncertainty_hardened": False,
        },
    }


def test_parse_candidate_accepts_strict_json() -> None:
    parsed, move, utterance = _parse_candidate('{"move":"INVITE_CONTINUE","utterance":"Contame más."}')
    assert parsed["move"] == "INVITE_CONTINUE"
    assert move == "INVITE_CONTINUE"
    assert utterance == "Contame más."


def test_b2_summary_separates_first_attempt_repair_and_fallback() -> None:
    items = [
        _item(source="model", accepted_attempt=1, attempts=1, utterance="Seguí."),
        _item(source="model", accepted_attempt=2, attempts=2, utterance="¿Qué recordás de eso?"),
        _item(source="deterministic-fallback", accepted_attempt=None, attempts=3, utterance="Contame."),
    ]
    summary = summarise_model(items)
    assert summary["n"] == 3
    assert summary["accepted_on_first_attempt"] == 1
    assert summary["accepted_after_repair"] == 1
    assert summary["final_fallback_count"] == 1
    assert summary["final_fallback_rate"] == 0.3333
    assert summary["max_attempt_count"] == 3
    assert summary["delivered_unique_utterances"] == 3
