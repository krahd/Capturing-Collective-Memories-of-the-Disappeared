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


def test_configuring_the_server_address_does_not_disable_the_resident_server(monkeypatch):
    # Uncommenting a whole voice block used to switch the resident server off,
    # because the presence of an address was read as "somebody else runs this".
    # The result was a silent fall back to reloading a multi-gigabyte model per
    # turn — the exact latency the resident path removes, and invisible from the
    # interface.
    monkeypatch.setenv("WHISPER_SERVER_URL", "http://127.0.0.1:8178/inference")
    monkeypatch.delenv("WHISPER_SERVER_EXTERNAL", raising=False)

    assert VoiceService()._external_server is False

    monkeypatch.setenv("WHISPER_SERVER_EXTERNAL", "1")
    assert VoiceService()._external_server is True


def test_an_unrelated_service_on_the_port_is_not_adopted_as_the_recogniser(monkeypatch):
    # Reachability is not identity. A 404 from something else holding port 8178
    # used to count as proof of Whisper, and the mistake only surfaced as a
    # failed first turn.
    monkeypatch.delenv("WHISPER_SERVER_EXTERNAL", raising=False)
    service = VoiceService()

    def impostor(request):
        if request.url.path == "/":
            return httpx.Response(404, text="Not Found")
        return httpx.Response(200, json={"error": "unknown route"})

    service._server_client = httpx.Client(transport=httpx.MockTransport(impostor))
    assert service._wait_for_server(0.2) is False

    def whisper(request):
        if request.url.path == "/":
            return httpx.Response(200, text="<html>whisper.cpp</html>")
        return httpx.Response(200, json={"text": ""})

    service._server_client = httpx.Client(transport=httpx.MockTransport(whisper))
    assert service._wait_for_server(0.2) is True
    service.close()


def test_speech_voice_is_loaded_at_startup_rather_than_on_the_first_reply(tmp_path, monkeypatch):
    # Everything else is made resident at startup. Leaving synthesis lazy meant
    # the first spoken reply — the only first impression there is — still paid a
    # model load.
    model = tmp_path / "voice.onnx"
    model.write_text("", encoding="utf-8")
    monkeypatch.setenv("PIPER_MODEL", str(model))
    loads = []

    class FakeVoice:
        @staticmethod
        def load(path):
            loads.append(path)
            return FakeVoice()

        def synthesize_wav(self, text, wav_file):
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(b"\x00\x00" * 64)

    service = VoiceService()
    service._piper_voice_class = FakeVoice

    assert service.config()["tts_mode"] == "lazy"
    service.warm()

    assert loads == [str(model)]
    assert service.warm_status["tts"]["ready"] is True
    assert service.config()["tts_mode"] == "resident"

    # A real reply now reuses the loaded voice instead of loading another.
    service.synthesize("Contame.")
    assert len(loads) == 1


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
