from pathlib import Path
import json

from scripts.analyse_rtca_guard_effects import analyse_model


def test_guard_effect_analysis_detects_fallback_collapse(tmp_path: Path) -> None:
    path = tmp_path / "experiment-b.json"
    payload = {
        "model": "test",
        "results": [
            {
                "scenario_id": "a", "policy_id": "deferred-significance", "repetition": 1,
                "parsed_model_output": {"move": "ACKNOWLEDGE", "utterance": "Sí, Tito."},
                "guard_outcome": "fallback", "delivered_move": "INVITE_CONTINUE", "delivered_utterance": "Contame.",
            },
            {
                "scenario_id": "b", "policy_id": "deferred-significance", "repetition": 1,
                "parsed_model_output": {"move": "FOLLOW_UP", "utterance": "¿Quién era?"},
                "guard_outcome": "fallback", "delivered_move": "INVITE_CONTINUE", "delivered_utterance": "Contame.",
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = analyse_model(path)["policies"]["deferred-significance"]
    assert result["guard_fallback_rate"] == 1.0
    assert result["raw_delivered_replacement_rate"] == 1.0
    assert result["raw_unique_utterances"] == 2
    assert result["delivered_unique_utterances"] == 1
    assert result["top_delivered_utterance_rate"] == 1.0
    assert result["delivered_entropy_bits"] == 0.0
