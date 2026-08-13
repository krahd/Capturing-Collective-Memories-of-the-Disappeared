from pathlib import Path

import httpx

from voice import VoiceService, audio_suffix


def test_voice_service_reports_missing_components(monkeypatch):
    monkeypatch.setenv("WHISPER_CLI", "/missing/whisper-cli")
    monkeypatch.setenv("WHISPER_MODEL", "/missing/model.bin")
    monkeypatch.setenv("PIPER_CLI", "/missing/piper")
    monkeypatch.setenv("PIPER_MODEL", "/missing/voice.onnx")

    service = VoiceService()
    config = service.config()

    assert config["asr_configured"] is False
    assert config["tts_configured"] is False
    assert "whisper-cli" in config["missing"]["asr"]
    assert "PIPER_MODEL" in config["missing"]["tts"]


def test_voice_service_recognises_existing_explicit_paths(tmp_path, monkeypatch):
    executable = tmp_path / "tool"
    model = tmp_path / "model.bin"
    executable.write_text("", encoding="utf-8")
    executable.chmod(0o755)
    model.write_text("", encoding="utf-8")
    monkeypatch.setenv("FFMPEG_CLI", str(executable))
    monkeypatch.setenv("WHISPER_CLI", str(executable))
    monkeypatch.setenv("WHISPER_MODEL", str(model))
    monkeypatch.setenv("PIPER_CLI", str(executable))
    monkeypatch.setenv("PIPER_MODEL", str(model))

    service = VoiceService()

    assert service.asr_configured is True
    assert service.tts_configured is True


def test_browser_audio_mime_types_get_safe_known_suffixes():
    assert audio_suffix("audio/webm; codecs=opus") == ".webm"
    assert audio_suffix("audio/mp4") == ".m4a"
    assert audio_suffix("anything/untrusted") == ".webm"


def test_wav_input_is_converted_to_a_distinct_file(tmp_path, monkeypatch):
    service = VoiceService()
    service.ffmpeg = "/fake/ffmpeg"
    service.whisper_cli = "/fake/whisper-cli"
    service.whisper_model = str(tmp_path / "model.bin")
    calls = []

    def fake_run(command, input_text=None):
        calls.append(command)
        if command[0] == service.whisper_cli:
            output = Path(command[command.index("--output-file") + 1])
            Path(f"{output}.txt").write_text("Una prueba de voz.", encoding="utf-8")

    monkeypatch.setattr(service, "_run", fake_run)

    transcript, _detail = service.transcribe(b"RIFF-test", ".wav")

    ffmpeg = calls[0]
    assert ffmpeg[ffmpeg.index("-i") + 1] != ffmpeg[-1]
    assert transcript == "Una prueba de voz."


def test_resident_whisper_receives_each_turn_without_launching_whisper_cli(tmp_path, monkeypatch):
    service = VoiceService()
    service.ffmpeg = "/fake/ffmpeg"
    service.whisper_cli = "/fake/whisper-cli"
    service.whisper_model = str(tmp_path / "model.bin")
    service._server_ready = True
    calls = []

    def handler(request):
        assert request.url.path == "/inference"
        assert b'filename="converted.wav"' in request.content
        return httpx.Response(200, json={"text": "Una respuesta residente."})

    service._server_client = httpx.Client(transport=httpx.MockTransport(handler))

    def fake_run(command, input_text=None):
        calls.append(command)
        Path(command[-1]).write_bytes(b"RIFF-test")

    monkeypatch.setattr(service, "_run", fake_run)
    transcript, detail = service.transcribe(b"browser audio", ".webm")

    assert transcript == "Una respuesta residente."
    assert detail["resident"] is True
    assert len(calls) == 1
    assert calls[0][0] == service.ffmpeg
    service.close()
