#!/usr/bin/env python3
"""Build a small corpus of researcher-authored conversations for the memory field.

One conversation shows an interaction. Only several conversations show the thing
the project is actually about: that separate, partial, personally-held
recollections accumulate into a structure none of them contains alone.

Every transcript here is written by the researcher. None is participant
testimony and none was generated live. The **extractions, however, are real** —
the script runs the configured model over each recollection exactly as the
running application does, so the graph's model-derived material carries genuine
provenance rather than fabricated attribution. That is why this needs a
configured model and takes a few minutes.

The material deliberately overlaps: the same people, places and years recur
across conversations that do not otherwise know about each other, and two
conversations date the same move differently without the corpus resolving it.

Re-running is safe and is the right thing to do after changing the extraction
policy: each conversation replaces its own previous build rather than adding a
second copy beside it.

    python scripts/build_demo_corpus.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model import LLMClient  # noqa: E402
from state import ACTOR_SYSTEM, ORIGIN_MODEL, SessionStore, new_id  # noqa: E402

# (title, [(role, text), ...]) — assistant turns are authored exemplars.
CONVERSATIONS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Ficha 01 · la casa del Cerro",
        [
            ("assistant", "Podés empezar por donde quieras."),
            ("user", "Yo era chico, tendría nueve o diez. Esto habrá sido por el 77, por ahí."),
            ("assistant", "¿Qué te hace ubicarlo por esos años?"),
            ("user", "En casa de mi abuela, en el Cerro, se juntaban los domingos. Yo me acuerdo del ruido."),
            ("assistant", "Contame de esas reuniones."),
            ("user", "Del Flaco yo no me acuerdo. Lo que sé es porque mi vieja contaba que aparecía por casa y hablaba horas con mi tío Aníbal."),
        ],
    ),
    (
        "Ficha 02 · la facultad",
        [
            ("assistant", "Podés empezar por donde quieras."),
            ("user", "Mi padre conocía a Julio de la facultad. Estudiaban juntos, arquitectura me parece."),
            ("assistant", "¿Cómo era esa relación?"),
            ("user", "A Julio lo vi una sola vez, en el Cerro, en una de esas reuniones de los domingos."),
            ("assistant", "¿Te acordás de cuándo?"),
            ("user", "Fue en el 76. De eso estoy seguro porque ese año nos mudamos."),
        ],
    ),
    (
        "Ficha 03 · la mudanza",
        [
            ("assistant", "Podés empezar por donde quieras."),
            ("user", "Nos mudamos a La Teja después, cuando ya no estaba Aníbal."),
            ("assistant", "¿Cómo fue esa mudanza?"),
            ("user", "Yo digo que la mudanza fue en el 77. Mi hermana dice que en el 76. Nunca nos pusimos de acuerdo y ya no vale la pena discutirlo."),
        ],
    ),
    (
        "Ficha 04 · la maestra",
        [
            ("assistant", "Podés empezar por donde quieras."),
            ("user", "La maestra Elena preguntaba por mi tío Aníbal, y después dejó de preguntar. Nunca supe si le dijeron algo."),
            ("assistant", "¿Dónde era eso?"),
            ("user", "En la escuela del Cerro. Yo estaba en cuarto, creo."),
        ],
    ),
    (
        "Ficha 05 · Maldonado",
        [
            ("assistant", "Podés empezar por donde quieras."),
            ("user", "A Julio lo vieron en Maldonado en el 78, pero eso me lo contaron, yo no lo vi."),
            ("assistant", "¿Quién te lo contó?"),
            ("user", "Mi vieja decía que no, que era otro, que se parecía nomás. Quedó así."),
        ],
    ),
    (
        "Ficha 06 · el silencio",
        [
            ("assistant", "Podés empezar por donde quieras."),
            ("user", "En casa no se hablaba de Aníbal. Había fotos guardadas en una lata."),
            ("assistant", "¿Y esas fotos?"),
            ("user", "Mi abuela guardaba también una carta del Flaco. No sé qué decía, nunca la leí."),
        ],
    ),
    (
        "Ficha 07 · los domingos",
        [
            ("assistant", "Podés empezar por donde quieras."),
            ("user", "Las reuniones de los domingos en el Cerro siguieron hasta el 79, más o menos."),
            ("assistant", "¿Quiénes iban?"),
            ("user", "Venía gente que yo no conocía y a mí me mandaban al fondo a jugar. Se escuchaba igual."),
        ],
    ),
]


def discard_previous(store: SessionStore, title: str) -> int:
    """Remove an earlier build of this conversation.

    Without this, re-running after changing the extraction policy leaves the old
    interpretations in the field beside the new ones and doubles the corpus.
    Only conversations this script authored are touched — they are matched by
    their exact title, which no live session has.
    """
    stale = [session.id for session in store.list() if session.title == title]
    return sum(1 for session_id in stale if store.discard(session_id))


async def build_one(store: SessionStore, llm: LLMClient, title: str, script: list[tuple[str, str]]) -> None:
    discarded = discard_previous(store, title)
    session = store.create(title)
    session.is_recorded = True
    for role, text in script:
        session.add_turn(role, text, actor=ACTOR_SYSTEM if role == "assistant" else None)

    testimony = [t for t in session.turns if t.role == "user" and t.record_kind == "testimony"]
    created = 0
    for turn in testimony:
        provenance = {**llm.provenance(for_extraction=True), "run_id": new_id("run")}
        try:
            items = await llm.extract([turn.__dict__])
        except Exception as exc:  # noqa: BLE001
            print(f"    extracción falló en {turn.id}: {exc}")
            continue
        for raw in items:
            refs = [x for x in raw.get("source_turn_ids", []) if x == turn.id]
            if not refs or not raw.get("text"):
                continue
            try:
                session.add_derived_item(
                    raw.get("kind", "other"),
                    raw["text"],
                    refs,
                    origin=ORIGIN_MODEL,
                    origin_detail=provenance,
                )
                created += 1
            except ValueError:
                continue
    store.save(session)
    note = f" (reemplaza {discarded} anterior[es])" if discarded else ""
    print(f"  {title}: {len(testimony)} recuerdos, {created} interpretaciones del modelo{note}")


async def main() -> None:
    llm = LLMClient()
    if not llm.configured:
        raise SystemExit(
            "Se necesita un modelo configurado. Las extracciones del corpus son reales, "
            "no inventadas, así que este script no puede correr sin él."
        )
    store = SessionStore(ROOT / "data" / "sessions")
    print(f"Construyendo {len(CONVERSATIONS)} conversaciones con {llm.model}…")
    for title, script in CONVERSATIONS:
        await build_one(store, llm, title, script)
    print("Listo. Abrí la aplicación para ver el campo de memoria.")


if __name__ == "__main__":
    asyncio.run(main())
