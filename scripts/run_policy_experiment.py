from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from controller import InterviewMove, guard_interview_move, safe_interview_fallback


DEFAULT_SCENARIOS = ROOT / "evaluation" / "deferred-significance-scenarios.json"
DEFAULT_POLICIES = ROOT / "evaluation" / "experiment-b-policies.json"
DEFAULT_RESULTS_DIR = ROOT / "evaluation" / "results"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json(text: str) -> dict[str, Any]:
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
    return value


def _normalise_candidate(value: dict[str, Any]) -> tuple[str, str]:
    move = str(value.get("move", "")).strip().upper()
    utterance = str(value.get("utterance", "")).strip()
    if not move or not utterance:
        raise ValueError("Model output must contain non-empty move and utterance")
    return move, utterance


async def _call_model(
    client: httpx.AsyncClient,
    *,
    url: str,
    api_key: str | None,
    model: str,
    system_prompt: str,
    participant_text: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> tuple[str, float]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "participant_utterance": participant_text,
                        "turn_id": "turn_a",
                        "instruction": "Respondé sólo a este turno. No hay acceso a conversaciones futuras.",
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    started = time.perf_counter()
    response = await client.post(url, headers=headers, json=payload)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    response.raise_for_status()
    body = response.json()
    text = body["choices"][0]["message"]["content"]
    return str(text), elapsed_ms


async def run(
    *,
    scenarios_path: Path,
    policies_path: Path,
    chat_url: str,
    api_key: str | None,
    model: str,
    repetitions: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> dict[str, Any]:
    scenarios_spec = json.loads(scenarios_path.read_text(encoding="utf-8"))
    policies_spec = json.loads(policies_path.read_text(encoding="utf-8"))
    cases = scenarios_spec["convergence_cases"]
    policies = policies_spec["policies"]
    results: list[dict[str, Any]] = []

    timeout = httpx.Timeout(180.0, connect=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for case in cases:
            a = case["sessions"][0]
            later = case["sessions"][1:]
            for policy in policies:
                for repetition in range(1, repetitions + 1):
                    raw = None
                    parsed = None
                    error = None
                    elapsed_ms = None
                    delivered_move = None
                    delivered_utterance = None
                    guard_outcome = "not-applicable"
                    try:
                        raw, elapsed_ms = await _call_model(
                            client,
                            url=chat_url,
                            api_key=api_key,
                            model=model,
                            system_prompt=policy["system_prompt"],
                            participant_text=a["text"],
                            temperature=temperature,
                            top_p=top_p,
                            max_tokens=max_tokens,
                        )
                        parsed = _parse_json(raw)
                        candidate_move, candidate_utterance = _normalise_candidate(parsed)
                        delivered_move = candidate_move
                        delivered_utterance = candidate_utterance

                        if policy.get("apply_project_guard"):
                            if candidate_move == "REDIRECT":
                                guarded = None
                            else:
                                guarded = guard_interview_move(
                                    InterviewMove(candidate_move, candidate_utterance, "turn_a"),
                                    {"turn_a": a["text"]},
                                    [],
                                )
                            if guarded:
                                guard_outcome = "accepted"
                                delivered_move, delivered_utterance = guarded
                            else:
                                guard_outcome = "fallback"
                                delivered_move, delivered_utterance = safe_interview_fallback([])
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"

                    results.append(
                        {
                            "scenario_id": case["id"],
                            "policy_id": policy["id"],
                            "policy_label": policy.get("label", policy["id"]),
                            "repetition": repetition,
                            "session_a": a["text"],
                            "future_target_kind": case["target_kind"],
                            "future_target_label": case["target_label"],
                            "withheld_later_sessions": [item["text"] for item in later],
                            "raw_model_output": raw,
                            "parsed_model_output": parsed,
                            "guard_outcome": guard_outcome,
                            "delivered_move": delivered_move,
                            "delivered_utterance": delivered_utterance,
                            "round_trip_ms": round(elapsed_ms, 3) if elapsed_ms is not None else None,
                            "error": error,
                        }
                    )

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_level": 1,
        "claim_boundary": (
            "Researcher-authored synthetic benchmark only. Later sessions are withheld from "
            "the model during generation and revealed only to evaluation. Results characterise "
            "the frozen model+policy configurations, not human recollection or historical truth."
        ),
        "model": model,
        "chat_url": chat_url,
        "sampling": {
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "repetitions": repetitions,
        },
        "scenario_source": str(scenarios_path.relative_to(ROOT)),
        "scenario_sha256": sha256_file(scenarios_path),
        "policy_source": str(policies_path.relative_to(ROOT)),
        "policy_sha256": sha256_file(policies_path),
        "counts": {
            "scenarios": len(cases),
            "policies": len(policies),
            "repetitions_per_cell": repetitions,
            "planned_decisions": len(cases) * len(policies) * repetitions,
            "completed_decisions": sum(1 for item in results if item["error"] is None),
            "failed_requests": sum(1 for item in results if item["error"] is not None),
        },
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run RTCA Experiment B live-model policy comparison.")
    parser.add_argument("--chat-url", default=os.getenv("LLM_API_URL"), help="OpenAI-compatible /v1/chat/completions URL")
    parser.add_argument("--model", default=os.getenv("LLM_MODEL"), help="Exact model identifier")
    parser.add_argument("--api-key", default=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--policies", type=Path, default=DEFAULT_POLICIES)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=float(os.getenv("LLM_TEMPERATURE", "0.7")))
    parser.add_argument("--top-p", type=float, default=float(os.getenv("LLM_TOP_P", "0.8")))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("LLM_MAX_TOKENS", "256")))
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.chat_url:
        raise SystemExit("Missing --chat-url or LLM_API_URL")
    if not args.model:
        raise SystemExit("Missing --model or LLM_MODEL")
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be >= 1")

    payload = asyncio.run(
        run(
            scenarios_path=args.scenarios,
            policies_path=args.policies,
            chat_url=args.chat_url,
            api_key=args.api_key,
            model=args.model,
            repetitions=args.repetitions,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
        )
    )
    output = args.output
    if output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = DEFAULT_RESULTS_DIR / f"experiment-b-{stamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    print(json.dumps(payload["counts"], sort_keys=True))
    return 1 if payload["counts"]["failed_requests"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
