from model import LLMClient, URUGUAYAN_CONVERSATION_POLICY, conversation_messages, opening_message


def test_opening_is_open_and_uses_uruguayan_voseo():
    text = opening_message()
    assert "Podés" in text
    assert "por donde quieras" in text
    assert text.count("?") == 1


def test_policy_encodes_non_questionnaire_and_uncertainty_requirements():
    policy = URUGUAYAN_CONVERSATION_POLICY.lower()
    for phrase in [
        "español rioplatense natural para uruguay",
        "no recorras una lista de preguntas",
        "no hagas dos o tres preguntas juntas",
        "permití digresiones",
        "preservá esa incertidumbre",
        "no hagas fact checking",
        "no debe parecer un cuestionario",
    ]:
        assert phrase in policy


def test_conversation_messages_keep_turn_text_exactly():
    turns = [
        {"role": "user", "text": "Bo, no; dije 'capaz que', no que estaba seguro."},
        {"role": "assistant", "text": "Sí, te entendí: lo dejás como una posibilidad."},
    ]
    messages = conversation_messages(turns)
    assert messages[1]["content"] == turns[0]["text"]
    assert messages[2]["content"] == turns[1]["text"]


def test_local_openai_compatible_endpoint_does_not_require_api_key(monkeypatch):
    monkeypatch.setenv("LLM_API_URL", "http://127.0.0.1:11434/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "local-model")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    client = LLMClient()

    assert client.configured is True
    assert client.api_key is None


def test_default_openai_endpoint_still_requires_api_key(monkeypatch):
    monkeypatch.delenv("LLM_API_URL", raising=False)
    monkeypatch.setenv("LLM_MODEL", "gpt-model")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    client = LLMClient()

    assert client.configured is False
