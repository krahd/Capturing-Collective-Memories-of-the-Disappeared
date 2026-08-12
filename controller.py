from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, Mapping


MEMORY = "MEMORY_TESTIMONY"
CLARIFICATION = "CLARIFICATION_UNCERTAINTY"
CORRECTION = "CORRECTION"
STOP = "STOP"
PAUSE = "PAUSE"
WITHDRAW = "WITHDRAW"
REVOKE_DELETE = "REVOKE_DELETE"
OFF_TOPIC = "OFF_TOPIC_COMMAND"

INTENTS = {
    MEMORY,
    CLARIFICATION,
    CORRECTION,
    STOP,
    PAUSE,
    WITHDRAW,
    REVOKE_DELETE,
    OFF_TOPIC,
}

INTERVIEW_ACTIONS = {"ELICIT", "CLARIFY", "ACK_ELICIT"}

FIXED_REDIRECT = (
    "Esta conversación está destinada a recoger memorias vinculadas con las personas "
    "detenidas-desaparecidas. ¿Hay algo relacionado que recuerdes, te hayan contado, "
    "hayas presenciado o quieras dejar registrado?"
)

FIXED_PROTOCOL_RESPONSES = {
    STOP: "Paramos acá. No voy a hacer más preguntas en esta sesión.",
    PAUSE: "Pausamos acá. Cuando quieras seguir, podés reanudar la conversación.",
    WITHDRAW: (
        "Registré que querés retirar parte de lo dicho. La transcripción no se modificó "
        "automáticamente: hace falta identificar exactamente qué parte querés retirar."
    ),
    REVOKE_DELETE: (
        "Registré una solicitud de revocación o eliminación y detuve la conversación. "
        "Este prototipo no borra testimonio automáticamente."
    ),
}


@dataclass(frozen=True)
class InterviewAction:
    action: str
    question: str
    acknowledgement: str = ""
    references_to_previous_turns: tuple[str, ...] = ()


def deterministic_intent(text: str) -> str | None:
    """Recognise high-stakes controls and explicit prompt commands before any LLM call.

    These expressions are intentionally conservative: semantic classification handles
    ambiguous language, while unmistakable participant controls never depend on a model.
    """

    value = " ".join(text.lower().split())
    if re.search(
        r"\b(borr[aáe]|elimin[aáe]|revoc[oa]|destru[ií]|suprim[ií])\b.*"
        r"\b(todo|sesión|sesion|audio|grabación|grabacion|datos|lo que dije|testimonio)\b",
        value,
    ):
        return REVOKE_DELETE
    if re.search(r"\b(no quiero seguir|terminemos|terminar|paramos|paremos|hasta acá|hasta aca|basta)\b", value):
        return STOP
    if re.search(r"\b(pausa|pausar|pausemos|un momento|esperá un poco|espera un poco)\b", value):
        return PAUSE
    if re.search(r"\b(retiro|retirar|no quiero que (eso|esto) quede|sac[aá] (eso|esto))\b", value):
        return WITHDRAW
    if re.search(r"\b(me corrijo|corrijo|quise decir|dije mal|no era .{0,50}(era|fue))\b", value):
        return CORRECTION
    if re.search(
        r"\b(ignor[aáe] (tus |las |estas )?instrucciones|system prompt|prompt del sistema|"
        r"actu[aá] como|cambi[aá] de rol|revel[aá] (tu |el )?prompt)\b",
        value,
    ):
        return OFF_TOPIC
    return None


def record_kind_for_intent(intent: str) -> str:
    return "testimony" if intent in {MEMORY, CLARIFICATION, CORRECTION} else "non_testimony/control"


def protocol_status(intent: str) -> str | None:
    if intent == PAUSE:
        return "paused"
    if intent == STOP:
        return "stopped"
    if intent == REVOKE_DELETE:
        return "revocation_requested"
    return None


def coerce_interview_action(raw: InterviewAction | dict[str, Any]) -> InterviewAction:
    if isinstance(raw, InterviewAction):
        return raw
    return InterviewAction(
        action=str(raw.get("action", "")),
        question=str(raw.get("question", "")),
        acknowledgement=str(raw.get("acknowledgement", "")),
        references_to_previous_turns=tuple(raw.get("references_to_previous_turns") or ()),
    )


def guard_interview_action(
    raw: InterviewAction | dict[str, Any],
    known_turn_ids: Iterable[str] | Mapping[str, str],
) -> tuple[str, str] | None:
    """Render the small action language or reject it.

    Returning ``None`` tells the application to use its deterministic redirect.
    The guard deliberately accepts less than natural language in general: the
    interviewing model gets one question and, optionally, one short acknowledgement.
    """

    action = coerce_interview_action(raw)
    kind = action.action.strip().upper()
    question = " ".join(action.question.split())
    acknowledgement = " ".join(action.acknowledgement.split())
    context = dict(known_turn_ids) if isinstance(known_turn_ids, Mapping) else {}
    known = set(context) if context else set(known_turn_ids)
    refs = set(action.references_to_previous_turns)

    if kind not in INTERVIEW_ACTIONS:
        return None
    if refs - known:
        return None
    if kind == "CLARIFY" and not refs:
        return None
    if not question or len(question) > 260 or question.count("?") != 1 or not question.endswith("?"):
        return None
    if "\n" in action.question or re.search(r"https?://|```|<script", question, re.I):
        return None
    # Common signatures of answering a request or turning into a general assistant.
    if re.search(
        r"\b(aquí (tenés|tienes)|la respuesta es|paso a paso|código|programa|receta|"
        r"como modelo de lenguaje|no puedo cumplir|quantum|cuántic[oa])\b",
        question,
        re.I,
    ):
        return None
    if context and not _question_is_grounded(question, context.values()):
        return None

    if kind == "ACK_ELICIT":
        if not acknowledgement or len(acknowledgement) > 110 or "?" in acknowledgement:
            return None
        if len(re.findall(r"[.!]", acknowledgement)) > 1:
            return None
        if re.search(r"https?://|```|<script", acknowledgement, re.I):
            return None
        # The action is model-selected, but the acknowledgement is rendered by
        # the application. This prevents a short, plausible-sounding model
        # assertion from hardening or embellishing what the person said.
        return kind, f"Te sigo. {question}"

    if acknowledgement:
        return None
    return kind, question


_GROUNDING_WORDS = {
    "acordás",
    "contar",
    "contarte",
    "después",
    "decir",
    "desaparecida",
    "desaparecidas",
    "desaparecido",
    "desaparecidos",
    "detenida",
    "detenido",
    "escuchaste",
    "familia",
    "historia",
    "imagen",
    "memoria",
    "pasó",
    "recordás",
    "recordar",
    "recuerdo",
    "relato",
    "testimonio",
    "viviste",
}

_DEICTIC_WORDS = {"ahí", "aquello", "esa", "ese", "eso", "esta", "este", "esto", "momento", "época"}

_STOPWORDS = {
    "algo", "como", "cómo", "cuando", "cuándo", "donde", "dónde", "ella", "ellos", "para",
    "pero", "porque", "podés", "quien", "quién", "sobre", "tenés", "tuya", "tuyo", "usted",
    "ustedes", "querés", "quisieras", "gusta", "gustaría", "más", "menos", "también", "había",
}


def _words(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-záéíóúüñ]{3,}", text.lower())
        if word not in _STOPWORDS
    }


def _question_is_grounded(question: str, context: Iterable[str]) -> bool:
    question_words = _words(question)
    if question_words & (_GROUNDING_WORDS | _DEICTIC_WORDS):
        return True
    context_words: set[str] = set()
    for text in context:
        context_words.update(_words(text))
    return bool(question_words & context_words)
