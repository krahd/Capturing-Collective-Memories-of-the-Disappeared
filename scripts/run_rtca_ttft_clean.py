from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import httpx

from scripts import run_rtca_ttft_experiment as base


DEFAULT_SEED_BASE = 42
DEFAULT_CONTEXT_LENGTH = 8192


def _derived_seed(
    *,
    seed_base: int,
    model: str,
    participant_text: str,
    prior_raw_outputs: list[str],
) -> int:
    """Derive a stable per-request seed from request identity.

    This avoids making all five nominal repetitions of a scenario identical while
    keeping the seed schedule reproducible. Repair attempts receive different
    seeds because prior_raw_outputs is part of the derivation.
    """
    material = json.dumps(
        {
            "seed_base": seed_base,
            "model": model,
            "participant_text": participant_text,
            "prior_raw_outputs": prior_raw_outputs,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(material).digest()
    # Ollama's OpenAI-compatible endpoint accepts integer seeds. Keep the value
    # within the signed 31-bit range for portability.
    return int.from_bytes(digest[:8], "big") % 2_147_483_647


def _make_seeded_stream_candidate(seed_base: int):
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
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": base._base_user_message(participant_text)},
        ]
        for raw in prior_raw_outputs:
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": base._repair_message()})

        seed = _derived_seed(
            seed_base=seed_base,
            model=model,
            participant_text=participant_text,
            prior_raw_outputs=prior_raw_outputs,
        )
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "seed": seed,
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

    return _stream_candidate


def _augment_json(path: Path, reproducibility: dict[str, Any]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["reproducibility"] = reproducibility
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean, reproducible wrapper for the RTCA B2 streaming TTFT replication."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed-base", type=int, default=DEFAULT_SEED_BASE)
    parser.add_argument("--context-length", type=int, default=DEFAULT_CONTEXT_LENGTH)
    parser.add_argument("--ollama-server-version", required=True)
    parser.add_argument("--ollama-client-version", required=True)
    args = parser.parse_args()

    if args.ollama_server_version != args.ollama_client_version:
        raise SystemExit(
            "Clean replication requires matched Ollama versions: "
            f"server={args.ollama_server_version}, client={args.ollama_client_version}"
        )
    if args.context_length < 1:
        raise SystemExit("--context-length must be positive")

    # _run_decision resolves this module global at runtime, so replacing the
    # streaming function here preserves the frozen B2 control/guard logic while
    # adding an explicit reproducible seed to every model request.
    base._stream_candidate = _make_seeded_stream_candidate(args.seed_base)

    original_argv = sys.argv
    try:
        sys.argv = [
            "run_rtca_ttft_experiment",
            "--output-dir",
            str(args.output_dir),
            "--ollama-server-version",
            args.ollama_server_version,
            "--ollama-client-version",
            args.ollama_client_version,
        ]
        status = base.main()
    finally:
        sys.argv = original_argv

    if status != 0:
        return status

    reproducibility = {
        "clean_replication": True,
        "seed_base": args.seed_base,
        "seed_scheme": (
            "sha256(seed_base, model, participant_text, prior_raw_outputs) modulo 2147483647; "
            "stable per request and different across repair states"
        ),
        "context_length": args.context_length,
        "context_configuration": "OLLAMA_CONTEXT_LENGTH set on the dedicated ollama serve process",
        "ollama_server_version": args.ollama_server_version,
        "ollama_client_version": args.ollama_client_version,
        "versions_matched": True,
    }

    for filename in ("experiment-b2-ttft.json", "ttft-summary.json", "manifest.json"):
        _augment_json(args.output_dir / filename, reproducibility)
    for path in sorted(args.output_dir.glob("models/*/experiment-b2-ttft.json")):
        _augment_json(path, reproducibility)

    print(f"CLEAN_RESULT_DIR={args.output_dir}")
    print(f"SEED_BASE={args.seed_base}")
    print(f"CONTEXT_LENGTH={args.context_length}")
    print(f"OLLAMA_VERSION={args.ollama_server_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
