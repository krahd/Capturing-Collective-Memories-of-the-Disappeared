from __future__ import annotations

import json
from pathlib import Path

from scripts.run_rtca_experiments import _matrix_summary


ROOT = Path(__file__).resolve().parents[1]


def test_frozen_model_matrix_has_primary_scale_and_cross_family_controls() -> None:
    payload = json.loads((ROOT / "evaluation" / "model-robustness-matrix.json").read_text(encoding="utf-8"))
    models = payload["models"]
    assert len(models) == 3
    assert {item["role"] for item in models} == {"primary", "scale-control", "cross-family-control"}
    assert len({item["ollama_model"] for item in models}) == 3
    assert all(item["repetitions"] >= 5 for item in models)
    assert payload["provider"] == "ollama"


def test_matrix_summary_keeps_model_and_policy_axes_separate() -> None:
    bucket = {
        "policy_label": "Deferred",
        "n": 5,
        "valid_n": 5,
        "errors": 0,
        "possibility_preserved": 4,
        "premature_redirection": 1,
        "over_specification": 0,
        "question_packing": 0,
        "floor_closure": 0,
        "generic_acknowledgement": 1,
        "uncertainty_hardened": 0,
        "possibility_preserved_rate": 0.8,
    }
    runs = [
        {
            "model_spec": {"id": "m1", "role": "primary", "family": "A", "ollama_model": "a:1"},
            "automatic_by_policy": {"deferred": dict(bucket)},
        },
        {
            "model_spec": {"id": "m2", "role": "cross-family-control", "family": "B", "ollama_model": "b:1"},
            "automatic_by_policy": {"deferred": dict(bucket)},
        },
    ]
    result = _matrix_summary(runs)
    assert result["total_valid_decisions"] == 10
    assert result["by_model"]["m1"]["by_policy"]["deferred"]["possibility_preserved"] == 4
    assert result["across_models_by_policy"]["deferred"]["possibility_preserved"] == 8
    assert result["across_models_by_policy"]["deferred"]["possibility_preserved_rate"] == 0.8
