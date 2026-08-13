#!/usr/bin/env python3
"""Validate the frozen synthetic corpus used by the meeting interface."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_field import build_memory_field, build_timeline, normalise  # noqa: E402
from state import Session  # noqa: E402

EXPECTED = {
    "session_demo_seed_01": "Ficha 01 · la casa del Cerro",
    "session_demo_seed_02": "Ficha 02 · la facultad",
    "session_demo_seed_03": "Ficha 03 · la mudanza",
    "session_demo_seed_04": "Ficha 04 · la maestra",
    "session_demo_seed_05": "Ficha 05 · Maldonado",
    "session_demo_seed_06": "Ficha 06 · el silencio",
    "session_demo_seed_07": "Ficha 07 · los domingos",
    "session_demo_seed_08": "Ficha 08 · Tito en la casa",
    "session_demo_seed_09": "Ficha 09 · Tito en La Teja",
    "session_demo_seed_10": "Ficha 10 · un nombre usado",
}


def main() -> int:
    paths = sorted((ROOT / "demo" / "corpus").glob("session_*.json"))
    sessions = [Session.from_dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    assert len(sessions) == 10, f"se esperaban 10 fichas, hay {len(sessions)}"
    assert all(session.session_kind == "demo_seed" for session in sessions)
    assert {session.id: session.title for session in sessions} == EXPECTED

    field = build_memory_field(sessions)
    timeline = build_timeline(sessions)
    assert 60 <= len(field["nodes"]) <= 85, f"campo poco legible: {len(field['nodes'])} nodos"
    tito = next(
        (
            node
            for node in field["nodes"]
            if node["type"] == "person" and normalise(node["label"]) == "tito"
        ),
        None,
    )
    assert tito is not None, "la extracción no produjo a Tito como persona"
    assert set(tito["conversations"]) == {
        "session_demo_seed_08",
        "session_demo_seed_09",
        "session_demo_seed_10",
    }, "Tito no converge exactamente en las tres fichas diferidas"

    known_testimony = {
        turn.id
        for session in sessions
        for turn in session.turns
        if turn.role == "user" and turn.record_kind == "testimony"
    }
    mudanza = next(
        (
            divergence
            for divergence in timeline["divergences"]
            if normalise(divergence["subject"]) == "mudanza"
        ),
        None,
    )
    assert mudanza is not None and set(mudanza["years"]) == {1976, 1977}
    assert all(
        refs and set(refs).issubset(known_testimony)
        for refs in mudanza["by_year"].values()
    ), "las fechas contradictorias perdieron su fuente testimonial"

    recollection_ids = {
        node["turn_id"] for node in field["nodes"] if node["type"] == "recollection"
    }
    forbidden = {
        turn.id
        for session in sessions
        for turn in session.turns
        if turn.record_kind == "non_testimony/control"
    }
    assert recollection_ids.isdisjoint(forbidden)

    print(
        json.dumps(
            {
                "conversaciones": len(sessions),
                "nodos": len(field["nodes"]),
                "relaciones": len(field["edges"]),
                "tito_en_conversaciones": len(tito["conversations"]),
                "cronologias_abiertas": timeline["counts"]["fechados_de_varias_maneras"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
