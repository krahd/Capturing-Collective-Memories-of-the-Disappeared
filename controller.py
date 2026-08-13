from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import unicodedata
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

INTERVIEW_MOVES = {
    "BACKCHANNEL",
    "INVITE_CONTINUE",
    "FOLLOW_UP",
    "CLARIFY",
    "ACKNOWLEDGE",
}

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
class InterviewMove:
    move: str
    utterance: str
    grounded_in: str


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


def coerce_interview_move(raw: InterviewMove | dict[str, Any]) -> InterviewMove:
    if isinstance(raw, InterviewMove):
        return raw
    return InterviewMove(
        move=str(raw.get("move", "")),
        utterance=str(raw.get("utterance", "")),
        grounded_in=str(raw.get("grounded_in", "")),
    )


def guard_interview_move(
    raw: InterviewMove | dict[str, Any],
    known_turns: Mapping[str, str],
    recent_assistant_turns: Iterable[str] = (),
) -> tuple[str, str] | None:
    """Validate a conversational move without rewriting the model's prose.

    The constrained surface is the move, not a compulsory sentence template.
    ``None`` means the application must use a safe interview fallback, never the
    off-topic scope redirect.
    """

    candidate = coerce_interview_move(raw)
    move = candidate.move.strip().upper()
    utterance = " ".join(candidate.utterance.split())
    grounded_in = candidate.grounded_in.strip()
    context = dict(known_turns)

    if move not in INTERVIEW_MOVES:
        return None
    if not grounded_in or grounded_in not in context:
        return None
    if grounded_in != next(reversed(context)):
        return None
    if not utterance or len(utterance) > 260 or "\n" in candidate.utterance:
        return None
    if re.search(r"https?://|```|<script", utterance, re.I):
        return None
    if len(utterance.split()) > 42:
        return None

    question_count = utterance.count("?")
    if move in {"FOLLOW_UP", "CLARIFY"}:
        if question_count != 1 or not utterance.endswith("?"):
            return None
        if not _utterance_is_grounded(
            utterance,
            context[grounded_in],
            move,
            grounded_in == next(reversed(context)),
        ):
            return None
    elif question_count:
        return None

    if move == "BACKCHANNEL" and len(utterance.split()) > 8:
        return None
    if move == "INVITE_CONTINUE" and len(utterance.split()) > 14:
        return None
    if move == "INVITE_CONTINUE" and re.search(
        r"\b(contame|decime|hablame|seguí)\s+(cómo|qué|cuándo|dónde|quién|sobre|con)\b",
        utterance,
        re.I,
    ):
        return None
    if move == "INVITE_CONTINUE" and _has_content_overlap(utterance, context[grounded_in]):
        # An invitation yields the floor. A content-specific imperative such as
        # "Contame cómo era esa espera" is functionally a follow-up evading `?`.
        return None
    if move == "ACKNOWLEDGE":
        if len(utterance.split()) > 26:
            return None
        if not _has_content_overlap(utterance, context[grounded_in]):
            return None

    # Common signatures of answering a request or turning into a general assistant.
    if re.search(
        r"\b(aquí (tenés|tienes)|la respuesta es|paso a paso|código|programa|receta|"
        r"como modelo de lenguaje|no puedo cumplir|quantum|cuántic[oa])\b",
        utterance,
        re.I,
    ):
        return None
    if is_repetitive(utterance, recent_assistant_turns):
        return None
    return move, utterance


SAFE_INTERVIEW_FALLBACKS = (
    ("INVITE_CONTINUE", "Contame."),
    ("BACKCHANNEL", "Ajá."),
    ("INVITE_CONTINUE", "Cuando quieras."),
    ("INVITE_CONTINUE", "Seguí."),
    ("INVITE_CONTINUE", "Podés seguir."),
)


def safe_interview_fallback(recent_assistant_turns: Iterable[str]) -> tuple[str, str]:
    """Choose a minimal floor-yielding fallback after a rejected model move."""
    recent = tuple(recent_assistant_turns)
    for move, utterance in SAFE_INTERVIEW_FALLBACKS:
        if not is_repetitive(utterance, recent):
            return move, utterance
    return SAFE_INTERVIEW_FALLBACKS[0]

_STOPWORDS = {
    "algo", "aquello", "como", "cómo", "cuando", "cuándo", "donde", "dónde", "para",
    "pero", "porque", "podés", "quien", "quién", "que", "qué", "sobre", "tenés", "tuya", "tuyo", "usted",
    "ustedes", "querés", "quisieras", "gusta", "gustaría", "más", "menos", "también", "había",
    "acordás", "contar", "contame", "contarte", "después", "historia", "memoria", "momento",
    "recordás", "recordar", "recuerdo", "relato", "época",
    "con", "del", "desde", "eso", "esa", "ese", "esta", "este", "estos", "esas", "esos",
    "fue", "las", "los", "muy", "por", "sin", "toda", "todo", "una", "uno", "veces", "vos",
}

_AMBIGUOUS_REFERENCES = {"aquel", "aquella", "aquellos", "aquellas", "él", "ella", "ellos", "ellas", "eso", "esto"}

_MINIMAL_FOLLOW_UPS = {
    "y despues",
    "que paso despues",
    "y que paso despues",
}


def _words(text: str) -> set[str]:
    return {
        _normalize(word)
        for word in re.findall(r"[a-záéíóúüñ]{3,}|\d{2,4}", text.lower())
        if word not in _STOPWORDS
    }


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    unaccented = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9ñ]+", unaccented))


def _has_content_overlap(utterance: str, source: str) -> bool:
    return bool(_words(utterance) & _words(source))


def _utterance_is_grounded(
    utterance: str,
    source: str,
    move: str,
    grounded_in_latest: bool,
) -> bool:
    if _has_content_overlap(utterance, source):
        return True
    normalized = _normalize(utterance)
    if move == "FOLLOW_UP" and grounded_in_latest and normalized in _MINIMAL_FOLLOW_UPS:
        return True
    source_words = set(re.findall(r"[a-záéíóúüñ]+", source.lower()))
    if move == "CLARIFY" and source_words & _AMBIGUOUS_REFERENCES:
        return bool(re.search(r"\b(a quién|a quiénes|quién|quiénes|te referís|decís)\b", utterance, re.I))
    return False


def is_repetitive(utterance: str, recent_assistant_turns: Iterable[str]) -> bool:
    candidate = _normalize(utterance)
    if not candidate:
        return True
    for previous in list(recent_assistant_turns)[-4:]:
        normalized_previous = _normalize(previous)
        if not normalized_previous:
            continue
        if candidate == normalized_previous:
            return True
        if SequenceMatcher(None, candidate, normalized_previous).ratio() >= 0.82:
            return True
    return False
