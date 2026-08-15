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

from scripts.ensure_rtca_models import prepare as prepare_models
from scripts.evaluate_policy_experiment import evaluate, markdown, summarise_adjudication, write_review_csv
from scripts.run_policy_experiment import run as run_policy_experiment


DEFAULT_RESULTS_DIR = ROOT / "evaluation" / "results"
DEFAULT_SCENARIOS = ROOT / "evaluation" / "deferred-significance-scenarios.json"
DEFAULT_POLICIES = ROOT / "evaluation" / "experiment-b-policies.json"
DEFAULT_MATRIX = ROOT / "evaluation" / "model-robustness-matrix.json"


def _run_level0(output_dir: Path) -> dict[str, Any]:
    json_path = output_dir / "level0.json"
    report_path = output_dir / "level0.md"
    command = [sys.executable, "-m", "scripts.run_deferred_significance_experiment", "--output", str(json_path), "--report", str(report_path)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {"command": command, "returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "json": str(json_path), "report": str(report_path)}


def _runtime_benchmark(model: str, output: Path, repetitions: int = 3) -> dict[str, Any]:
    command = [
        "modelito-benchmark-local", "--provider", "ollama", "--model", model,
        "--repetitions", str(repetitions), "--json", "--output", str(output),
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {"command": command, "returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "output": str(output)}


def _matrix_summary(model_runs: list[dict[str, Any]]) -> dict[str, Any]:
    by_model: dict[str, Any] = {}
    by_policy: dict[str, dict[str, int]] = {}
    total = 0
    for run in model_runs:
        model_id = run["model_spec"]["id"]
        auto = run["automatic_by_policy"]
        by_model[model_id] = {
            "role": run["model_spec"]["role"],
            "family": run["model_spec"]["family"],
            "ollama_model": run["model_spec"]["ollama_model"],
            "by_policy": auto,
        }
        for policy_id, bucket in auto.items():
            aggregate = by_policy.setdefault(policy_id, {"valid_n": 0, "possibility_preserved": 0, "premature_redirection": 0, "over_specification": 0, "question_packing": 0, "floor_closure": 0, "generic_acknowledgement": 0, "uncertainty_hardened": 0})
            for key in aggregate:
                aggregate[key] += int(bucket.get(key, 0))
            total += int(bucket.get("valid_n", 0))
    for bucket in by_policy.values():
        valid = bucket["valid_n"]
        bucket["possibility_preserved_rate"] = round(bucket["possibility_preserved"] / valid, 4) if valid else None
    return {"total_valid_decisions": total, "by_model": by_model, "across_models_by_policy": by_policy}


def _matrix_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# RTCA multi-model automatic screening",
        "",
        "This is a conservative automatic screen of researcher-authored model outputs. It is not final adjudication and does not measure human memory.",
        "",
        "| Model | Role | Policy | Valid n | Preserve | Redirection | Over-specification | Packed | Floor closure | Generic ack | Hardened uncertainty |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model_id, model in payload["by_model"].items():
        for policy_id, bucket in model["by_policy"].items():
            lines.append(
                f"| {model_id} | {model['role']} | {policy_id} | {bucket['valid_n']} | {bucket['possibility_preserved']}/{bucket['valid_n']} | "
                f"{bucket['premature_redirection']} | {bucket['over_specification']} | {bucket['question_packing']} | {bucket['floor_closure']} | "
                f"{bucket['generic_acknowledgement']} | {bucket['uncertainty_hardened']} |"
            )
    lines.extend(["", "## Across-model policy totals", "", "| Policy | Valid n | Preserve | Rate |", "|---|---:|---:|---:|"])
    for policy_id, bucket in payload["across_models_by_policy"].items():
        lines.append(f"| {policy_id} | {bucket['valid_n']} | {bucket['possibility_preserved']} | {bucket['possibility_preserved_rate']} |")
    return "\n".join(lines) + "\n"


def _summarise_matrix_reviews(root: Path) -> dict[str, Any]:
    models: dict[str, Any] = {}
    incomplete = 0
    for review in sorted(root.glob("models/*/experiment-b-manual-review.csv")):
        model_id = review.parent.name
        summary = summarise_adjudication(review)
        models[model_id] = summary
        incomplete += int(summary.get("incomplete_rows", 0))
    if not models:
        raise SystemExit(f"No model review CSVs found under {root / 'models'}")
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(root),
        "incomplete_rows": incomplete,
        "by_model": models,
        "claim_boundary": "Manual adjudication of researcher-authored model outputs only; no participant or false-memory outcome is measured.",
    }


def _run_one_model(
    *,
    model_spec: dict[str, Any],
    output_dir: Path,
    scenarios: Path,
    policies: Path,
    chat_url: str,
    api_key: str | None,
    temperature: float,
    top_p: float,
    max_tokens: int,
    default_repetitions: int,
    runtime_benchmark: bool,
) -> dict[str, Any]:
    model_dir = output_dir / "models" / model_spec["id"]
    model_dir.mkdir(parents=True, exist_ok=False)
    repetitions = int(model_spec.get("repetitions", default_repetitions))
    model = model_spec["ollama_model"]
    experiment_path = model_dir / "experiment-b.json"
    experiment = asyncio.run(run_policy_experiment(
        scenarios_path=scenarios,
        policies_path=policies,
        chat_url=chat_url,
        api_key=api_key,
        model=model,
        repetitions=repetitions,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    ))
    experiment["model_spec"] = model_spec
    experiment_path.write_text(json.dumps(experiment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    evaluation = evaluate(experiment_path)
    evaluation_json = model_dir / "experiment-b-evaluation.json"
    evaluation_md = model_dir / "experiment-b-evaluation.md"
    review_csv = model_dir / "experiment-b-manual-review.csv"
    evaluation_json.write_text(json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    evaluation_md.write_text(markdown(evaluation), encoding="utf-8")
    write_review_csv(evaluation["results"], review_csv)

    benchmark = None
    if runtime_benchmark:
        benchmark = _runtime_benchmark(model, model_dir / "runtime-benchmark.json")

    return {
        "model_spec": model_spec,
        "counts": experiment["counts"],
        "raw": str(experiment_path),
        "evaluation_json": str(evaluation_json),
        "evaluation_report": str(evaluation_md),
        "manual_review_csv": str(review_csv),
        "manual_summary_command": f"python -m scripts.run_rtca_experiments --summarise-review '{review_csv}'",
        "automatic_by_policy": evaluation["by_policy"],
        "runtime_benchmark": benchmark,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Single entry point for RTCA Level-0, multi-model policy comparison, runtime evidence, screening and manual-adjudication summaries.")
    parser.add_argument("--model-matrix", type=Path, default=DEFAULT_MATRIX, help="Frozen Ollama model matrix; default runs primary, scale-control and cross-family models")
    parser.add_argument("--model", default=None, help="Optional single Ollama model override instead of the matrix")
    parser.add_argument("--chat-url", default=os.getenv("LLM_API_URL"), help="Override OpenAI-compatible /v1/chat/completions URL")
    parser.add_argument("--api-key", default=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=float(os.getenv("LLM_TEMPERATURE", "0.7")))
    parser.add_argument("--top-p", type=float, default=float(os.getenv("LLM_TOP_P", "0.8")))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("LLM_MAX_TOKENS", "256")))
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--policies", type=Path, default=DEFAULT_POLICIES)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--skip-level0", action="store_true")
    parser.add_argument("--no-prepare", action="store_true", help="Do not install Modelito or pull missing Ollama models")
    parser.add_argument("--no-runtime-benchmark", action="store_true")
    parser.add_argument("--summarise-review", type=Path, default=None, help="Summarise one completed manual-review CSV")
    parser.add_argument("--summarise-matrix", type=Path, default=None, help="Summarise all completed model review CSVs in an existing result directory")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.summarise_review is not None:
        payload = summarise_adjudication(args.summarise_review)
        output = args.summarise_review.with_name(f"{args.summarise_review.stem}-summary.json")
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(output)
        return 2 if payload["incomplete_rows"] else 0

    if args.summarise_matrix is not None:
        payload = _summarise_matrix_reviews(args.summarise_matrix)
        output = args.summarise_matrix / "manual-matrix-summary.json"
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(output)
        return 2 if payload["incomplete_rows"] else 0

    if args.repetitions < 1:
        raise SystemExit("--repetitions must be >= 1")

    matrix = json.loads(args.model_matrix.read_text(encoding="utf-8"))
    if args.model:
        model_specs = [{"id": "single-model", "role": "single-model", "family": "unspecified", "ollama_model": args.model, "source_model": args.model, "representation": "caller-specified", "repetitions": args.repetitions}]
    else:
        model_specs = matrix["models"]
    chat_url = args.chat_url or matrix.get("chat_url")
    if not chat_url:
        raise SystemExit("No chat URL supplied and none is present in the model matrix")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir or DEFAULT_RESULTS_DIR / f"rtca-model-matrix-{stamp}"
    output_dir.mkdir(parents=True, exist_ok=False)

    preparation = None
    if not args.no_prepare and not args.model:
        preparation = prepare_models(args.model_matrix, install_modelito=True, pull_models=True)
    elif not args.no_prepare and args.model:
        raise SystemExit("Automatic preparation requires the frozen model matrix. Use the matrix or pass --no-prepare for a custom model.")

    level0 = None if args.skip_level0 else _run_level0(output_dir)
    if level0 is not None and level0["returncode"] != 0:
        manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "status": "failed-level0", "preparation": preparation, "level0": level0}
        (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(output_dir)
        return 1

    model_runs = []
    for spec in model_specs:
        model_runs.append(_run_one_model(
            model_spec=spec,
            output_dir=output_dir,
            scenarios=args.scenarios,
            policies=args.policies,
            chat_url=chat_url,
            api_key=args.api_key,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            default_repetitions=args.repetitions,
            runtime_benchmark=not args.no_runtime_benchmark,
        ))

    matrix_summary = _matrix_summary(model_runs)
    (output_dir / "automatic-matrix-summary.json").write_text(json.dumps(matrix_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "automatic-matrix-summary.md").write_text(_matrix_markdown(matrix_summary), encoding="utf-8")

    failed_requests = sum(int(run["counts"]["failed_requests"]) for run in model_runs)
    failed_benchmarks = sum(1 for run in model_runs if run["runtime_benchmark"] is not None and run["runtime_benchmark"]["returncode"] != 0)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if failed_requests == 0 and failed_benchmarks == 0 else "complete-with-errors",
        "single_entry_point": "python -m scripts.run_rtca_experiments",
        "model_matrix": str(args.model_matrix),
        "chat_url": chat_url,
        "sampling": {"temperature": args.temperature, "top_p": args.top_p, "max_tokens": args.max_tokens},
        "preparation": preparation,
        "level0": level0,
        "model_runs": model_runs,
        "planned_decisions": sum(int(run["counts"]["planned_decisions"]) for run in model_runs),
        "failed_requests": failed_requests,
        "failed_runtime_benchmarks": failed_benchmarks,
        "automatic_matrix_summary": str(output_dir / "automatic-matrix-summary.json"),
        "final_matrix_adjudication_command": f"python -m scripts.run_rtca_experiments --summarise-matrix '{output_dir}'",
        "claim_boundary": "The model matrix tests policy compliance and robustness across scale/family under one serving stack. Automatic screens and Modelito runtime evidence remain separate. Manual adjudication is required before subtle interaction claims. No participant or false-memory outcome is measured.",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(output_dir)
    print(f"planned decisions: {manifest['planned_decisions']}")
    for run in model_runs:
        print(f"{run['model_spec']['id']}: {run['counts']['completed_decisions']}/{run['counts']['planned_decisions']} completed")
    return 1 if failed_requests or failed_benchmarks else 0


if __name__ == "__main__":
    raise SystemExit(main())
