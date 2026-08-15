from pathlib import Path
import subprocess
import sys

from scripts.run_deferred_significance_experiment import DEFAULT_CASES, run


ROOT = Path(__file__).resolve().parents[1]


def test_deferred_significance_experiment_passes_all_level_zero_checks():
    payload = run(DEFAULT_CASES)
    assert payload["evidence_level"] == 0
    assert payload["summary"]["failed"] == 0
    assert payload["summary"]["convergence_passed"] == payload["summary"]["convergence_cases"]
    assert payload["summary"]["noncollapse_passed"] == payload["summary"]["noncollapse_cases"]
    assert payload["summary"]["guard_passed"] == payload["summary"]["guard_cases"]


def test_deferred_significance_runner_writes_auditable_outputs(tmp_path):
    output = tmp_path / "result.json"
    report = tmp_path / "result.md"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_deferred_significance_experiment.py",
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
    assert output.exists()
    assert report.exists()
    assert "Mechanical and researcher-authored evidence only" in output.read_text(encoding="utf-8")
    assert "Level 1 model experiment" in report.read_text(encoding="utf-8")
