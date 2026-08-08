from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from modelito import local_client

from model import EXTRACTION_POLICY, URUGUAYAN_CONVERSATION_POLICY


DEFAULT_OLLAMA_MODEL = "qwen3.5:9b-mlx"
DEFAULT_OMLX_MODEL = "mlx-community/Qwen3.5-9B-MLX-4bit"


def conversation_messages(turns: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{"role": "system", "content": URUGUAYAN_CONVERSATION_POLICY}] + [
        {"role": turn["role"], "content": turn["text"]} for turn in turns
    ]


def _parse_prefer(value: str | None) -> list[str] | None:
    if not value:
        return None
    values = [item.strip().lower() for item in value.split(",") if item.strip()]
    return values or None


class LLMClient:
    """Local conversational client using Modelito runtime selection."""

    def __init__(self) -> None:
        self.profile = os.getenv("MODELITO_LOCAL_PROFILE", "auto")
        self.prefer = _parse_prefer(os.getenv("MODELITO_LOCAL_PREFER"))
        self.probe_timeout = float(os.getenv("MODELITO_PROBE_TIMEOUT", "1.5"))
        self.models = {
            "ollama": os.getenv("LOCAL_MODEL_OLLAMA", DEFAULT_OLLAMA_MODEL),
            "omlx": os.getenv("LOCAL_MODEL_OMLX", DEFAULT_OMLX_MODEL),
        }
        self._client = None
        self._provider: str | None = None
        self._model: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.models.get("ollama") or self.models.get("omlx"))

    @property
    def model(self) -> str | None:
        return self._model or self.models.get("omlx") or self.models.get("ollama")

    @property
    def provider(self) -> str | None:
        return self._provider

    def reset(self) -> None:
        self._client = None
        self._provider = None
        self._model = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client

        client = local_client(
            profile=self.profile,
            models=self.models,
            prefer=self.prefer,
            probe_timeout=self.probe_timeout,
        )
        self._client = client
        provider_name = client.provider_name.lower()
        if "omlx" in provider_name:
            self._provider = "omlx"
        elif "ollama" in provider_name:
            self._provider = "ollama"
        else:
            self._provider = client.provider_name
        self._model = client.model
        return client

    async def status(self) -> dict[str, Any]:
        try:
            client = await asyncio.to_thread(self._ensure_client)
            return {
                "configured": True,
                "ready": True,
                "profile": self.profile,
                "provider": self.provider,
                "model": client.model,
            }
        except Exception as exc:
            return {
                "configured": self.configured,
                "ready": False,
                "profile": self.profile,
                "provider": None,
                "model": None,
                "reason": str(exc),
                "models": dict(self.models),
            }

    async def chat(self, turns: list[dict[str, str]]) -> str:
        def run() -> str:
            response = self._ensure_client().chat(conversation_messages(turns))
            return response.text.strip()

        text = await asyncio.to_thread(run)
        if not text:
            raise RuntimeError("El modelo local no devolvió contenido textual")
        return text

    async def extract(self, turns: list[dict[str, str]]) -> list[dict[str, Any]]:
        transcript = "\n".join(
            f"{turn['id']} | {turn['role']} | {turn['text']}" for turn in turns
        )

        def run() -> str:
            response = self._ensure_client().chat(
                [
                    {"role": "system", "content": EXTRACTION_POLICY},
                    {"role": "user", "content": transcript},
                ]
            )
            return response.text

        content = await asyncio.to_thread(run)
        parsed = _parse_json_object(content)
        items = parsed.get("items", [])
        if not isinstance(items, list):
            raise RuntimeError("La extracción no devolvió una lista de elementos")
        return items


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
