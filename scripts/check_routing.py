"""Run the adversarial routing set against the router actually configured.

Routing moved onto a small model to keep the large one free for interviewing.
That is the right architecture, but it puts a small model on a boundary where a
mistake is expensive: a session stopped in the middle of a memory, a recollection
filed as control material, or somebody asking to stop and being interviewed
anyway. Tests can show that the configured router is *called*; only running real
Uruguayan Spanish through it shows whether it is good enough to be there.

This exercises the same path as a live turn — deterministic controls first, then
the model — so what it measures is the classification the application would
actually make.

    python scripts/check_routing.py
    python scripts/check_routing.py --repetitions 3 --json evaluation/results/routing.json

Exit status is non-zero if any case marked `critical` fails, so it can gate a
model or configuration change rather than only informing one.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from controller import deterministic_intent  # noqa: E402
from model import LLMClient  # noqa: E402

CASES = ROOT / "evaluation" / "routing-cases.json"


async def classify_case(llm: LLMClient, text: str) -> tuple[str, str, int]:
    """Classify exactly as a live turn does. Returns intent, source, milliseconds."""
    started = time.perf_counter()
    intent = deterministic_intent(text)
    source = "deterministic"
    if not intent:
        source = "router_model"
        # One turn of context, matching the shape `classify` receives in the app.
        intent = await llm.classify([{"id": "turn_probe", "role": "user", "text": text}])
    return intent, source, round((time.perf_counter() - started) * 1000)


async def run(repetitions: int, router_model: str | None = None) -> dict:
    spec = json.loads(CASES.read_text(encoding="utf-8"))
    llm = LLMClient()
    if router_model:
        llm.router_model = router_model
    if not llm.configured:
        raise SystemExit("No hay modelo configurado; revisá .env (LLM_MODEL / LLM_API_URL).")
    await llm.start()
    results = []
    try:
        for case in spec["cases"]:
            allowed = {case["expected"], *case.get("acceptable", [])}
            observations = []
            for _ in range(repetitions):
                try:
                    intent, source, elapsed = await classify_case(llm, case["text"])
                except Exception as exc:  # a router failure is itself a finding
                    observations.append({"intent": f"ERROR: {exc}", "source": "error", "ms": 0})
                    continue
                observations.append({"intent": intent, "source": source, "ms": elapsed})
            observed = [o["intent"] for o in observations]
            results.append(
                {
                    "id": case["id"],
                    "text": case["text"],
                    "expected": case["expected"],
                    "acceptable": sorted(allowed - {case["expected"]}),
                    "severity": case.get("severity", "normal"),
                    "note": case.get("note", ""),
                    "observed": observed,
                    "source": observations[0]["source"] if observations else "none",
                    "ms": [o["ms"] for o in observations],
                    "exact": all(intent == case["expected"] for intent in observed),
                    "acceptable_only": all(intent in allowed for intent in observed),
                    "stable": len(set(observed)) == 1,
                }
            )
    finally:
        await llm.close()

    model_timings = [ms for r in results if r["source"] == "router_model" for ms in r["ms"]]
    failures = [r for r in results if not r["acceptable_only"]]
    return {
        "router": llm.router_provenance(),
        "repetitions": repetitions,
        "cases": len(results),
        "exact": sum(1 for r in results if r["exact"]),
        "acceptable": sum(1 for r in results if r["acceptable_only"]),
        "unstable": [r["id"] for r in results if not r["stable"]],
        "critical_failures": [r["id"] for r in failures if r["severity"] == "critical"],
        "failures": [r["id"] for r in failures],
        "router_latency_ms": {
            "n": len(model_timings),
            "median": sorted(model_timings)[len(model_timings) // 2] if model_timings else 0,
            "max": max(model_timings) if model_timings else 0,
        },
        "confusions": dict(
            Counter(
                f"{r['expected']} -> {observed}"
                for r in failures
                for observed in r["observed"]
                if observed != r["expected"] and observed not in r["acceptable"]
            )
        ),
        "results": results,
    }


def report(summary: dict) -> None:
    router = summary["router"]
    print(f"router: {router['model']}  ({router['endpoint']}, num_ctx={router['context_tokens']})")
    print(
        f"cases: {summary['cases']}  exacto: {summary['exact']}  "
        f"aceptable: {summary['acceptable']}  repeticiones: {summary['repetitions']}"
    )
    latency = summary["router_latency_ms"]
    print(f"latencia del router: mediana {latency['median']} ms, máx {latency['max']} ms ({latency['n']} llamadas)")
    if summary["unstable"]:
        print(f"inestables entre repeticiones: {', '.join(summary['unstable'])}")
    print()
    for result in summary["results"]:
        if result["acceptable_only"]:
            continue
        mark = "CRÍTICO" if result["severity"] == "critical" else "menor"
        print(f"[{mark}] {result['id']}: esperado {result['expected']}, obtenido {result['observed']}")
        print(f"    «{result['text']}»")
        if result["note"]:
            print(f"    {result['note']}")
    if summary["confusions"]:
        print("\nconfusiones:")
        for confusion, count in sorted(summary["confusions"].items(), key=lambda kv: -kv[1]):
            print(f"  {confusion}: {count}")
    print()
    if summary["critical_failures"]:
        print(f"FALLAS CRÍTICAS: {', '.join(summary['critical_failures'])}")
    else:
        print("Sin fallas críticas.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--json", type=Path, help="también escribir el resultado completo aquí")
    parser.add_argument(
        "--router-model",
        help="comparar otro modelo de ruteo sin tocar .env",
    )
    args = parser.parse_args()

    summary = asyncio.run(run(max(1, args.repetitions), args.router_model))
    report(summary)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"escrito: {args.json}")
    return 1 if summary["critical_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
