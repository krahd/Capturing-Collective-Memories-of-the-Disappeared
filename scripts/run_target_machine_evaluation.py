from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = ROOT / "evaluation" / "results"


def _run_text(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _safe_system_text(command: list[str]) -> str | None:
    if shutil.which(command[0]) is None:
        return None
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    return text or None


def machine_metadata() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": sys.version,
        "sw_vers": _safe_system_text(["sw_vers"]),
        "hardware_model": _safe_system_text(["sysctl", "-n", "hw.model"]),
        "cpu_brand": _safe_system_text(
            ["sysctl", "-n", "machdep.cpu.brand_string"]
        ),
        "memory_bytes": _safe_system_text(["sysctl", "-n", "hw.memsize"]),
    }


def slug(text: str) -> str:
    cleaned = []
    for char in text.lower():
        if char.isalnum():
            cleaned.append(char)
        elif not cleaned or cleaned[-1] != "-":
            cleaned.append("-")
    return "".join(cleaned).strip("-") or "evaluation"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create one target-machine evidence bundle containing raw conversational "
            "scenario outputs, machine metadata, and a separate Modelito local-runtime "
            "benchmark. This does not score conversational quality automatically."
        )
    )
    parser.add_argument("--provider", required=True, help="Modelito provider label")
    parser.add_argument("--model", required=True, help="Exact runtime model identifier")
    parser.add_argument(
        "--chat-url",
        required=True,
        help="Full OpenAI-compatible /v1/chat/completions URL used by the prototype",
    )
    parser.add_argument(
        "--benchmark-base-url",
        default=None,
        help="Optional OpenAI-compatible base /v1 URL for Modelito benchmark",
    )
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--pid", type=int, default=None)
    parser.add_argument(
        "--label",
        default=None,
        help="Optional human-readable configuration label for the evidence bundle",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be at least 1")

    benchmark_cli = shutil.which("modelito-benchmark-local")
    if benchmark_cli is None:
        raise SystemExit(
            "modelito-benchmark-local is not on PATH. Install the current krahd/modelito "
            "package before running target-machine evaluation."
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = args.label or f"{args.provider}-{args.model}"
    output_dir = args.output_dir or DEFAULT_RESULTS_DIR / f"{stamp}-{slug(label)}"
    output_dir.mkdir(parents=True, exist_ok=False)

    scenario_output = output_dir / "conversation-scenarios.json"
    benchmark_output = output_dir / "runtime-benchmark.json"

    scenario_env = os.environ.copy()
    scenario_env["LLM_API_URL"] = args.chat_url
    scenario_env["LLM_MODEL"] = args.model
    if args.api_key:
        scenario_env["LLM_API_KEY"] = args.api_key
    else:
        scenario_env.pop("LLM_API_KEY", None)
        scenario_env.pop("OPENAI_API_KEY", None)

    scenario_command = [
        sys.executable,
        "scripts/run_live_scenarios.py",
        "--output",
        str(scenario_output),
    ]
    scenario_result = subprocess.run(
        scenario_command,
        cwd=ROOT,
        env=scenario_env,
        capture_output=True,
        text=True,
        check=False,
    )

    benchmark_command = [
        benchmark_cli,
        "--provider",
        args.provider,
        "--model",
        args.model,
        "--repetitions",
        str(args.repetitions),
        "--json",
        "--output",
        str(benchmark_output),
    ]
    if args.benchmark_base_url:
        benchmark_command.extend(["--base-url", args.benchmark_base_url])
    if args.api_key:
        benchmark_command.extend(["--api-key", args.api_key])
    if args.pid is not None:
        benchmark_command.extend(["--pid", str(args.pid)])

    benchmark_result = subprocess.run(
        benchmark_command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "provider": args.provider,
        "model": args.model,
        "chat_url": args.chat_url,
        "benchmark_base_url": args.benchmark_base_url,
        "repetitions": args.repetitions,
        "pid": args.pid,
        "machine": machine_metadata(),
        "conversation": {
            "output": str(scenario_output),
            "returncode": scenario_result.returncode,
            "stdout": scenario_result.stdout.strip(),
            "stderr": scenario_result.stderr.strip(),
            "note": (
                "Conversation outputs are researcher-authored scenario evidence and "
                "require manual rubric review. They are not participant-validation data."
            ),
        },
        "runtime_benchmark": {
            "output": str(benchmark_output),
            "returncode": benchmark_result.returncode,
            "stdout": benchmark_result.stdout.strip(),
            "stderr": benchmark_result.stderr.strip(),
            "note": (
                "Runtime measurements are independent of conversational scoring; follow "
                "the caveats embedded by Modelito in the benchmark JSON."
            ),
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(output_dir)
    if scenario_result.returncode != 0 or benchmark_result.returncode != 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
