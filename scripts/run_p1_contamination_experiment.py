"""Run the deterministic P1 recursive-contamination qualification harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from p1.contamination import run_suite

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "evaluation" / "p1-contamination-scenarios.json"
DEFAULT_OUTPUT = ROOT / "evaluation" / "results" / "p1-contamination-level0-2026-09-29.json"
DEFAULT_REPORT = ROOT / "evaluation" / "results" / "p1-contamination-level0-2026-09-29.md"


def load_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def render_report(payload: dict) -> str:
    lines = [
        "# P1 recursive-contamination harness — Level 0",
        "",
        "**Evidence class:** deterministic architecture/invariant evidence only.",
        "",
        "This is not an LLM performance result and not participant evidence.  It verifies that the experimental conditions and provenance boundaries are mechanically distinguishable before model runs are attempted.",
        "",
        "## Summary",
        "",
        "| Condition | Cases | Target introductions | Source contaminations | Attribution failures | Prior-session items visible |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for condition, stats in payload["summary"].items():
        lines.append(
            f"| {condition} | {stats['cases']} | {stats['target_introductions']} | "
            f"{stats['evidence_contaminations']} | {stats['attribution_failures']} | "
            f"{stats['prior_session_items_visible']} |"
        )
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "Expected Level-0 behaviour is structural: C0 exposes no prior-session material; C1 exposes flattened prior material and therefore cannot preserve its provenance at the capture boundary; C2 exposes only explicitly selected participant-source material with provenance.  In all conditions, model mediation must remain outside the participant-source layer.",
        "",
        "A later Level-1 experiment must replace the deterministic leak probe with fixed, logged model calls and score target introduction/leadingness from actual outputs.  These Level-0 counts must not be reported as evidence that an LLM will or will not contaminate capture.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="P1 Level-0 recursive-contamination qualification harness")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    payload = run_suite(load_cases(args.cases))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(render_report(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
