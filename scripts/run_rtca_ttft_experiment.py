from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math
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
from scripts.run_rtca_experiment_b2 import (
    DEFAULT_MATRIX,
    DEFAULT_POLICIES,
    DEFAULT_RESULTS_DIR,
    DEFAULT_SCENARIOS,
    _base_user_message,
    _deferred_policy,
    _parse_candidate,
    _repair_message,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * q
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    fraction = rank - low
    return ordered[low] * (1.0 - fraction) + ordered[high] * fraction


def median(values: list[float]) -> float | None:
    return percentile(values, 0.5)


def _ollama_version_observation() -> dict[str, Any]:
    result = subprocess.run(
        ["ollama", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


async def _stream_candidate(
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
) -> tuple[str, float | None, float]:
    """Return full text, model TTFT, and full streamed request time in ms.

    TTFT is measured from request dispatch to the first non-empty `delta.content`
    chunk received from the OpenAI-compatible streaming endpoint. Role-only and
    empty chunks do not count as a first token.
    """
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
        "stream": True,
    }

    started = time.perf_counter()
    first_content_at: float | None = None
    parts: list[str] = []

    async with client.stream("POST", url, headers=headers, json=payload) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            if line == "[DONE]":
                break
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content = delta.get("content")
            if content is None:
                # Some compatible servers may stream message-shaped chunks.
                content = (choices[0].get("message") or {}).get("content")
            if not isinstance(content, str) or content == "":
                continue
            if first_content_at is None:
                first_content_at = time.perf_counter()
            parts.append(content)

    finished = time.perf_counter()
    ttft_ms = (first_content_at - started) * 1000.0 if first_content_at is not None else None
    completion_ms = (finished - started) * 1000.0
    return "".join(parts), ttft_ms, completion_ms


async def _warm_model(
    client: httpx.AsyncClient,
    *,
    url: str,
    api_key: str | None,
    model: str,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Respond only with: ok"}],
        "temperature": 0,
        "max_tokens": 4,
        "stream": True,
    }
    started = time.perf_counter()
    first_content_at: float | None = None
    async with client.stream("POST", url, headers=headers, json=payload) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            if line == "[DONE]":
                break
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content = delta.get("content")
            if isinstance(content, str) and content and first_content_at is None:
                first_content_at = time.perf_counter()
    finished = time.perf_counter()
    return {
        "ttft_ms": round((first_content_at - started) * 1000.0, 3) if first_content_at else None,
        "completion_ms": round((finished - started) * 1000.0, 3),
    }


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
    elapsed_before_attempt_ms = 0.0

    for attempt_index in range(1, max_attempts + 1):
        raw: str | None = None
        parsed: dict[str, Any] | None = None
        move: str | None = None
        utterance: str | None = None
        ttft_ms: float | None = None
        completion_ms: float | None = None
        first_token_from_decision_start_ms: float | None = None
        error: str | None = None
        guard_outcome = "not-run"
        try:
            raw, ttft_ms, completion_ms = await _stream_candidate(
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
            if ttft_ms is not None:
                first_token_from_decision_start_ms = elapsed_before_attempt_ms + ttft_ms
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

        if completion_ms is not None:
            elapsed_before_attempt_ms += completion_ms

        attempts.append(
            {
                "attempt": attempt_index,
                "raw_model_output": raw,
                "parsed_model_output": parsed,
                "candidate_move": move,
                "candidate_utterance": utterance,
                "guard_outcome": guard_outcome,
                "ttft_ms": round(ttft_ms, 3) if ttft_ms is not None else None,
                "completion_ms": round(completion_ms, 3) if completion_ms is not None else None,
                "first_token_from_decision_start_ms": (
                    round(first_token_from_decision_start_ms, 3)
                    if first_token_from_decision_start_ms is not None
                    else None
                ),
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

    accepted_attempt = next(
        (item for item in attempts if item["guard_outcome"] == "accepted"),
        None,
    )
    return {
        "attempts": attempts,
        "attempt_count": len(attempts),
        "accepted_attempt": accepted_attempt["attempt"] if accepted_attempt else None,
        "delivery_source": delivery_source,
        "delivered_move": delivered_move,
        "delivered_utterance": delivered_utterance,
        "first_attempt_ttft_ms": attempts[0]["ttft_ms"] if attempts else None,
        "accepted_candidate_ttft_ms": accepted_attempt["ttft_ms"] if accepted_attempt else None,
        "accepted_candidate_first_token_from_decision_start_ms": (
            accepted_attempt["first_token_from_decision_start_ms"] if accepted_attempt else None
        ),
        # The guard cannot admit a JSON intervention until the candidate is complete.
        # This is the earliest point at which the current architecture can safely
        # expose the accepted intervention to a participant.
        "admission_ready_ms": round(elapsed_before_attempt_ms, 3),
        "had_request_or_parse_error": any(item["error"] is not None for item in attempts),
    }


def _automatic_screen(item: dict[str, Any]) -> dict[str, Any]:
    compatible = {
        "scenario_id": item["scenario_id"],
        "policy_id": "deferred-significance-b2-ttft",
        "policy_label": "Deferred significance B2 TTFT replication",
        "repetition": item["repetition"],
        "session_a": item["session_a"],
        "withheld_later_sessions": item["withheld_later_sessions"],
        "delivered_move": item["delivered_move"],
        "delivered_utterance": item["delivered_utterance"],
        "error": None,
    }
    return evaluate_item(compatible)["automatic_screen"]


def _summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(items)
    fallback = sum(item["delivery_source"] == "deterministic-fallback" for item in items)
    first_ttft = [float(item["first_attempt_ttft_ms"]) for item in items if item["first_attempt_ttft_ms"] is not None]
    accepted_ttft = [
        float(item["accepted_candidate_ttft_ms"])
        for item in items
        if item["accepted_candidate_ttft_ms"] is not None
    ]
    accepted_from_start = [
        float(item["accepted_candidate_first_token_from_decision_start_ms"])
        for item in items
        if item["accepted_candidate_first_token_from_decision_start_ms"] is not None
    ]
    admission_ready = [float(item["admission_ready_ms"]) for item in items]
    return {
        "n": n,
        "final_fallback_count": fallback,
        "final_fallback_rate": round(fallback / n, 4) if n else None,
        "first_attempt_ttft_median_ms": round(median(first_ttft), 3) if first_ttft else None,
        "first_attempt_ttft_p90_ms": round(percentile(first_ttft, 0.9), 3) if first_ttft else None,
        "accepted_candidate_ttft_median_ms": round(median(accepted_ttft), 3) if accepted_ttft else None,
        "accepted_candidate_ttft_p90_ms": round(percentile(accepted_ttft, 0.9), 3) if accepted_ttft else None,
        "accepted_candidate_first_token_from_decision_start_median_ms": (
            round(median(accepted_from_start), 3) if accepted_from_start else None
        ),
        "accepted_candidate_first_token_from_decision_start_p90_ms": (
            round(percentile(accepted_from_start, 0.9), 3) if accepted_from_start else None
        ),
        "admission_ready_median_ms": round(median(admission_ready), 3) if admission_ready else None,
        "admission_ready_p90_ms": round(percentile(admission_ready, 0.9), 3) if admission_ready else None,
    }


def _markdown_summary(payload: dict[str, Any]) -> str:
    lines = [
        "# RTCA B2 TTFT replication summary",
        "",
        "This is a new streaming replication of the frozen B2 protocol. It does not retrofit TTFT into the original B2 run.",
        "",
        "**TTFT definition:** request dispatch to the first non-empty streamed model content chunk. Role-only/empty chunks are ignored.",
        "",
        "**Admission boundary:** the current guard validates the completed JSON candidate. Model TTFT therefore is not participant-visible response onset; `admission_ready` remains the earliest safe delivery time in this architecture.",
        "",
        "| Model | n | Fallback | First-attempt TTFT med/p90 | Accepted-candidate TTFT med/p90 | Accepted first token from decision start med/p90 | Admission-ready med/p90 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model_id, s in payload["by_model"].items():
        lines.append(
            f"| {model_id} | {s['n']} | {s['final_fallback_count']}/{s['n']} | "
            f"{s['first_attempt_ttft_median_ms']:.1f}/{s['first_attempt_ttft_p90_ms']:.1f} ms | "
            f"{s['accepted_candidate_ttft_median_ms']:.1f}/{s['accepted_candidate_ttft_p90_ms']:.1f} ms | "
            f"{s['accepted_candidate_first_token_from_decision_start_median_ms']:.1f}/{s['accepted_candidate_first_token_from_decision_start_p90_ms']:.1f} ms | "
            f"{s['admission_ready_median_ms']:.1f}/{s['admission_ready_p90_ms']:.1f} ms |"
        )
    return "\n".join(lines) + "\n"


async def run(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
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
    warmups: dict[str, Any] = {}

    async with httpx.AsyncClient(timeout=timeout) as client:
        for spec in matrix["models"]:
            model_id = spec["id"]
            warmups[model_id] = await _warm_model(
                client,
                url=chat_url,
                api_key=args.api_key,
                model=spec["ollama_model"],
            )
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
            by_model[model_id] = _summary(model_results)
            model_dir = output_dir / "models" / model_id
            model_dir.mkdir(parents=True, exist_ok=False)
            (model_dir / "experiment-b2-ttft.json").write_text(
                json.dumps({"model_spec": spec, "summary": by_model[model_id], "results": model_results}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "experiment": "B2-TTFT-replication",
        "relationship_to_frozen_b2": (
            "New streaming replication using the same B2 scenario/model/policy/repair design. "
            "TTFT cannot be reconstructed from the frozen non-streaming B2 traces."
        ),
        "measurement": {
            "ttft": "request dispatch to first non-empty streamed delta.content chunk",
            "completion": "request dispatch to completion of streamed candidate",
            "admission_ready": (
                "sum of completed candidate request times through the accepted attempt, or all attempts before fallback; "
                "the guard validates completed JSON, so this is the earliest safe delivery point in the current architecture"
            ),
            "warmup": "one excluded streaming warm-up request per model before measured decisions",
        },
        "claim_boundary": (
            "Researcher-authored synthetic streaming replication. It measures local model TTFT and guard-mediated decision timing, "
            "not ASR, endpointing, TTS, networked deployment, participant-perceived latency, or full-duplex conversational quality."
        ),
        "chat_url": chat_url,
        "sampling": {
            "temperature": args.temperature,
            "top_p": args.top_p,
            "max_tokens": args.max_tokens,
            "repetitions": args.repetitions,
            "max_attempts": args.max_attempts,
            "stream": True,
        },
        "runtime": {
            "ollama_version_observation": _ollama_version_observation(),
            "user_supplied_server_version": args.ollama_server_version,
            "user_supplied_client_version": args.ollama_client_version,
        },
        "warmups": warmups,
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
    parser = argparse.ArgumentParser(description="Streaming TTFT replication of RTCA Experiment B2.")
    parser.add_argument("--model-matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--policies", type=Path, default=DEFAULT_POLICIES)
    parser.add_argument("--chat-url", default=os.getenv("LLM_API_URL"))
    parser.add_argument("--api-key", default=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--temperature", type=float, default=float(os.getenv("LLM_TEMPERATURE", "0.7")))
    parser.add_argument("--top-p", type=float, default=float(os.getenv("LLM_TOP_P", "0.8")))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("LLM_MAX_TOKENS", "256")))
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--no-prepare", action="store_true")
    parser.add_argument("--ollama-server-version", default="0.32.5")
    parser.add_argument("--ollama-client-version", default="0.32.9")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be >= 1")
    if args.max_attempts != 3:
        raise SystemExit("Frozen B2 replication requires --max-attempts 3")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir or DEFAULT_RESULTS_DIR / f"rtca-experiment-b2-ttft-{stamp}"
    output_dir.mkdir(parents=True, exist_ok=False)

    preparation = None
    if not args.no_prepare:
        preparation = prepare_models(args.model_matrix, install_modelito=True, pull_models=True)

    payload = asyncio.run(run(args, output_dir))
    payload["code_git_head"] = _git_head()
    payload["preparation"] = preparation

    (output_dir / "experiment-b2-ttft.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "created_at": payload["created_at"],
        "experiment": payload["experiment"],
        "planned_primary_decisions": payload["planned_primary_decisions"],
        "measurement": payload["measurement"],
        "runtime": payload["runtime"],
        "by_model": payload["by_model"],
        "claim_boundary": payload["claim_boundary"],
    }
    (output_dir / "ttft-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "ttft-summary.md").write_text(_markdown_summary(summary), encoding="utf-8")
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "single_entry_point": "python -m scripts.run_rtca_ttft_experiment",
        "result_root": str(output_dir),
        "code_git_head": payload["code_git_head"],
        "planned_primary_decisions": payload["planned_primary_decisions"],
        "runtime": payload["runtime"],
        "measurement": payload["measurement"],
        "files": {
            "full_result": str(output_dir / "experiment-b2-ttft.json"),
            "summary_json": str(output_dir / "ttft-summary.json"),
            "summary_md": str(output_dir / "ttft-summary.md"),
            "per_model": [str(path) for path in sorted(output_dir.glob("models/*/experiment-b2-ttft.json"))],
        },
        "claim_boundary": payload["claim_boundary"],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(output_dir)
    print(f"primary decisions: {payload['planned_primary_decisions']}")
    for model_id, s in payload["by_model"].items():
        print(
            f"{model_id}: TTFT median/p90 {s['first_attempt_ttft_median_ms']:.1f}/"
            f"{s['first_attempt_ttft_p90_ms']:.1f} ms; admission-ready median/p90 "
            f"{s['admission_ready_median_ms']:.1f}/{s['admission_ready_p90_ms']:.1f} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
