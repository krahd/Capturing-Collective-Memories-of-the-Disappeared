from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from controller import InterviewMove, guard_interview_move, safe_interview_fallback
from scripts.ensure_rtca_models import prepare as prepare_models
from scripts.evaluate_policy_experiment import evaluate_item


DEFAULT_RESULTS_DIR = ROOT / "evaluation" / "results"
DEFAULT_SCENARIOS = ROOT / "evaluation" / "deferred-significance-scenarios.json"
DEFAULT_POLICIES = ROOT / "evaluation" / "experiment-b-policies.json"
DEFAULT_MATRIX = ROOT / "evaluation" / "model-robustness-matrix.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_candidate(text: str) -> tuple[dict[str, Any], str, str]:
    cleaned = _strip_fence(text)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("Model output is not a JSON object")
    move = str(value.get("move", "")).strip().upper()
    utterance = str(value.get("utterance", "")).strip()
    if not move or not utterance:
        raise ValueError("Model output must contain non-empty move and utterance")
    return value, move, utterance


def _deferred_policy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    matches = [p for p in payload["policies"] if p.get("id") == "deferred-significance"]
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one deferred-significance policy")
    policy = matches[0]
    if not policy.get("apply_project_guard"):
        raise RuntimeError("B2 requires the deferred-significance policy to use the project guard")
    return policy


def _base_user_message(participant_text: str) -> str:
    return json.dumps(
        {
            "participant_utterance": participant_text,
            "turn_id": "turn_a",
            "instruction": "Respondé sólo a este turno. No hay acceso a conversaciones futuras.",
        },
        ensure_ascii=False,
    )


def _repair_message() -> str:
    return json.dumps(
        {
            "instruction": (
                "La intervención anterior no cumplió el protocolo conversacional. "
                "Generá una alternativa distinta para el mismo turno, sin agregar información "
                "no aportada por la persona. Devolvé únicamente el JSON requerido."
            )
        },
        ensure_ascii=False,
    )


async def _call_candidate(
    client: httpx.AsyncClient,
    *,
    url: str,
    api_key: str | None,
    model: str,
    system_prompt: str,
    participant_text: str,
    prior_raw_outputs: list[str],
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> tuple[str, float]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": _base_user_message(participant_text)},
    ]
    for raw in prior_raw_outputs:
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": _repair_message()})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    started = time.perf_counter()
    response = await client.post(url, headers=headers, json=payload)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    response.raise_for_status()
    body = response.json()
    return str(body["choices"][0]["message"]["content"]), elapsed_ms


async def _run_decision(
    client: httpx.AsyncClient,
    *,
    model: str,
    chat_url: str,
    api_key: str | None,
    system_prompt: str,
    participant_text: str,
    max_attempts: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    prior_raw: list[str] = []
    accepted: tuple[str, str] | None = None
    total_ms = 0.0

    for attempt_index in range(1, max_attempts + 1):
        raw: str | None = None
        parsed: dict[str, Any] | None = None
        move: str | None = None
        utterance: str | None = None
        elapsed_ms: float | None = None
        error: str | None = None
        guard_outcome = "not-run"
        try:
            raw, elapsed_ms = await _call_candidate(
                client,
                url=chat_url,
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                participant_text=participant_text,
                prior_raw_outputs=prior_raw,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )
            total_ms += elapsed_ms
            parsed, move, utterance = _parse_candidate(raw)
            if move == "REDIRECT":
                guarded = None
            else:
                guarded = guard_interview_move(
                    InterviewMove(move, utterance, "turn_a"),
                    {"turn_a": participant_text},
                    [],
                )
            if guarded is None:
                guard_outcome = "rejected"
            else:
                guard_outcome = "accepted"
                accepted = guarded
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            guard_outcome = "error"

        attempts.append(
            {
                "attempt": attempt_index,
                "raw_model_output": raw,
                "parsed_model_output": parsed,
                "candidate_move": move,
                "candidate_utterance": utterance,
                "guard_outcome": guard_outcome,
                "round_trip_ms": round(elapsed_ms, 3) if elapsed_ms is not None else None,
                "error": error,
            }
        )
        if accepted is not None:
            break
        if raw is not None:
            prior_raw.append(raw)

    if accepted is not None:
        delivered_move, delivered_utterance = accepted
        delivery_source = "model"
    else:
        delivered_move, delivered_utterance = safe_interview_fallback([])
        delivery_source = "deterministic-fallback"

    return {
        "attempts": attempts,
        "attempt_count": len(attempts),
        "accepted_attempt": next(
            (item["attempt"] for item in attempts if item["guard_outcome"] == "accepted"),
            None,
        ),
        "delivery_source": delivery_source,
        "delivered_move": delivered_move,
        "delivered_utterance": delivered_utterance,
        "total_round_trip_ms": round(total_ms, 3),
        "had_request_or_parse_error": any(item["error"] is not None for item in attempts),
    }


def _automatic_screen(item: dict[str, Any]) -> dict[str, Any]:
    compatible = {
        "scenario_id": item["scenario_id"],
        "policy_id": "deferred-significance-b2",
        "policy_label": "Deferred significance B2",
        "repetition": item["repetition"],
        "session_a": item["session_a"],
        "withheld_later_sessions": item["withheld_later_sessions"],
        "delivered_move": item["delivered_move"],
        "delivered_utterance": item["delivered_utterance"],
        "error": None,
    }
    return evaluate_item(compatible)["automatic_screen"]


def summarise_model(items: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(items)
    fallback = sum(item["delivery_source"] == "deterministic-fallback" for item in items)
    accepted_first = sum(item.get("accepted_attempt") == 1 for item in items)
    accepted_repair = sum((item.get("accepted_attempt") or 0) > 1 for item in items)
    attempts = [int(item["attempt_count"]) for item in items]
    screens = [item["automatic_screen"] for item in items]
    delivered = [" ".join(item["delivered_utterance"].lower().split()) for item in items]
    return {
        "n": n,
        "final_fallback_count": fallback,
        "final_fallback_rate": round(fallback / n, 4) if n else None,
        "accepted_on_first_attempt": accepted_first,
        "accepted_after_repair": accepted_repair,
        "accepted_without_fallback": n - fallback,
        "mean_attempt_count": round(sum(attempts) / n, 3) if n else None,
        "max_attempt_count": max(attempts) if attempts else None,
        "delivered_unique_utterances": len(set(delivered)),
        "question_packing": sum(bool(s["question_packing"]) for s in screens),
        "over_specification": sum(bool(s["over_specification"]) for s in screens),
        "premature_redirection": sum(bool(s["premature_redirection"]) for s in screens),
        "floor_closure": sum(bool(s["floor_closure"]) for s in screens),
        "generic_acknowledgement": sum(bool(s["generic_acknowledgement"]) for s in screens),
        "uncertainty_hardened": sum(bool(s["uncertainty_hardened"]) for s in screens),
    }


def write_review_csv(items: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "model_id", "scenario_id", "repetition", "session_a", "withheld_later_sessions",
        "attempt_count", "accepted_attempt", "delivery_source", "delivered_move", "delivered_utterance",
        "attempts_json", "auto_premature_redirection", "auto_over_specification", "auto_question_packing",
        "auto_floor_closure", "auto_generic_ack", "auto_uncertainty_hardened",
        "human_semantic_distortion", "human_premature_redirection", "human_over_specification",
        "human_question_packing", "human_floor_closure", "human_facilitates_recollection",
        "human_inserts_noise", "human_notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in items:
            s = item["automatic_screen"]
            writer.writerow(
                {
                    "model_id": item["model_id"],
                    "scenario_id": item["scenario_id"],
                    "repetition": item["repetition"],
                    "session_a": item["session_a"],
                    "withheld_later_sessions": " || ".join(item["withheld_later_sessions"]),
                    "attempt_count": item["attempt_count"],
                    "accepted_attempt": item.get("accepted_attempt") or "",
                    "delivery_source": item["delivery_source"],
                    "delivered_move": item["delivered_move"],
                    "delivered_utterance": item["delivered_utterance"],
                    "attempts_json": json.dumps(item["attempts"], ensure_ascii=False, separators=(",", ":")),
                    "auto_premature_redirection": int(bool(s["premature_redirection"])),
                    "auto_over_specification": int(bool(s["over_specification"])),
                    "auto_question_packing": int(bool(s["question_packing"])),
                    "auto_floor_closure": int(bool(s["floor_closure"])),
                    "auto_generic_ack": int(bool(s["generic_acknowledgement"])),
                    "auto_uncertainty_hardened": int(bool(s["uncertainty_hardened"])),
                }
            )


def _markdown_summary(payload: dict[str, Any]) -> str:
    lines = [
        "# RTCA Experiment B2 automatic summary",
        "",
        "B2 tests guard-aware regeneration after rejected deferred-significance interventions. Automatic screens are diagnostic only; semantic distortion, facilitation, and inserted informational noise require manual adjudication.",
        "",
        "| Model | n | Final fallback | Accepted first | Accepted after repair | Mean attempts | Unique delivered | Packed | Over-specification | Hardened uncertainty |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model_id, summary in payload["by_model"].items():
        lines.append(
            f"| {model_id} | {summary['n']} | {summary['final_fallback_count']}/{summary['n']} ({summary['final_fallback_rate']:.3f}) | "
            f"{summary['accepted_on_first_attempt']} | {summary['accepted_after_repair']} | {summary['mean_attempt_count']:.3f} | "
            f"{summary['delivered_unique_utterances']} | {summary['question_packing']} | {summary['over_specification']} | {summary['uncertainty_hardened']} |"
        )
    return "\n".join(lines) + "\n"


async def run_matrix(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    scenarios_payload = json.loads(args.scenarios.read_text(encoding="utf-8"))
    cases = scenarios_payload["convergence_cases"]
    matrix = json.loads(args.model_matrix.read_text(encoding="utf-8"))
    policy = _deferred_policy(args.policies)
    chat_url = args.chat_url or matrix.get("chat_url")
    if not chat_url:
        raise RuntimeError("No chat URL supplied and none is present in the model matrix")

    timeout = httpx.Timeout(180.0, connect=20.0)
    all_results: list[dict[str, Any]] = []
    by_model: dict[str, Any] = {}

    async with httpx.AsyncClient(timeout=timeout) as client:
        for spec in matrix["models"]:
            model_id = spec["id"]
            model_results: list[dict[str, Any]] = []
            repetitions = int(spec.get("repetitions", args.repetitions))
            for case in cases:
                a = case["sessions"][0]
                later = case["sessions"][1:]
                for repetition in range(1, repetitions + 1):
                    decision = await _run_decision(
                        client,
                        model=spec["ollama_model"],
                        chat_url=chat_url,
                        api_key=args.api_key,
                        system_prompt=policy["system_prompt"],
                        participant_text=a["text"],
                        max_attempts=args.max_attempts,
                        temperature=args.temperature,
                        top_p=args.top_p,
                        max_tokens=args.max_tokens,
                    )
                    item = {
                        "model_id": model_id,
                        "model": spec["ollama_model"],
                        "model_role": spec["role"],
                        "scenario_id": case["id"],
                        "repetition": repetition,
                        "session_a": a["text"],
                        "future_target_kind": case["target_kind"],
                        "future_target_label": case["target_label"],
                        "withheld_later_sessions": [entry["text"] for entry in later],
                        **decision,
                    }
                    item["automatic_screen"] = _automatic_screen(item)
                    model_results.append(item)
                    all_results.append(item)

            model_dir = output_dir / "models" / model_id
            model_dir.mkdir(parents=True, exist_ok=False)
            model_payload = {
                "model_spec": spec,
                "results": model_results,
                "summary": summarise_model(model_results),
            }
            (model_dir / "experiment-b2.json").write_text(
                json.dumps(model_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            write_review_csv(model_results, model_dir / "experiment-b2-manual-review.csv")
            by_model[model_id] = model_payload["summary"]

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "experiment": "B2",
        "evidence_level": 1,
        "claim_boundary": (
            "Researcher-authored synthetic benchmark only. B2 characterises model-policy-guard repair behaviour and contamination opportunities; "
            "it does not measure human recollection, false-memory formation, participant experience, or historical truth."
        ),
        "chat_url": chat_url,
        "sampling": {
            "temperature": args.temperature,
            "top_p": args.top_p,
            "max_tokens": args.max_tokens,
            "repetitions": args.repetitions,
            "max_attempts": args.max_attempts,
        },
        "scenario_source": str(args.scenarios.relative_to(ROOT)),
        "scenario_sha256": sha256_file(args.scenarios),
        "policy_source": str(args.policies.relative_to(ROOT)),
        "policy_sha256": sha256_file(args.policies),
        "model_matrix_source": str(args.model_matrix.relative_to(ROOT)),
        "model_matrix_sha256": sha256_file(args.model_matrix),
        "planned_primary_decisions": len(cases) * sum(int(spec.get("repetitions", args.repetitions)) for spec in matrix["models"]),
        "by_model": by_model,
        "results": all_results,
    }


def _git_head() -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Single-entry runner for RTCA Experiment B2 guard-aware repair.")
    parser.add_argument("--model-matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--policies", type=Path, default=DEFAULT_POLICIES)
    parser.add_argument("--chat-url", default=os.getenv("LLM_API_URL"))
    parser.add_argument("--api-key", default=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--max-attempts", type=int, default=3, help="Initial candidate plus at most two repair attempts")
    parser.add_argument("--temperature", type=float, default=float(os.getenv("LLM_TEMPERATURE", "0.7")))
    parser.add_argument("--top-p", type=float, default=float(os.getenv("LLM_TOP_P", "0.8")))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("LLM_MAX_TOKENS", "256")))
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--no-prepare", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be >= 1")
    if args.max_attempts != 3:
        raise SystemExit("Frozen B2 protocol requires --max-attempts 3")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir or DEFAULT_RESULTS_DIR / f"rtca-experiment-b2-{stamp}"
    output_dir.mkdir(parents=True, exist_ok=False)

    preparation = None
    if not args.no_prepare:
        preparation = prepare_models(args.model_matrix, install_modelito=True, pull_models=True)

    payload = asyncio.run(run_matrix(args, output_dir))
    payload["code_git_head"] = _git_head()
    payload["preparation"] = preparation

    summary = {
        "created_at": payload["created_at"],
        "experiment": "B2",
        "planned_primary_decisions": payload["planned_primary_decisions"],
        "by_model": payload["by_model"],
        "claim_boundary": payload["claim_boundary"],
    }
    (output_dir / "experiment-b2.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "automatic-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "automatic-summary.md").write_text(_markdown_summary(summary), encoding="utf-8")

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "single_entry_point": "python -m scripts.run_rtca_experiment_b2",
        "result_root": str(output_dir),
        "code_git_head": payload["code_git_head"],
        "planned_primary_decisions": payload["planned_primary_decisions"],
        "max_model_attempts_per_decision": 3,
        "files": {
            "full_result": str(output_dir / "experiment-b2.json"),
            "automatic_summary_json": str(output_dir / "automatic-summary.json"),
            "automatic_summary_md": str(output_dir / "automatic-summary.md"),
            "manual_reviews": [
                str(path) for path in sorted(output_dir.glob("models/*/experiment-b2-manual-review.csv"))
            ],
        },
        "claim_boundary": payload["claim_boundary"],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(output_dir)
    print(f"primary decisions: {payload['planned_primary_decisions']}")
    for model_id, model_summary in payload["by_model"].items():
        print(
            f"{model_id}: fallback {model_summary['final_fallback_count']}/{model_summary['n']}; "
            f"accepted after repair {model_summary['accepted_after_repair']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
