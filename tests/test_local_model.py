import asyncio

import local_model as local_model_module
from local_model import LLMClient
from modelito.messages import Response


class FakeModelitoClient:
    provider_name = "BaseRTProvider"
    model = "gemma-4-12B"

    def chat(self, messages, settings=None):
        assert messages[0]["role"] == "system"
        return Response(text="Seguí, te escucho.")


def test_local_client_passes_mac_runtime_candidates(monkeypatch):
    called = {}

    def fake_local_client(**kwargs):
        called.update(kwargs)
        return FakeModelitoClient()

    monkeypatch.setattr(local_model_module, "local_client", fake_local_client)
    monkeypatch.setenv("MODELITO_LOCAL_PROFILE", "mac-performance")
    monkeypatch.setenv("LOCAL_MODEL_BASERT", "gemma-4-12B")
    monkeypatch.setenv("LOCAL_MODEL_OMLX", "mlx-community/gemma-4-12B-4bit")
    monkeypatch.setenv("LOCAL_MODEL_OLLAMA", "gemma4:12b-mlx")

    client = LLMClient()
    reply = asyncio.run(client.chat([{"role": "user", "text": "Me acuerdo de una cosa."}]))

    assert reply == "Seguí, te escucho."
    assert called["profile"] == "mac-performance"
    assert called["models"] == {
        "basert": "gemma-4-12B",
        "omlx": "mlx-community/gemma-4-12B-4bit",
        "ollama": "gemma4:12b-mlx",
    }
    assert client.provider == "basert"


def test_portable_profile_can_force_ollama_order(monkeypatch):
    called = {}

    def fake_local_client(**kwargs):
        called.update(kwargs)
        client = FakeModelitoClient()
        client.provider_name = "OllamaProvider"
        client.model = "gemma4:12b-mlx"
        return client

    monkeypatch.setattr(local_model_module, "local_client", fake_local_client)
    monkeypatch.setenv("MODELITO_LOCAL_PROFILE", "portable")
    monkeypatch.setenv("MODELITO_LOCAL_PREFER", "ollama")

    client = LLMClient()
    status = asyncio.run(client.status())

    assert status["ready"] is True
    assert status["provider"] == "ollama"
    assert called["profile"] == "portable"
    assert called["prefer"] == ["ollama"]
