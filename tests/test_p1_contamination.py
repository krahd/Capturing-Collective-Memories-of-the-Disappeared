import json
from pathlib import Path
import subprocess
import sys

import pytest

from p1.contamination import (
    NAIVE_MEMORY,
    SOURCE_BOUNDED,
    STRICT_ISOLATION,
    run_case,
    run_suite,
)

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evaluation" / "p1-contamination-scenarios.json"


def cases():
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]


def test_scenarios_keep_target_out_of_session_b():
    for case in cases():
        assert case["target"].casefold() not in case["session_b_text"].casefold()


def test_condition_wiring_is_mechanically_distinct():
    payload = run_suite(cases())
    n = len(cases())
    c0 = payload["summary"][STRICT_ISOLATION]
    c1 = payload["summary"][NAIVE_MEMORY]
    c2 = payload["summary"][SOURCE_BOUNDED]

    assert payload["evidence_level"] == 0
    assert c0["target_introductions"] == 0
    assert c0["prior_session_items_visible"] == 0

    assert c1["target_introductions"] == n
    assert c1["attribution_failures"] == n

    assert c2["target_introductions"] == n
    assert c2["attribution_failures"] == 0

    # No condition is allowed to convert model mediation into participant evidence.
    assert c0["evidence_contaminations"] == 0
    assert c1["evidence_contaminations"] == 0
    assert c2["evidence_contaminations"] == 0


def test_source_bounded_context_carries_explicit_provenance():
    row = run_case(cases()[0], SOURCE_BOUNDED)
    refs = row["mediation"][0]["context_provenance"]
    prior = [ref for ref in refs if ref["source_session_id"].endswith(":A")]
    assert len(prior) == 1
    assert prior[0]["source_kind"] == "participant_source"


def test_naive_memory_deliberately_loses_prior_attribution():
    row = run_case(cases()[0], NAIVE_MEMORY)
    assert row["target_introduced"] is True
    assert row["attribution_preserved"] is False


def test_case_rejects_target_already_present_in_b():
    bad = dict(cases()[0])
    bad["session_b_text"] += " " + bad["target"]
    with pytest.raises(ValueError, match="target is already in B"):
        run_case(bad, STRICT_ISOLATION)


def test_runner_writes_auditable_level_zero_outputs(tmp_path):
    output = tmp_path / "result.json"
    report = tmp_path / "result.md"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_p1_contamination_experiment",
            "--output",
            str(output),
            "--report",
            str(report),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["evidence_level"] == 0
    text = report.read_text(encoding="utf-8")
    assert "not an LLM performance result" in text
    assert "Level-1" in text
