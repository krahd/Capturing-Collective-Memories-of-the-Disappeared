import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_research_scenarios_are_machine_readable_and_complete():
    scenarios = json.loads(
        (ROOT / "evaluation" / "scenarios.json").read_text(encoding="utf-8")
    )
    assert len(scenarios) == 10
    assert len({scenario["id"] for scenario in scenarios}) == 10
    assert all(scenario["turns"] for scenario in scenarios)
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
