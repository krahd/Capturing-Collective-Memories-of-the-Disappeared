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


DEFAULT_SCENARIOS = ROOT / "evaluation" / "rhythm-scenarios.json"
DEFAULT_RESULTS_DIR = ROOT / "evaluation" / "results"


def load_scenarios(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Rhythm scenario file must contain a JSON list")
    for scenario in data:
        turns = scenario.get("participant_turns")
        if not isinstance(turns, list) or len(turns) < 3 or not all(isinstance(x, str) for x in turns):
            raise ValueError("Every rhythm scenario needs at least three participant_turns")
    return data


async def run_scenario(client: LLMClient, scenario: dict[str, Any]) -> dict[str, Any]:
    history: list[dict[str, str]] = []
    exchange = []
    for participant_text in scenario["participant_turns"]:
        history.append({"role": "user", "text": participant_text})
        started = time.perf_counter()
        try:
            response = await client.respond(history)
            error = None
            assistant_text = response["utterance"]
            history.append({"role": "assistant", "text": assistant_text})
        except Exception as exc:  # retain failures as evaluation evidence
            response = None
            error = f"{type(exc).__name__}: {exc}"
            assistant_text = None
        exchange.append(
            {
                "participant": participant_text,
                "assistant": assistant_text,
                "controller": response,
                "question_count": assistant_text.count("?") if assistant_text else None,
                "round_trip_ms": round((time.perf_counter() - started) * 1000.0, 3),
                "error": error,
            }
        )
        if error:
            break
    return {
        "id": scenario["id"],
        "label": scenario.get("label", scenario["id"]),
        "review": scenario.get("review", ""),
        "exchange": exchange,
    }


async def run_all(scenarios_path: Path) -> dict[str, Any]:
    client = LLMClient()
    client._require_configuration()
    results = []
    for scenario in load_scenarios(scenarios_path):
        results.append(await run_scenario(client, scenario))
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": client.model,
        "api_url": client.api_url,
        "scenario_source": str(scenarios_path),
        "note": (
            "Each generated assistant utterance is fed into the next turn. Review move variation, "
            "question frequency, content grounding, and conversational rhythm manually."
        ),
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run multi-turn conversational-rhythm scenarios against the configured model."
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
        output = DEFAULT_RESULTS_DIR / f"rhythm-{stamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
