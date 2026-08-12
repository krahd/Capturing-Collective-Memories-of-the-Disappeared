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
