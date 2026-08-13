from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import wave
from io import BytesIO
from typing import Any
from urllib.parse import urlparse

import httpx


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


def _flag(env_name: str) -> bool:
    return (os.getenv(env_name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _is_local(url: str) -> bool:
    return (urlparse(url).hostname or "").lower() in {"127.0.0.1", "localhost", "::1", ""}


# A 40 ms silent 16 kHz mono WAV. Small enough to cost nothing, real enough that
# only something that actually transcribes audio will answer it correctly.
_SILENT_WAV = (
    b"RIFF" + (36 + 1280).to_bytes(4, "little") + b"WAVEfmt "
    + (16).to_bytes(4, "little")
    + (1).to_bytes(2, "little")
    + (1).to_bytes(2, "little")
    + (16000).to_bytes(4, "little")
    + (32000).to_bytes(4, "little")
    + (2).to_bytes(2, "little")
    + (16).to_bytes(2, "little")
    + b"data" + (1280).to_bytes(4, "little") + b"\x00" * 1280
)


class VoiceService:
    """Resident local speech services with CLI fallbacks."""

    def __init__(self) -> None:
        self.ffmpeg = _resolved_command("FFMPEG_CLI", "ffmpeg")
        self.whisper_cli = _resolved_command("WHISPER_CLI", "whisper-cli")
        self.whisper_server = _resolved_command("WHISPER_SERVER", "whisper-server")
        self.whisper_model = _resolved_file("WHISPER_MODEL")
        self.whisper_language = os.getenv("WHISPER_LANGUAGE", "es")
        configured_server_url = os.getenv("WHISPER_SERVER_URL")
        self.whisper_server_url = configured_server_url or "http://127.0.0.1:8178/inference"
        # `WHISPER_SERVER_URL` is an address, not an instruction. Reading its mere
        # presence as "somebody else supervises this" made the natural act of
        # uncommenting a whole configuration block silently disable the resident
        # server and fall back to per-turn CLI loads of a multi-gigabyte model —
        # exactly the latency this path exists to remove, and invisible from the
        # interface. Not launching is now either explicit, or forced by an
        # address this process could not have started anyway.
        self._external_server = _flag("WHISPER_SERVER_EXTERNAL") or not _is_local(
            self.whisper_server_url
        )
        self._whisper_process: subprocess.Popen[str] | None = None
        self._server_client: httpx.Client | None = None
        self._server_ready = False
        self.piper_cli = _resolved_command("PIPER_CLI", "piper")
        self.piper_model = _resolved_file("PIPER_MODEL")
        try:
            from piper import PiperVoice  # type: ignore[import-not-found]
        except ImportError:
            PiperVoice = None
        self._piper_voice_class = PiperVoice
        self._piper_voice = None
        self.command_timeout = float(os.getenv("VOICE_COMMAND_TIMEOUT", "180"))
        self.startup_timeout = float(os.getenv("WHISPER_STARTUP_TIMEOUT", "180"))
        self.warm_status: dict[str, Any] = {"attempted": False}

    @property
    def asr_configured(self) -> bool:
        resident = self.whisper_model and (self.whisper_server or self._external_server)
        fallback = self.whisper_model and self.whisper_cli
        return bool(self.ffmpeg and (resident or fallback))

    @property
    def tts_configured(self) -> bool:
        return bool((self._piper_voice_class or self.piper_cli) and self.piper_model)

    def config(self) -> dict[str, Any]:
        try:
            end_of_turn_ms = int(os.getenv("VOICE_END_OF_TURN_MS", "2200"))
        except ValueError:
            end_of_turn_ms = 2200
        end_of_turn_ms = max(1000, min(5000, end_of_turn_ms))
        return {
            "asr_configured": self.asr_configured,
            "tts_configured": self.tts_configured,
            "half_duplex": True,
            "language": self.whisper_language,
            "end_of_turn_ms": end_of_turn_ms,
            "asr_mode": "resident" if self._server_ready else "cli_fallback",
            "tts_mode": "resident" if self._piper_voice is not None else "lazy",
            "warmup": self.warm_status,
            "missing": {
                "asr": [
                    name
                    for name, value in (
                        ("ffmpeg", self.ffmpeg),
                        (
                            "whisper-cli",
                            self.whisper_cli
                            if os.getenv("WHISPER_CLI")
                            else self.whisper_server or self.whisper_cli,
                        ),
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

    def start(self) -> None:
        """Connect to or launch whisper-server so its model is loaded once."""
        if not self.asr_configured or not self.whisper_model:
            return
        self._server_client = httpx.Client(timeout=self.command_timeout)
        # Reuse a service deliberately started outside this process, including
        # one left resident by a supervising demo setup.
        if self._wait_for_server(0.25):
            self._server_ready = True
            return
        if self._external_server or not self.whisper_server:
            self._server_ready = self._wait_for_server(2.0)
            return
        parsed = urlparse(self.whisper_server_url)
        try:
            self._whisper_process = subprocess.Popen(
                [
                    self.whisper_server,
                    "--model",
                    self.whisper_model,
                    "--language",
                    self.whisper_language,
                    "--no-timestamps",
                    "--host",
                    parsed.hostname or "127.0.0.1",
                    "--port",
                    str(parsed.port or 8178),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            self._server_ready = self._wait_for_server(self.startup_timeout)
        except OSError:
            self._server_ready = False
        if not self._server_ready:
            self._stop_server_process()

    def warm(self) -> None:
        """Load the speech-synthesis voice before anybody is waiting on it.

        Recognition and the conversational weights are made resident at startup;
        leaving synthesis lazy meant the first spoken reply — the one moment a
        first impression is actually formed — still paid a model load. One
        discarded sentence moves that cost into startup where it belongs.
        """
        self.warm_status = {"attempted": True, "tts": {"ready": False}}
        if not self.tts_configured:
            self.warm_status["tts"] = {"ready": False, "reason": "no configurado"}
            return
        started = time.perf_counter()
        try:
            audio = self.synthesize("Listo.")
        except Exception as exc:  # a cold voice must not make the archive unavailable
            self.warm_status["tts"] = {"ready": False, "error": str(exc)}
            return
        self.warm_status["tts"] = {
            "ready": bool(audio),
            "engine": "piper-python" if self._piper_voice is not None else "piper-cli",
            "ms": round((time.perf_counter() - started) * 1000),
        }

    def close(self) -> None:
        self._stop_server_process()
        if self._server_client is not None:
            self._server_client.close()
            self._server_client = None
        self._server_ready = False

    def _wait_for_server(self, timeout: float) -> bool:
        """Wait until something at the address actually transcribes audio.

        Reachability is not identity. Accepting any response under 500 from `/`
        meant an unrelated application holding port 8178 could be adopted as the
        resident recogniser, and the mistake would only surface as a failed first
        turn. One silent-WAV inference settles it, and doubles as the first real
        pass through the model.
        """
        if self._server_client is None:
            return False
        parsed = urlparse(self.whisper_server_url)
        health_url = f"{parsed.scheme}://{parsed.netloc}/"
        deadline = time.monotonic() + timeout
        reachable = False
        while time.monotonic() < deadline:
            if self._whisper_process is not None and self._whisper_process.poll() is not None:
                return False
            try:
                response = self._server_client.get(health_url, timeout=1.0)
                if response.status_code < 500:
                    reachable = True
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        if not reachable:
            return False
        return self._inference_answers(max(2.0, deadline - time.monotonic()))

    def _inference_answers(self, timeout: float) -> bool:
        """Confirm the endpoint speaks whisper.cpp's inference protocol."""
        if self._server_client is None:
            return False
        try:
            response = self._server_client.post(
                self.whisper_server_url,
                files={"file": ("probe.wav", _SILENT_WAV, "audio/wav")},
                data={
                    "language": self.whisper_language,
                    "response_format": "json",
                    "no_timestamps": "true",
                },
                timeout=timeout,
            )
            response.raise_for_status()
            # Silence legitimately transcribes to an empty or near-empty string;
            # what matters is that the shape of the answer is the right one.
            return isinstance(response.json().get("text"), str)
        except (httpx.HTTPError, ValueError, AttributeError):
            return False

    def _stop_server_process(self) -> None:
        process = self._whisper_process
        self._whisper_process = None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def transcribe(self, audio: bytes, suffix: str = ".webm") -> tuple[str, dict[str, Any]]:
        if not self.asr_configured:
            raise RuntimeError("La entrada de voz no está configurada")
        if not audio:
            raise RuntimeError("El audio está vacío")

        with tempfile.TemporaryDirectory(prefix="ccm-voice-") as directory:
            total_started = time.perf_counter()
            root = Path(directory)
            # Browsers may submit WAV directly. Keep source and conversion
            # names distinct even then: ffmpeg refuses an input and output that
            # resolve to the same file.
            source = root / f"source{suffix}"
            wav = root / "converted.wav"
            output_prefix = root / "transcript"
            source.write_bytes(audio)

            convert_started = time.perf_counter()
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
            conversion_ms = round((time.perf_counter() - convert_started) * 1000)
            asr_started = time.perf_counter()
            resident = False
            if self._server_ready and self._server_client is not None:
                try:
                    transcript = self._transcribe_resident(wav)
                    resident = True
                except RuntimeError:
                    # A crashed resident should cost at most one CLI fallback,
                    # not the participant's entire turn.
                    self._server_ready = False
                    if not self.whisper_cli:
                        raise
            if not resident:
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
            asr_ms = round((time.perf_counter() - asr_started) * 1000)
            if not transcript:
                raise RuntimeError("No se detectó habla en el audio")
            return transcript, {
                "engine": "whisper.cpp",
                "model": Path(self.whisper_model or "").name,
                "language": self.whisper_language,
                "resident": resident,
                "derived_from": "participant_audio",
                "timings_ms": {
                    "audio_conversion_ms": conversion_ms,
                    "asr_ms": asr_ms,
                    "asr_total_ms": round((time.perf_counter() - total_started) * 1000),
                },
            }

    def _transcribe_resident(self, wav: Path) -> str:
        if self._server_client is None:
            raise RuntimeError("El servicio residente de Whisper no está disponible")
        try:
            with wav.open("rb") as audio_file:
                response = self._server_client.post(
                    self.whisper_server_url,
                    files={"file": (wav.name, audio_file, "audio/wav")},
                    data={
                        "language": self.whisper_language,
                        "response_format": "json",
                        "no_timestamps": "true",
                    },
                )
            response.raise_for_status()
            payload = response.json()
            return " ".join(str(payload.get("text", "")).split())
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError(f"Falló el servicio residente de Whisper: {exc}") from exc

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
