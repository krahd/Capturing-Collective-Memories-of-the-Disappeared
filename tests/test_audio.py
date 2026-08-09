import asyncio

import audio as audio_module
from audio import SpeechService


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None, content=b"wav", content_type="audio/wav"):
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content
        self.headers = {"content-type": content_type}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeAsyncClient:
    posts = []

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.get("timeout")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url):
        return FakeResponse(status_code=200)

    async def post(self, url, **kwargs):
        type(self).posts.append((url, kwargs))
        if url.endswith("/audio/transcriptions"):
            return FakeResponse(payload={"text": "  Me acuerdo de eso.  "})
        return FakeResponse(content=b"RIFF-test", content_type="audio/wav")


def test_speech_defaults_are_small_apple_silicon_models(monkeypatch):
    monkeypatch.delenv("STT_MODEL", raising=False)
    monkeypatch.delenv("TTS_MODEL", raising=False)
    service = SpeechService()

    assert service.config.stt_model == "mlx-community/Qwen3-ASR-0.6B-8bit"
    assert service.config.tts_model == "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit"


def test_transcription_uses_openai_compatible_multipart_endpoint(monkeypatch):
    FakeAsyncClient.posts = []
    monkeypatch.setattr(audio_module.httpx, "AsyncClient", FakeAsyncClient)
    service = SpeechService()

    text = asyncio.run(
        service.transcribe(
            b"audio",
            filename="speech.webm",
            content_type="audio/webm",
        )
    )

    assert text == "Me acuerdo de eso."
    url, kwargs = FakeAsyncClient.posts[-1]
    assert url.endswith("/v1/audio/transcriptions")
    assert kwargs["data"]["model"] == service.config.stt_model
    assert kwargs["data"]["language"] == "Spanish"
    assert kwargs["files"]["file"][0] == "speech.webm"


def test_speech_synthesis_uses_openai_compatible_endpoint(monkeypatch):
    FakeAsyncClient.posts = []
    monkeypatch.setattr(audio_module.httpx, "AsyncClient", FakeAsyncClient)
    service = SpeechService()

    body, content_type = asyncio.run(service.synthesise("Podés contarme un poco más."))

    assert body == b"RIFF-test"
    assert content_type == "audio/wav"
    url, kwargs = FakeAsyncClient.posts[-1]
    assert url.endswith("/v1/audio/speech")
    assert kwargs["json"]["model"] == service.config.tts_model
    assert kwargs["json"]["voice"] == service.config.tts_voice
