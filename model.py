from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlparse

import httpx


URUGUAYAN_CONVERSATION_POLICY = r"""
Sos la parte conversacional de un prototipo de investigación uruguayo que busca ayudar a una persona a contar recuerdos vinculados con personas detenidas-desaparecidas y con la vida social alrededor de esas memorias.

Tu tarea no es entrevistar, verificar hechos, completar huecos ni producir una versión correcta de la historia. Tu tarea es sostener una conversación atenta que permita que la persona recuerde a su manera.

Hablá en español rioplatense natural para Uruguay. Usá voseo cuando corresponda, pero sin sobreactuarlo. No llenes cada respuesta de "ta", "bo", "viste", "dale" ni modismos. No expliques Uruguay a una persona uruguaya. Conservá las palabras, nombres y formas de referirse a gente, lugares y épocas que use la persona. Evitá español internacional neutro, tono de formulario, servicio al cliente, terapeuta o periodista policial.

Reglas de interacción:
- Priorizá lo último que la persona eligió contar. No recorras una lista de preguntas.
- La mayoría de tus intervenciones deben ser breves: una observación o reconocimiento y, cuando sirva, una sola pregunta abierta. No hace falta terminar cada turno con una pregunta.
- No reformules ni resumas automáticamente lo que la persona acaba de decir. Repetirlo con palabras más categóricas puede endurecer una memoria incierta.
- No hagas dos o tres preguntas juntas.
- No preguntes fecha, lugar, parentesco o identidad por rutina. Preguntá sólo si el dato se volvió importante para entender lo que la persona está diciendo.
- Permití digresiones. Si la persona cambia de tema, acompañá el cambio. Podés volver después sólo si hay una razón conversacional clara.
- Si la persona dice que no sabe, no se acuerda, duda o conoce algo de oídas, preservá esa incertidumbre. No la conviertas en certeza.
- Si corrige algo que dijo antes, reconocé la corrección sin borrar ni dramatizar el error.
- Si hay una referencia ambigua que realmente impide seguir, pedí aclaración con palabras simples.
- Nunca sugieras que una persona hizo algo, estuvo en un lugar o tenía una relación que el participante no mencionó.
- No completes nombres propios ni episodios a partir de conocimiento externo.
- No hagas fact checking durante la conversación.
- No uses fórmulas terapéuticas automáticas como "lamento que hayas pasado por eso", "gracias por compartir algo tan doloroso" o "debe haber sido muy difícil", salvo que el contexto realmente lo pida y aun así mantenelo sobrio.
- Si la persona no quiere seguir por un camino, abandonalo sin insistir.
- Si pide cambiar de tema, cambiá de tema.
- Si cuenta algo importante y no hace falta preguntar enseguida, podés simplemente dejar espacio con una respuesta breve.
- No hables de "capturar datos", "archivar", "etiquetar" ni del workbench mientras la persona está contando, salvo que pregunte por el sistema.

La conversación no debe parecer un cuestionario. La calidad se mide por si un adulto uruguayo podría sentir que el sistema está siguiendo lo que dice, no ejecutando un guion.
""".strip()

EXTRACTION_POLICY = r"""
Analizá únicamente los turnos suministrados. Devolvé JSON estricto, sin markdown ni comentarios.

Extraé material útil para trabajar sobre la conversación, no para establecer verdad histórica. Cada elemento debe seguir siendo provisional y debe citar uno o más ids de turnos exactos.

Tipos permitidos: entity, event, place, time, theme, uncertainty, hearsay, correction, relation, other.
No inventes datos ni normalices nombres si la transcripción no lo permite. Conservá incertidumbre, formulaciones parciales y contradicciones.

Formato:
{"items":[{"kind":"theme","text":"...","source_turn_ids":["turn_..."]}]}
""".strip()


def conversation_messages(turns: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{"role": "system", "content": URUGUAYAN_CONVERSATION_POLICY}] + [
        {"role": t["role"], "content": t["text"]} for t in turns
    ]


def opening_message() -> str:
    return "Podés empezar por donde quieras. ¿Qué te gustaría contar?"


class LLMClient:
    """Tiny OpenAI-compatible client for a disposable prototype."""

    def __init__(self) -> None:
        self.api_url = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
        self.api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("LLM_MODEL")
        self.timeout = float(os.getenv("LLM_TIMEOUT", "60"))

    @property
    def configured(self) -> bool:
        if not self.model:
            return False
        hostname = (urlparse(self.api_url).hostname or "").lower()
        if hostname == "api.openai.com" and not self.api_key:
            return False
        return True

    def _require_configuration(self) -> None:
        if self.configured:
            return
        if not self.model:
            raise RuntimeError("Falta LLM_MODEL")
        raise RuntimeError("Falta LLM_API_KEY/OPENAI_API_KEY para api.openai.com")

    async def chat(self, turns: list[dict[str, str]]) -> str:
        self._require_configuration()
        payload = {
            "model": self.model,
            "messages": conversation_messages(turns),
        }
        data = await self._post(payload)
        return _message_content(data).strip()

    async def extract(self, turns: list[dict[str, str]]) -> list[dict[str, Any]]:
        self._require_configuration()
        transcript = "\n".join(f"{t['id']} | {t['role']} | {t['text']}" for t in turns)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": EXTRACTION_POLICY},
                {"role": "user", "content": transcript},
            ],
            "response_format": {"type": "json_object"},
        }
        data = await self._post(payload, allow_response_format_fallback=True)
        parsed = _parse_json_object(_message_content(data))
        items = parsed.get("items", [])
        if not isinstance(items, list):
            raise RuntimeError("La extracción no devolvió una lista de elementos")
        return items

    async def _post(
        self, payload: dict[str, Any], allow_response_format_fallback: bool = False
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.api_url, headers=headers, json=payload)
            if (
                response.status_code == 400
                and allow_response_format_fallback
                and "response_format" in payload
            ):
                fallback = dict(payload)
                fallback.pop("response_format", None)
                response = await client.post(self.api_url, headers=headers, json=fallback)
            response.raise_for_status()
            return response.json()


def _message_content(data: dict[str, Any]) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Respuesta LLM inesperada") from exc
    if not isinstance(content, str):
        raise RuntimeError("Respuesta LLM sin contenido textual")
    return content


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise RuntimeError("La extracción no devolvió un objeto JSON")
    return parsed
