import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_research_scenarios_are_machine_readable_and_complete():
    scenarios = json.loads(
        (ROOT / "evaluation" / "scenarios.json").read_text(encoding="utf-8")
    )
    assert len(scenarios) >= 10
    assert len({scenario["id"] for scenario in scenarios}) == len(scenarios)
    assert all(scenario["turns"] for scenario in scenarios)
    # Memories contain other people's instructions. The scope controller has to
    # be exercised against reported speech, not only against real controls.
    assert "reported-control" in {scenario["id"] for scenario in scenarios}
    assert all(
        turn["role"] in {"user", "assistant"} and isinstance(turn["text"], str)
        for scenario in scenarios
        for turn in scenario["turns"]
    )


def test_live_scenario_runner_starts_without_model_configuration():
    result = subprocess.run(
        [sys.executable, "scripts/run_live_scenarios.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Uruguayan-Spanish" in result.stdout


def test_rhythm_scenarios_are_multi_turn_and_runner_is_executable():
    scenarios = json.loads(
        (ROOT / "evaluation" / "rhythm-scenarios.json").read_text(encoding="utf-8")
    )
    assert len(scenarios) >= 3
    assert all(len(scenario["participant_turns"]) >= 3 for scenario in scenarios)

    result = subprocess.run(
        [sys.executable, "scripts/run_rhythm_scenarios.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "multi-turn conversational-rhythm" in result.stdout


def test_target_machine_wrapper_exposes_evidence_arguments():
    result = subprocess.run(
        [sys.executable, "scripts/run_target_machine_evaluation.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "target-machine evidence bundle" in result.stdout
    assert "--provider" in result.stdout
    assert "--chat-url" in result.stdout
    assert "--benchmark-base-url" in result.stdout
