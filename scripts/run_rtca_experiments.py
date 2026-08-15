from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_policy_experiment import evaluate, markdown, summarise_adjudication, write_review_csv
from scripts.run_policy_experiment import run as run_policy_experiment


DEFAULT_RESULTS_DIR = ROOT / "evaluation" / "results"
DEFAULT_SCENARIOS = ROOT / "evaluation" / "deferred-significance-scenarios.json"
DEFAULT_POLICIES = ROOT / "evaluation" / "experiment-b-policies.json"


def _run_level0(output_dir: Path) -> dict[str, Any]:
    json_path = output_dir / "level0.json"
    report_path = output_dir / "level0.md"
    command = [sys.executable, "-m", "scripts.run_deferred_significance_experiment", "--output", str(json_path), "--report", str(report_path)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {"command": command, "returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "json": str(json_path), "report": str(report_path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Single entry point for RTCA Experiment B generation, screening and final manual-adjudication summary.")
    parser.add_argument("--chat-url", default=os.getenv("LLM_API_URL"), help="OpenAI-compatible /v1/chat/completions URL")
    parser.add_argument("--model", default=os.getenv("LLM_MODEL"), help="Exact model identifier")
    parser.add_argument("--api-key", default=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--repetitions", type=int, default=5, help="Repetitions per scenario × policy; 5 gives 75 decisions")
    parser.add_argument("--temperature", type=float, default=float(os.getenv("LLM_TEMPERATURE", "0.7")))
    parser.add_argument("--top-p", type=float, default=float(os.getenv("LLM_TOP_P", "0.8")))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("LLM_MAX_TOKENS", "256")))
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--policies", type=Path, default=DEFAULT_POLICIES)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--skip-level0", action="store_true")
    parser.add_argument("--summarise-review", type=Path, default=None, help="Summarise a completed manual-review CSV instead of generating new model outputs")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.summarise_review is not None:
        payload = summarise_adjudication(args.summarise_review)
        output = args.summarise_review.with_name(f"{args.summarise_review.stem}-summary.json")
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(output)
        print(json.dumps(payload["by_policy"], ensure_ascii=False, sort_keys=True))
        return 2 if payload["incomplete_rows"] else 0

    if not args.chat_url:
        raise SystemExit("Missing --chat-url or LLM_API_URL")
    if not args.model:
        raise SystemExit("Missing --model or LLM_MODEL")
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be >= 1")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir or DEFAULT_RESULTS_DIR / f"rtca-experiments-{stamp}"
    output_dir.mkdir(parents=True, exist_ok=False)

    level0 = None if args.skip_level0 else _run_level0(output_dir)
    if level0 is not None and level0["returncode"] != 0:
        manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "status": "failed-level0", "level0": level0}
        (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(output_dir)
        return 1

    experiment_path = output_dir / "experiment-b.json"
    experiment = asyncio.run(run_policy_experiment(
        scenarios_path=args.scenarios,
        policies_path=args.policies,
        chat_url=args.chat_url,
        api_key=args.api_key,
        model=args.model,
        repetitions=args.repetitions,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
    ))
    experiment_path.write_text(json.dumps(experiment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    evaluation = evaluate(experiment_path)
    evaluation_json = output_dir / "experiment-b-evaluation.json"
    evaluation_md = output_dir / "experiment-b-evaluation.md"
    review_csv = output_dir / "experiment-b-manual-review.csv"
    evaluation_json.write_text(json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    evaluation_md.write_text(markdown(evaluation), encoding="utf-8")
    write_review_csv(evaluation["results"], review_csv)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if experiment["counts"]["failed_requests"] == 0 else "complete-with-request-errors",
        "single_entry_point": "python -m scripts.run_rtca_experiments",
        "final_adjudication_command": f"python -m scripts.run_rtca_experiments --summarise-review {review_csv}",
        "model": args.model,
        "chat_url": args.chat_url,
        "sampling": experiment["sampling"],
        "level0": level0,
        "experiment_b": {
            "raw": str(experiment_path),
            "evaluation_json": str(evaluation_json),
            "evaluation_report": str(evaluation_md),
            "manual_review_csv": str(review_csv),
            "counts": experiment["counts"],
            "automatic_by_policy": evaluation["by_policy"],
        },
        "claim_boundary": "The automatic evaluation is a conservative screen, not final adjudication. Complete the manual-review CSV before using subtle branch-closure, contamination, or facilitation claims in the manuscript. No participant or false-memory outcome is measured.",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(output_dir)
    print(json.dumps(experiment["counts"], sort_keys=True))
    for policy, summary in evaluation["by_policy"].items():
        print(f"{policy}: {summary['possibility_preserved']}/{summary['valid_n']} automatic preserve")
    return 1 if experiment["counts"]["failed_requests"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
