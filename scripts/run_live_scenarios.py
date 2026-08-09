from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model import LLMClient


DEFAULT_SCENARIOS = ROOT / "evaluation" / "scenarios.json"
DEFAULT_RESULTS_DIR = ROOT / "evaluation" / "results"


def load_scenarios(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Scenario file must contain a JSON list")
    return data


async def run_scenario(client: LLMClient, scenario: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = await client.chat(scenario["turns"])
        error = None
    except Exception as exc:  # retain failures as evaluation evidence
        response = None
        error = f"{type(exc).__name__}: {exc}"
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "id": scenario["id"],
        "label": scenario.get("label", scenario["id"]),
        "turns": scenario["turns"],
        "response": response,
        "round_trip_ms": round(elapsed_ms, 3),
        "error": error,
    }


async def run_all(scenarios_path: Path) -> dict[str, Any]:
    client = LLMClient()
    client._require_configuration()
    scenarios = load_scenarios(scenarios_path)
    results = []
    for scenario in scenarios:
        results.append(await run_scenario(client, scenario))
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": client.model,
        "api_url": client.api_url,
        "scenario_source": str(scenarios_path),
        "metric_note": (
            "round_trip_ms measures complete request/response time for the prototype's "
            "non-streaming HTTP call. It is not TTFT and does not measure server-side "
            "turn detection, interruption, or cancellation."
        ),
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the researcher-authored Uruguayan-Spanish interaction scenarios "
            "against the configured OpenAI-compatible model and record raw outputs."
        )
    )
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = asyncio.run(run_all(args.scenarios))
    output = args.output
    if output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = DEFAULT_RESULTS_DIR / f"live-{stamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
