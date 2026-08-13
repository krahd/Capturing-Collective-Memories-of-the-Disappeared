from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave
from io import BytesIO
from typing import Any


def _resolved_command(env_name: str, default: str) -> str | None:
    configured = os.getenv(env_name)
    if configured:
        path = Path(configured).expanduser()
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None
    return shutil.which(default)


def _resolved_file(env_name: str) -> str | None:
    configured = os.getenv(env_name)
    if not configured:
        return None
    path = Path(configured).expanduser()
    return str(path) if path.is_file() else None


class VoiceService:
    """Thin adapters around local whisper.cpp, ffmpeg and Piper executables."""

    def __init__(self) -> None:
        self.ffmpeg = _resolved_command("FFMPEG_CLI", "ffmpeg")
        self.whisper_cli = _resolved_command("WHISPER_CLI", "whisper-cli")
        self.whisper_model = _resolved_file("WHISPER_MODEL")
        self.whisper_language = os.getenv("WHISPER_LANGUAGE", "es")
        self.piper_cli = _resolved_command("PIPER_CLI", "piper")
        self.piper_model = _resolved_file("PIPER_MODEL")
        try:
            from piper import PiperVoice  # type: ignore[import-not-found]
        except ImportError:
            PiperVoice = None
        self._piper_voice_class = PiperVoice
        self._piper_voice = None
        self.command_timeout = float(os.getenv("VOICE_COMMAND_TIMEOUT", "180"))

    @property
    def asr_configured(self) -> bool:
        return bool(self.ffmpeg and self.whisper_cli and self.whisper_model)

    @property
    def tts_configured(self) -> bool:
        return bool((self._piper_voice_class or self.piper_cli) and self.piper_model)

    def config(self) -> dict[str, Any]:
        return {
            "asr_configured": self.asr_configured,
            "tts_configured": self.tts_configured,
            "half_duplex": True,
            "language": self.whisper_language,
            "missing": {
                "asr": [
                    name
                    for name, value in (
                        ("ffmpeg", self.ffmpeg),
                        ("whisper-cli", self.whisper_cli),
                        ("WHISPER_MODEL", self.whisper_model),
                    )
                    if not value
                ],
                "tts": [
                    name
                    for name, value in (
                        ("piper-tts/PIPER_CLI", self._piper_voice_class or self.piper_cli),
                        ("PIPER_MODEL", self.piper_model),
                    )
                    if not value
                ],
            },
        }

    def transcribe(self, audio: bytes, suffix: str = ".webm") -> tuple[str, dict[str, Any]]:
        if not self.asr_configured:
            raise RuntimeError("La entrada de voz no está configurada")
        if not audio:
            raise RuntimeError("El audio está vacío")

        with tempfile.TemporaryDirectory(prefix="ccm-voice-") as directory:
            root = Path(directory)
            # Browsers may submit WAV directly. Keep source and conversion
            # names distinct even then: ffmpeg refuses an input and output that
            # resolve to the same file.
            source = root / f"source{suffix}"
            wav = root / "converted.wav"
            output_prefix = root / "transcript"
            source.write_bytes(audio)

            self._run(
                [
                    self.ffmpeg or "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(source),
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    str(wav),
                ]
            )
            self._run(
                [
                    self.whisper_cli or "whisper-cli",
                    "--model",
                    self.whisper_model or "",
                    "--file",
                    str(wav),
                    "--language",
                    self.whisper_language,
                    "--no-timestamps",
                    "--output-txt",
                    "--output-file",
                    str(output_prefix),
                ]
            )
            transcript_path = Path(f"{output_prefix}.txt")
            if not transcript_path.exists():
                raise RuntimeError("whisper.cpp no produjo el archivo de transcripción esperado")
            transcript = " ".join(transcript_path.read_text(encoding="utf-8").split())
            if not transcript:
                raise RuntimeError("No se detectó habla en el audio")
            return transcript, {
                "engine": "whisper.cpp",
                "model": Path(self.whisper_model or "").name,
                "language": self.whisper_language,
                "derived_from": "participant_audio",
            }

    def synthesize(self, text: str) -> bytes:
        if not self.tts_configured:
            raise RuntimeError("La salida de voz no está configurada")
        if not text.strip():
            raise RuntimeError("No hay texto para sintetizar")

        if self._piper_voice_class:
            if self._piper_voice is None:
                self._piper_voice = self._piper_voice_class.load(self.piper_model or "")
            output = BytesIO()
            with wave.open(output, "wb") as wav_file:
                self._piper_voice.synthesize_wav(text, wav_file)
            return output.getvalue()

        with tempfile.TemporaryDirectory(prefix="ccm-tts-") as directory:
            output = Path(directory) / "reply.wav"
            self._run(
                [
                    self.piper_cli or "piper",
                    "-m",
                    self.piper_model or "",
                    "-f",
                    str(output),
                    "--",
                    text,
                ]
            )
            if not output.exists() or output.stat().st_size == 0:
                raise RuntimeError("Piper no produjo audio")
            return output.read_bytes()

    def _run(self, command: list[str], input_text: str | None = None) -> None:
        try:
            completed = subprocess.run(
                command,
                input=input_text,
                text=True,
                capture_output=True,
                timeout=self.command_timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"Falló el componente local de voz: {exc}") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "error desconocido").strip()
            raise RuntimeError(f"Falló el componente local de voz: {detail[-600:]}")


def audio_suffix(content_type: str) -> str:
    value = content_type.lower()
    if "ogg" in value:
        return ".ogg"
    if "mp4" in value or "m4a" in value:
        return ".m4a"
    if "wav" in value:
        return ".wav"
    return ".webm"
