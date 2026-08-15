from __future__ import annotations

import json
from pathlib import Path

from scripts.evaluate_policy_experiment import evaluate, evaluate_item, question_units


def test_question_units_detects_packing():
    assert question_units("¿Quién era Tito?") == 1
    assert question_units("¿Quién era Tito y dónde vivía?") >= 2
    assert question_units("Contame.") == 0


def test_evaluator_flags_basic_failure_mechanisms():
    base = {
        "scenario_id": "x",
        "policy_id": "p",
        "policy_label": "P",
        "repetition": 1,
        "session_a": "Capaz que Tito venía por casa.",
        "withheld_later_sessions": ["Tito vivía por La Teja."],
        "guard_outcome": "not-applicable",
        "error": None,
    }
    packed = evaluate_item({**base, "delivered_move": "FOLLOW_UP", "delivered_utterance": "¿Quién era Tito y dónde vivía?"})
    assert packed["automatic_screen"]["question_packing"] is True

    novel = evaluate_item({**base, "delivered_move": "FOLLOW_UP", "delivered_utterance": "¿Era Julio ese Tito?"})
    assert novel["automatic_screen"]["over_specification"] is True

    safe = evaluate_item({**base, "delivered_move": "INVITE_CONTINUE", "delivered_utterance": "Contame."})
    assert safe["automatic_screen"]["possibility_preserved"] is True


def test_bundle_evaluation_round_trip(tmp_path: Path):
    payload = {
        "model": "test-model",
        "sampling": {"repetitions": 1},
        "results": [
            {
                "scenario_id": "x",
                "policy_id": "deferred-significance",
                "policy_label": "Deferred significance",
                "repetition": 1,
                "session_a": "No me acuerdo bien de Tito.",
                "withheld_later_sessions": ["Tito vivía por La Teja."],
                "delivered_move": "INVITE_CONTINUE",
                "delivered_utterance": "Contame.",
                "guard_outcome": "accepted",
                "error": None,
            }
        ],
    }
    source = tmp_path / "experiment.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    result = evaluate(source)
    assert result["by_policy"]["deferred-significance"]["valid_n"] == 1
    assert result["by_policy"]["deferred-significance"]["possibility_preserved"] == 1
