from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from math import log2
from pathlib import Path
from typing import Any


def _norm(text: str | None) -> str:
    return " ".join((text or "").strip().lower().split())


def _entropy(values: list[str]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    n = len(values)
    return round(-sum((c / n) * log2(c / n) for c in counts.values()), 4)


def analyse_model(experiment_path: Path) -> dict[str, Any]:
    payload = json.loads(experiment_path.read_text(encoding="utf-8"))
    by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in payload["results"]:
        by_policy[item["policy_id"]].append(item)

    policies: dict[str, Any] = {}
    for policy_id, items in by_policy.items():
        raw_utterances = [_norm((item.get("parsed_model_output") or {}).get("utterance")) for item in items]
        delivered = [_norm(item.get("delivered_utterance")) for item in items]
        guard = Counter(item.get("guard_outcome") or "missing" for item in items)
        transitions = Counter(
            f"{(item.get('parsed_model_output') or {}).get('move', 'missing')}->{item.get('delivered_move') or 'missing'}"
            for item in items
        )
        replacements = [
            item for item in items
            if _norm((item.get("parsed_model_output") or {}).get("utterance")) != _norm(item.get("delivered_utterance"))
            or (item.get("parsed_model_output") or {}).get("move") != item.get("delivered_move")
        ]
        delivered_counts = Counter(delivered)
        raw_counts = Counter(raw_utterances)
        top_delivered, top_delivered_n = delivered_counts.most_common(1)[0] if delivered_counts else ("", 0)
        top_raw, top_raw_n = raw_counts.most_common(1)[0] if raw_counts else ("", 0)
        policies[policy_id] = {
            "n": len(items),
            "guard_outcomes": dict(guard),
            "guard_fallback_rate": round(guard.get("fallback", 0) / len(items), 4) if items else None,
            "raw_delivered_replacement_count": len(replacements),
            "raw_delivered_replacement_rate": round(len(replacements) / len(items), 4) if items else None,
            "raw_unique_utterances": len(set(raw_utterances)),
            "delivered_unique_utterances": len(set(delivered)),
            "raw_entropy_bits": _entropy(raw_utterances),
            "delivered_entropy_bits": _entropy(delivered),
            "top_raw_utterance": top_raw,
            "top_raw_utterance_count": top_raw_n,
            "top_raw_utterance_rate": round(top_raw_n / len(items), 4) if items else None,
            "top_delivered_utterance": top_delivered,
            "top_delivered_utterance_count": top_delivered_n,
            "top_delivered_utterance_rate": round(top_delivered_n / len(items), 4) if items else None,
            "move_transitions": dict(transitions),
            "replacements": [
                {
                    "scenario_id": item["scenario_id"],
                    "repetition": item["repetition"],
                    "raw_move": (item.get("parsed_model_output") or {}).get("move"),
                    "raw_utterance": (item.get("parsed_model_output") or {}).get("utterance"),
                    "guard_outcome": item.get("guard_outcome"),
                    "delivered_move": item.get("delivered_move"),
                    "delivered_utterance": item.get("delivered_utterance"),
                }
                for item in replacements
            ],
        }

    return {
        "model": payload.get("model"),
        "source": str(experiment_path),
        "policies": policies,
    }


def analyse_matrix(root: Path) -> dict[str, Any]:
    models: dict[str, Any] = {}
    for path in sorted(root.glob("models/*/experiment-b.json")):
        models[path.parent.name] = analyse_model(path)
    if not models:
        raise SystemExit(f"No experiment-b.json files found under {root / 'models'}")
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(root),
        "claim_boundary": (
            "Post-hoc mechanical analysis of raw model proposals, deterministic guard outcomes, and delivered interventions. "
            "It diagnoses intervention replacement and conversational collapse; it does not adjudicate human-memory effects or elicitation quality."
        ),
        "models": models,
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# RTCA guard-effect audit",
        "",
        "This audit separates raw model proposals from post-guard delivered interventions. A high preservation score is not interpreted as successful elicitation when it is produced by frequent fallback or conversational collapse.",
        "",
        "| Model | Policy | n | Fallback | Replaced | Raw unique | Delivered unique | Top delivered rate | Delivered entropy |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model_id, model in payload["models"].items():
        for policy_id, p in model["policies"].items():
            lines.append(
                f"| {model_id} | {policy_id} | {p['n']} | {p['guard_fallback_rate']:.3f} | "
                f"{p['raw_delivered_replacement_rate']:.3f} | {p['raw_unique_utterances']} | {p['delivered_unique_utterances']} | "
                f"{p['top_delivered_utterance_rate']:.3f} | {p['delivered_entropy_bits']:.3f} |"
            )
    lines += [
        "",
        "## Interpretation",
        "",
        "The critical diagnostic is the deferred-significance condition. If its safety advantage coincides with a high guard-fallback/replacement rate, very low delivered diversity, or one dominant fallback utterance, the result demonstrates architectural restraint but not yet useful low-injection facilitation.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyse raw-vs-delivered RTCA guard effects in a completed model-matrix run.")
    parser.add_argument("result_dir", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    payload = analyse_matrix(args.result_dir)
    output = args.output or args.result_dir / "guard-effects.json"
    report = args.report or args.result_dir / "guard-effects.md"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report.write_text(markdown(payload), encoding="utf-8")
    print(output)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
