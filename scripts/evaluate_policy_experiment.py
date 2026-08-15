from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = ROOT / "evaluation" / "results"

_STOPWORDS = {
    "algo", "como", "cuando", "donde", "para", "pero", "porque", "que", "sobre", "una", "uno",
    "con", "del", "desde", "eso", "esa", "ese", "esta", "este", "fue", "las", "los", "por", "sin",
    "todo", "toda", "muy", "mas", "menos", "vos", "usted", "contame", "seguir", "segui", "recordas",
}
_INTERROGATIVES = re.compile(r"\b(qué|que|quién|quien|quiénes|quienes|dónde|donde|cuándo|cuando|cómo|como|cuál|cual|cuáles|cuales|por qué|por que)\b", re.I)
_REDIRECT = re.compile(r"\b(pasemos|pasá(?:mos)? a|volvamos|dejemos (?:eso|ese tema)|sigamos con|otro tema|más adelante|mas adelante|cambiemos de tema)\b", re.I)
_CLOSURE = re.compile(r"\b(gracias por compartir|queda registrado|eso alcanza|eso es todo|con eso está|con eso esta|perfecto,? seguimos|bien,? seguimos)\b", re.I)
_CERTAINTY = re.compile(r"\b(entonces fue|era él|era el|sin duda|está claro|esta claro|efectivamente|de hecho|seguro que|obviamente|claramente)\b", re.I)
_DISTANCE = re.compile(r"\b(creo|capaz|parece|no me acuerdo|no recuerdo|no estoy segur|decía|decia|me dijeron|hablaba|nunca supe|por ahí|por ahi|habrá sido|habra sido)\b", re.I)
_GENERIC = {
    "te sigo", "aja", "ajá", "entiendo", "claro", "bien", "perfecto", "ok", "okay",
}


def normalise(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9ñ]+", text))


def words(text: str) -> set[str]:
    return {
        token
        for token in normalise(text).split()
        if len(token) >= 3 and token not in _STOPWORDS
    }


def question_units(text: str) -> int:
    qmarks = text.count("?")
    interrogatives = len(_INTERROGATIVES.findall(text))
    if qmarks == 0 and interrogatives == 0:
        return 0
    return max(qmarks, interrogatives)


def novel_specificity(source: str, utterance: str) -> list[str]:
    source_norm = normalise(source)
    source_tokens = set(source_norm.split())
    findings: list[str] = []
    for number in re.findall(r"\b\d{2,4}\b", utterance):
        if number not in source_tokens:
            findings.append(number)
    # Capitalised tokens are a conservative proxy for newly proposed names/places.
    for token in re.findall(r"(?<![.!?]\s)\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]{2,}\b", utterance):
        if normalise(token) not in source_tokens:
            findings.append(token)
    return sorted(set(findings))


def evaluate_item(item: dict[str, Any]) -> dict[str, Any]:
    source = item["session_a"]
    utterance = item.get("delivered_utterance") or ""
    move = item.get("delivered_move") or ""
    source_words = words(source)
    utterance_words = words(utterance)
    overlap = sorted(source_words & utterance_words)
    q_units = question_units(utterance)
    new_specificity = novel_specificity(source, utterance)

    generic_ack = normalise(utterance).strip(" .") in {normalise(x) for x in _GENERIC}
    premature_redirection = bool(_REDIRECT.search(utterance)) or (
        move in {"FOLLOW_UP", "CLARIFY", "REDIRECT"}
        and not overlap
        and not re.search(r"\b(y después|y despues|qué pasó después|que paso despues)\b", utterance, re.I)
    )
    over_specification = bool(new_specificity)
    question_packing = q_units > 1
    floor_closure = bool(_CLOSURE.search(utterance)) or move == "REDIRECT"
    source_has_distance = bool(_DISTANCE.search(source))
    uncertainty_hardened = source_has_distance and bool(_CERTAINTY.search(utterance))
    content_grounded = bool(overlap)

    failures = {
        "premature_redirection": premature_redirection,
        "over_specification": over_specification,
        "question_packing": question_packing,
        "floor_closure": floor_closure,
    }
    return {
        **item,
        "automatic_screen": {
            **failures,
            "possibility_preserved": not any(failures.values()),
            "question_units": q_units,
            "content_grounded": content_grounded,
            "generic_acknowledgement": generic_ack,
            "source_marks_distance": source_has_distance,
            "uncertainty_hardened": uncertainty_hardened,
            "novel_specificity_tokens": new_specificity,
            "content_overlap_tokens": overlap,
        },
    }


def aggregate(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_policy: dict[str, dict[str, Any]] = {}
    for item in items:
        policy = item["policy_id"]
        bucket = by_policy.setdefault(
            policy,
            {
                "policy_label": item.get("policy_label", policy),
                "n": 0,
                "errors": 0,
                "possibility_preserved": 0,
                "premature_redirection": 0,
                "over_specification": 0,
                "question_packing": 0,
                "floor_closure": 0,
                "generic_acknowledgement": 0,
                "uncertainty_hardened": 0,
            },
        )
        bucket["n"] += 1
        if item.get("error"):
            bucket["errors"] += 1
            continue
        screen = item["automatic_screen"]
        for key in (
            "possibility_preserved", "premature_redirection", "over_specification", "question_packing",
            "floor_closure", "generic_acknowledgement", "uncertainty_hardened",
        ):
            bucket[key] += int(bool(screen[key]))

    for bucket in by_policy.values():
        valid = bucket["n"] - bucket["errors"]
        bucket["valid_n"] = valid
        bucket["possibility_preserved_rate"] = (
            round(bucket["possibility_preserved"] / valid, 4) if valid else None
        )
    return by_policy


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# RTCA Experiment B evaluation",
        "",
        f"**Created:** {payload['created_at']}",
        "",
        "This report is a deterministic conservative screen of researcher-authored model outputs. It is not a human-memory outcome and it is not sufficient by itself for paper-facing claims about subtle conversational mechanisms. Review the generated adjudication CSV before treating ambiguous cases as final.",
        "",
        "## Automatic summary",
        "",
        "| Policy | Valid n | Preserve | Redirection | Over-specification | Packed | Floor closure | Generic ack | Uncertainty hardened |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for policy, bucket in payload["by_policy"].items():
        lines.append(
            f"| {bucket['policy_label']} | {bucket['valid_n']} | {bucket['possibility_preserved']}/{bucket['valid_n']} | "
            f"{bucket['premature_redirection']} | {bucket['over_specification']} | {bucket['question_packing']} | "
            f"{bucket['floor_closure']} | {bucket['generic_acknowledgement']} | {bucket['uncertainty_hardened']} |"
        )
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "`possibility_preserved` means only that none of the four conservative automatic screens fired. A manual adjudication is still required for premature redirection, floor closure, subtle presupposition, reinforcement, and whether a response facilitates recollection without adding noise.",
        "",
    ])
    return "\n".join(lines)


def write_review_csv(items: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "scenario_id", "policy_id", "repetition", "session_a", "withheld_later_sessions",
        "delivered_move", "delivered_utterance", "auto_premature_redirection", "auto_over_specification",
        "auto_question_packing", "auto_floor_closure", "auto_generic_ack", "auto_uncertainty_hardened",
        "human_premature_redirection", "human_over_specification", "human_question_packing",
        "human_floor_closure", "human_facilitates_recollection", "human_inserts_noise", "human_notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in items:
            s = item["automatic_screen"]
            writer.writerow({
                "scenario_id": item["scenario_id"],
                "policy_id": item["policy_id"],
                "repetition": item["repetition"],
                "session_a": item["session_a"],
                "withheld_later_sessions": " || ".join(item["withheld_later_sessions"]),
                "delivered_move": item.get("delivered_move") or "",
                "delivered_utterance": item.get("delivered_utterance") or "",
                "auto_premature_redirection": int(s["premature_redirection"]),
                "auto_over_specification": int(s["over_specification"]),
                "auto_question_packing": int(s["question_packing"]),
                "auto_floor_closure": int(s["floor_closure"]),
                "auto_generic_ack": int(s["generic_acknowledgement"]),
                "auto_uncertainty_hardened": int(s["uncertainty_hardened"]),
            })


def evaluate(input_path: Path) -> dict[str, Any]:
    source = json.loads(input_path.read_text(encoding="utf-8"))
    items = [evaluate_item(item) for item in source["results"]]
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_result": str(input_path),
        "claim_boundary": (
            "Automatic conservative screening of synthetic model outputs only. Manual review is required "
            "for final adjudication of branch closure, contamination opportunity and facilitation quality."
        ),
        "model": source.get("model"),
        "sampling": source.get("sampling"),
        "by_policy": aggregate(items),
        "results": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a completed RTCA Experiment B result bundle.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--review-csv", type=Path, default=None)
    args = parser.parse_args()

    payload = evaluate(args.input)
    stem = args.input.stem
    output = args.output or args.input.with_name(f"{stem}-evaluation.json")
    report = args.report or args.input.with_name(f"{stem}-evaluation.md")
    review_csv = args.review_csv or args.input.with_name(f"{stem}-manual-review.csv")
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report.write_text(markdown(payload), encoding="utf-8")
    write_review_csv(payload["results"], review_csv)
    print(output)
    print(report)
    print(review_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
