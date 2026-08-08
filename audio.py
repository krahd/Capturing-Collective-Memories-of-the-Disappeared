from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import httpx


DEFAULT_STT_MODEL = "mlx-community/Qwen3-ASR-0.6B-8bit"
DEFAULT_TTS_MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"


@dataclass(frozen=True)
class SpeechConfig:
    base_url: str
    stt_model: str
    tts_model: str
    tts_voice: str
    timeout: float


class SpeechService:
    """Small adapter for an MLX-Audio OpenAI-compatible local server.

    MLX-Audio is intentionally kept out-of-process. This prototype only
    forwards audio and text through its documented HTTP endpoints, so model
    loading, streaming implementations, VAD, and architecture support remain
    upstream concerns rather than being reimplemented here.
    """

    def __init__(self) -> None:
        base = os.getenv("AUDIO_BASE_URL", "http://127.0.0.1:8001/v1")
        self.config = SpeechConfig(
            base_url=base.rstrip("/"),
            stt_model=os.getenv("STT_MODEL", DEFAULT_STT_MODEL),
            tts_model=os.getenv("TTS_MODEL", DEFAULT_TTS_MODEL),
            tts_voice=os.getenv("TTS_VOICE", "Chelsie"),
            timeout=float(os.getenv("AUDIO_TIMEOUT", "120")),
        )

    @property
    def configured(self) -> bool:
        return bool(self.config.base_url and self.config.stt_model and self.config.tts_model)

    async def health(self) -> dict[str, Any]:
        """Best-effort readiness check without loading or downloading models."""

        url = self.config.base_url.removesuffix("/v1") + "/docs"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(url)
            return {
                "ready": response.status_code < 500,
                "endpoint": self.config.base_url,
                "status_code": response.status_code,
            }
        except Exception as exc:
            return {
                "ready": False,
                "endpoint": self.config.base_url,
                "reason": str(exc),
            }

    async def transcribe(
        self,
        audio: bytes,
        *,
        filename: str = "speech.webm",
        content_type: str = "audio/webm",
        language: str | None = "Spanish",
    ) -> str:
        if not audio:
            raise ValueError("No se recibió audio")

        data: dict[str, str] = {"model": self.config.stt_model}
        if language:
            # OpenAI-compatible transcription servers commonly accept a
            # language hint. MLX-Audio ignores unsupported optional fields
            # rather than requiring this prototype to know model internals.
            data["language"] = language

        files = {"file": (filename, audio, content_type or "application/octet-stream")}
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.base_url}/audio/transcriptions",
                data=data,
                files=files,
            )
            response.raise_for_status()
            payload = response.json()

        text = payload.get("text") if isinstance(payload, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("El servicio de reconocimiento no devolvió texto")
        return text.strip()

    async def synthesise(self, text: str) -> tuple[bytes, str]:
        if not text.strip():
            raise ValueError("No hay texto para sintetizar")

        payload = {
            "model": self.config.tts_model,
            "input": text,
            "voice": self.config.tts_voice,
            "response_format": "wav",
        }
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.base_url}/audio/speech",
                json=payload,
            )
            response.raise_for_status()

        content_type = response.headers.get("content-type") or "audio/wav"
        return response.content, content_type
