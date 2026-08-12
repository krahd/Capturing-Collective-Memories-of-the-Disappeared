#!/usr/bin/env python3
"""Build the researcher-authored example transcript used as a demo fallback.

Every turn here is written by the researcher. Nothing was captured from a
participant and nothing was generated live by a model. The assistant turns are
authored exemplars of the interaction policy, not model output.

The point of building it through the real `Session` API rather than hand-writing
JSON is that the session record is then produced by exactly the same code path
the live application uses, so the audit trail is genuine rather than decorative.

    python scripts/build_demo_session.py
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from state import (  # noqa: E402
    ACTOR_SYSTEM,
    ORIGIN_MODEL,
    ORIGIN_RESEARCHER,
    Session,
    new_id,
)

OUTPUT = ROOT / "demo" / "sesion-ejemplo.json"

# The model identity a run of this material would have carried. Recorded so the
# example shows what real model provenance looks like.
MODEL_PROVENANCE = {
    "model": "qwen3:30b-a3b-instruct-2507-q4_K_M",
    "endpoint": "http://127.0.0.1:11434",
    "local": True,
    "temperature": 0.7,
    "top_p": 0.8,
    "max_tokens": 256,
    "run_id": "run_ejemplo01",
}

# Researcher-authored. Deliberately contains an approximate date, hearsay, a
# correction several turns later, a refusal, and a digression.
TRANSCRIPT = [
    ("assistant", "Podés empezar por donde quieras. ¿Qué te gustaría contar?"),
    ("user", "Yo era chico, tendría nueve o diez. Esto habrá sido por el 77, 78, por ahí. No te puedo decir más."),
    ("assistant", "¿Qué te hace ubicarlo por esos años?"),
    ("user", "Porque me acuerdo del uniforme de la escuela, y de que todavía vivíamos en lo de mi abuela. Después nos mudamos."),
    ("assistant", "La casa de tu abuela aparece bastante en lo que contás."),
    ("user", "Sí. Ahí se juntaban. Del Flaco yo no me acuerdo, ojo. Lo que sé es porque mi vieja contaba que aparecía por casa y hablaba horas con mi tío."),
    ("assistant", "Entonces lo del Flaco te llega por tu madre."),
    ("user", "Claro. Yo no lo vi nunca, o no me acuerdo de haberlo visto. Eso fue en La Teja."),
    ("assistant", "Ta."),
    ("user", "Pará, te dije La Teja pero estoy mezclando dos cosas. Esto que te cuento era en el Cerro. La Teja fue después, cuando ya no estaba mi tío."),
    ("assistant", "Bien. ¿Querés seguir por ahí o preferís contarme otra cosa?"),
    ("user", "De lo de mi tío no quiero hablar. Te puedo contar de las reuniones que hacían después en casa de mi abuela."),
    ("assistant", "Contame de las reuniones."),
    ("user", "Eran los domingos. Venía gente que yo no conocía y a mí me mandaban al fondo a jugar. Pero se escuchaba igual. No entendía nada de lo que decían, pero me acuerdo del tono."),
]


def build() -> Session:
    session = Session(id=new_id("session"), title="Conversación de ejemplo (grabada)")
    session.is_recorded = True
    session.record(ACTOR_SYSTEM, "sesion_creada", "Sesión de ejemplo redactada por el investigador")

    turns = []
    for index, (role, text) in enumerate(TRANSCRIPT):
        # The scripted opening is not model output and the record says so.
        actor = ACTOR_SYSTEM if index == 0 else None
        turns.append(session.add_turn(role, text, actor=actor))

    fecha, oidas, teja, cerro, reuniones = turns[1], turns[5], turns[7], turns[9], turns[13]

    session.add_annotation([fecha.id], "uncertain", "La persona da un rango, no una fecha.")
    session.add_annotation([oidas.id], "hearsay", "Fuente declarada: la madre.")
    session.add_annotation([cerro.id], "correction", "Corrige el lugar dicho antes.")

    # Researcher-authored interpretations.
    tiempo = session.add_derived_item(
        "time",
        "Período recordado de manera aproximada: «por el 77, 78»",
        [fecha.id],
        note="No convertir en fecha establecida.",
    )
    lugar_teja = session.add_derived_item(
        "place",
        "La Teja, mencionada primero y después corregida",
        [teja.id],
        origin=ORIGIN_RESEARCHER,
    )
    lugar_cerro = session.add_derived_item(
        "place",
        "el Cerro, lugar corregido por la persona",
        [cerro.id],
        origin=ORIGIN_RESEARCHER,
    )

    # Model-derived interpretations, stamped with the exact model and settings.
    flaco = session.add_derived_item(
        "entity",
        "Persona referida como «el Flaco»",
        [oidas.id],
        origin=ORIGIN_MODEL,
        origin_detail=MODEL_PROVENANCE,
    )
    session.add_derived_item(
        "hearsay",
        "Lo relativo al Flaco proviene del relato de la madre, no de memoria propia de la persona",
        [oidas.id],
        origin=ORIGIN_MODEL,
        origin_detail=MODEL_PROVENANCE,
    )
    session.add_derived_item(
        "theme",
        "Reuniones de los domingos en casa de la abuela",
        [reuniones.id],
        origin=ORIGIN_MODEL,
        origin_detail=MODEL_PROVENANCE,
    )

    # The model overreached: it produced an event the participant never stated,
    # from a topic the participant explicitly declined. Retired with a reason and
    # kept on the record rather than quietly deleted.
    exceso = session.add_derived_item(
        "event",
        "Detención del tío de la persona",
        [turns[11].id],
        origin=ORIGIN_MODEL,
        origin_detail=MODEL_PROVENANCE,
    )

    # An edit, so the revision history is populated.
    session.update_derived_item(
        flaco.id,
        text="Persona referida como «el Flaco». Identidad no establecida.",
        note="La persona no afirma haberlo visto.",
    )

    session.add_relation("corrects", lugar_cerro.id, lugar_teja.id, "La persona corrige el lugar.")

    session.withdraw_derived_item(
        exceso.id,
        "La persona no dijo esto. El modelo lo infirió de un tema que ella explícitamente no quiso tratar.",
    )

    session.add_annotation([tiempo.source_turn_ids[0]], "significant", "Ancla temporal del relato.")
    return session


def main() -> None:
    session = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(session.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    counts = session.summary()
    print(f"Escrito {OUTPUT.relative_to(ROOT)}")
    print(
        f"  {counts['turnos']} turnos · {counts['interpretaciones']} interpretaciones "
        f"({counts['interpretaciones_investigador']} investigador, {counts['interpretaciones_modelo']} modelo) · "
        f"{counts['retiradas']} retirada(s) · {counts['ediciones']} edición(es) · {counts['eventos']} eventos"
    )


if __name__ == "__main__":
    main()
