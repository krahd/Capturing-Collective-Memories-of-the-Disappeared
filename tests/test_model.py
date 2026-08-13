import asyncio
import json

from model import (
    EXTRACTION_POLICY,
    ConversationGate,
    LLMClient,
    URUGUAYAN_CONVERSATION_POLICY,
    conversation_messages,
    opening_message,
)


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


def test_conversation_messages_treat_participant_text_as_data_without_changing_it():
    turns = [
        {"role": "user", "text": "Bo, no; dije 'capaz que', no que estaba seguro."},
        {"role": "assistant", "text": "Sí, te entendí: lo dejás como una posibilidad."},
    ]
    messages = conversation_messages(turns)
    payload = json.loads(messages[1]["content"])
    assert payload["participant_utterance"] == turns[0]["text"]
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


def test_generation_options_are_absent_by_default(monkeypatch):
    monkeypatch.delenv("LLM_TEMPERATURE", raising=False)
    monkeypatch.delenv("LLM_TOP_P", raising=False)
    monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)

    client = LLMClient()

    assert client._generation_options() == {}


def test_generation_options_can_be_fixed_for_comparable_runs(monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", "0.7")
    monkeypatch.setenv("LLM_TOP_P", "0.8")
    monkeypatch.setenv("LLM_MAX_TOKENS", "256")

    client = LLMClient()

    assert client._generation_options() == {
        "temperature": 0.7,
        "top_p": 0.8,
        "max_tokens": 256,
    }


def test_extraction_does_not_inherit_the_short_conversational_token_cap(monkeypatch):
    # The conversational cap is deliberately small; reusing it for extraction
    # truncates the JSON mid-string.
    monkeypatch.setenv("LLM_MAX_TOKENS", "256")
    monkeypatch.delenv("LLM_EXTRACTION_MAX_TOKENS", raising=False)

    client = LLMClient()

    assert client._generation_options()["max_tokens"] == 256
    assert client._generation_options(client.extraction_max_tokens)["max_tokens"] == 1536


def test_provenance_reports_the_settings_actually_used(monkeypatch):
    monkeypatch.setenv("LLM_API_URL", "http://127.0.0.1:11434/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "qwen3:30b-a3b-instruct-2507-q4_K_M")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.7")
    monkeypatch.setenv("LLM_TOP_P", "0.8")
    monkeypatch.setenv("LLM_MAX_TOKENS", "256")

    client = LLMClient()

    conversation = client.provenance()
    extraction = client.provenance(for_extraction=True)

    assert conversation["model"] == "qwen3:30b-a3b-instruct-2507-q4_K_M"
    assert conversation["local"] is True
    assert conversation["endpoint"] == "http://127.0.0.1:11434"
    assert conversation["max_tokens"] == 256
    assert extraction["max_tokens"] == 1536


def test_a_separate_extraction_model_is_attributed_to_itself(monkeypatch):
    # Interpretations must name the model that actually produced them, not the
    # conversational one that happens to be configured alongside it.
    monkeypatch.setenv("LLM_API_URL", "http://127.0.0.1:11434/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "qwen3:30b-a3b-instruct-2507-q4_K_M")
    monkeypatch.setenv("LLM_EXTRACTION_MODEL", "llama3.2:latest")

    client = LLMClient()

    assert client.provenance()["model"] == "qwen3:30b-a3b-instruct-2507-q4_K_M"
    assert client.provenance(for_extraction=True)["model"] == "llama3.2:latest"


def test_extraction_model_defaults_to_the_conversational_one(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "one-model")
    monkeypatch.delenv("LLM_EXTRACTION_MODEL", raising=False)

    client = LLMClient()

    assert client.extraction_model is None
    assert client.provenance(for_extraction=True)["model"] == "one-model"


def test_extraction_asks_for_person_explicitly_and_keeps_entity_generic():
    policy = EXTRACTION_POLICY.lower()
    assert "person" in policy
    assert "`person` sólo para seres humanos" in policy
    assert "ante la duda usá `entity`" in policy


def test_gate_waits_for_a_conversational_call_to_finish_and_settle():
    async def scenario():
        gate = ConversationGate(settle_seconds=0.05)
        waiter = asyncio.create_task(gate.wait_until_idle(timeout=5))

        async with gate.conversing():
            await asyncio.sleep(0.1)
            # Background work must not have started while the participant waits.
            assert not waiter.done()

        assert await waiter is True

    asyncio.run(scenario())


def test_gate_gives_up_rather_than_never_extracting():
    # A participant who keeps talking can hold the model busy indefinitely.
    # Growing the field late beats never growing it.
    async def scenario():
        gate = ConversationGate(settle_seconds=0.05)
        async with gate.conversing():
            assert await gate.wait_until_idle(timeout=0.1) is False

    asyncio.run(scenario())


def test_gate_is_idle_before_anything_has_been_asked_of_the_model():
    assert asyncio.run(ConversationGate(settle_seconds=0).wait_until_idle(timeout=1)) is True


def test_policy_addresses_observed_hearsay_and_register_failures():
    policy = URUGUAYAN_CONVERSATION_POLICY.lower()
    # Added after a live run in which the model asked what someone sounded like
    # right after the participant said they did not remember them.
    assert "no le preguntes por detalles que sólo tendría si lo hubiera vivido" in policy
    assert "no repitas la misma fórmula de pregunta" in policy
    # Added after a live run in which an acknowledgement reported that the
    # participant's mother "recordaba bien" what she had only been said to talk
    # about. Acknowledgements assert without asking, so they evade the
    # leading-question rules entirely.
    assert "preferí backchannel o invite_continue" in policy
    assert "conservá la distancia que puso la persona" in policy


def test_policy_allows_floor_yielding_moves_without_forced_questions():
    policy = URUGUAYAN_CONVERSATION_POLICY.lower()
    for move in ["backchannel", "invite_continue", "follow_up", "clarify", "acknowledge"]:
        assert move in policy
    assert "no lleva pregunta" in policy
    assert "no debés preferir una pregunta por defecto" in policy
    assert "una única intervención completa, lista para mostrar sin reescritura" in policy
