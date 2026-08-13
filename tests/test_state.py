import json

import pytest

from state import (
    ACTOR_MODEL,
    ACTOR_PARTICIPANT,
    ACTOR_RESEARCHER,
    ACTOR_SYSTEM,
    ORIGIN_MODEL,
    ORIGIN_RESEARCHER,
    SessionStore,
    export_markdown,
)


def test_session_preserves_exact_transcript_and_roundtrips(tmp_path):
    store = SessionStore(tmp_path)
    session = store.create("Prueba")
    first = session.add_turn("user", "Yo dije 'por el 78', no 1978 seguro.")
    second = session.add_turn("assistant", "¿Qué te hace ubicarlo más o menos por ahí?")
    store.save(session)

    loaded = SessionStore(tmp_path).get(session.id)
    assert loaded.turns[0].text == first.text
    assert loaded.turns[1].text == second.text
    data = json.loads((tmp_path / f"{session.id}.json").read_text(encoding="utf-8"))
    assert data["turns"][0]["text"] == "Yo dije 'por el 78', no 1978 seguro."


def test_ephemeral_session_never_writes_a_json_file(tmp_path):
    store = SessionStore(tmp_path)
    session = store.create(
        "Contribución temporal",
        session_kind="demo_live",
        storage_policy="ephemeral",
        demo_run_id="demo_test",
    )
    session.add_turn("user", "Un recuerdo no sensible.")
    store.save(session)

    assert store.get(session.id) is session
    assert not (tmp_path / f"{session.id}.json").exists()
    assert session in store.list()

    removed = store.discard_demo_run("demo_test")
    assert removed == [session.id]
    assert session not in store.list()


def test_late_background_save_cannot_resurrect_a_cleaned_demo_run(tmp_path):
    store = SessionStore(tmp_path)
    session = store.create(
        "Contribución temporal",
        session_kind="demo_live",
        storage_policy="ephemeral",
        demo_run_id="demo_closed",
    )

    store.discard_demo_run("demo_closed")
    session.add_turn("user", "Una extracción terminó después de la limpieza.")
    store.save(session)

    with pytest.raises(KeyError):
        store.get(session.id)
    assert session not in store.list()
    assert not (tmp_path / f"{session.id}.json").exists()


def test_interview_move_metadata_roundtrips_and_exports(tmp_path):
    store = SessionStore(tmp_path)
    session = store.create("Ritmo")
    participant = session.add_turn("user", "Una vez llegó con una bolsa de libros.")
    assistant = session.add_turn(
        "assistant",
        "¿Qué pasó con esos libros?",
        move="FOLLOW_UP",
        grounded_in=[participant.id],
        record_kind="interview_move",
    )
    store.save(session)

    loaded = SessionStore(tmp_path).get(session.id)
    loaded_assistant = next(turn for turn in loaded.turns if turn.id == assistant.id)
    assert loaded_assistant.move == "FOLLOW_UP"
    assert loaded_assistant.grounded_in == [participant.id]

    markdown = export_markdown(loaded)
    assert "Conversación · FOLLOW_UP" in markdown
    assert f"Movimiento fundamentado en: `{participant.id}`" in markdown


def test_annotations_and_derived_material_require_source_turns(tmp_path):
    store = SessionStore(tmp_path)
    session = store.create()
    turn = session.add_turn("user", "Creo que le decían el Vasco, pero eso me llegó por mi madre.")

    ann = session.add_annotation([turn.id], "hearsay", "La fuente declarada es la madre.")
    item = session.add_derived_item("entity", "Persona conocida como 'el Vasco'", [turn.id])

    assert ann.source_turn_ids == [turn.id]
    assert item.source_turn_ids == [turn.id]
    with pytest.raises(ValueError):
        session.add_derived_item("entity", "Sin fuente", [])
    with pytest.raises(ValueError):
        session.add_annotation(["turn_missing"], "uncertain")


def test_correction_relation_keeps_both_records(tmp_path):
    session = SessionStore(tmp_path).create()
    old = session.add_turn("user", "Era en La Teja.")
    correction = session.add_turn("user", "No, pará, me confundí: era en el Cerro.")
    old_item = session.add_derived_item("place", "La Teja", [old.id])
    new_item = session.add_derived_item("correction", "La persona corrige el lugar a el Cerro", [correction.id])
    rel = session.add_relation("corrects", new_item.id, old_item.id)

    assert rel.source_id == new_item.id
    assert rel.target_id == old_item.id
    assert len(session.derived_items) == 2


def test_derived_item_is_editable_without_changing_transcript(tmp_path):
    session = SessionStore(tmp_path).create()
    turn = session.add_turn("user", "Fue después de carnaval, me parece.")
    item = session.add_derived_item("time", "Después de carnaval", [turn.id])
    original = turn.text
    session.update_derived_item(item.id, text="Momento recordado como posterior a carnaval", status="reviewed")

    assert session.turns[0].text == original
    assert item.status == "reviewed"
    assert "posterior" in item.text


def test_deleting_derived_item_preserves_transcript_and_removes_dangling_relations(tmp_path):
    session = SessionStore(tmp_path).create()
    turn = session.add_turn("user", "Primero dije La Teja, pero después me corregí.")
    item = session.add_derived_item("place", "La Teja", [turn.id])
    other = session.add_derived_item("correction", "Corrección posterior", [turn.id])
    session.add_relation("corrects", other.id, item.id)
    original = turn.text

    deleted = session.delete_derived_item(item.id)

    assert deleted.id == item.id
    assert all(candidate.id != item.id for candidate in session.derived_items)
    assert session.relations == []
    assert session.turns[0].text == original


def test_markdown_export_contains_exact_turn_ids_and_provisional_warning(tmp_path):
    session = SessionStore(tmp_path).create("Memoria")
    turn = session.add_turn("user", "No sé si fue martes o miércoles.")
    session.add_annotation([turn.id], "uncertain")
    md = export_markdown(session)

    assert turn.id in md
    assert "No sé si fue martes o miércoles." in md
    assert "provisional" in md.lower()


def test_participant_turn_is_not_trimmed_or_normalised(tmp_path):
    session = SessionStore(tmp_path).create()
    original = "  Capaz que era el 78... no sé.  "
    turn = session.add_turn("user", original)
    assert turn.text == original


def test_model_derived_material_is_distinguishable_from_researcher_material(tmp_path):
    session = SessionStore(tmp_path).create()
    turn = session.add_turn("user", "Del Flaco me contó mi vieja, yo no me acuerdo.")
    provenance = {"model": "qwen3-30b-a3b-instruct-2507", "temperature": 0.7, "top_p": 0.8}

    mine = session.add_derived_item("hearsay", "La fuente es la madre", [turn.id])
    theirs = session.add_derived_item(
        "entity", "el Flaco", [turn.id], origin=ORIGIN_MODEL, origin_detail=provenance
    )

    assert mine.origin == ORIGIN_RESEARCHER
    assert mine.origin_detail == {}
    assert theirs.origin == ORIGIN_MODEL
    assert theirs.origin_detail["model"] == "qwen3-30b-a3b-instruct-2507"
    # The exact sampling settings travel with the interpretation.
    assert theirs.origin_detail["temperature"] == 0.7


def test_editing_records_a_revision_instead_of_overwriting_silently(tmp_path):
    session = SessionStore(tmp_path).create()
    turn = session.add_turn("user", "Fue después de carnaval, me parece.")
    item = session.add_derived_item("time", "Después de carnaval", [turn.id])

    session.update_derived_item(item.id, text="Momento posterior a carnaval, sin fecha")

    assert len(item.revisions) == 1
    assert item.revisions[0].field == "text"
    assert item.revisions[0].before == "Después de carnaval"
    assert item.revisions[0].after == "Momento posterior a carnaval, sin fecha"
    assert session.turns[0].text == "Fue después de carnaval, me parece."


def test_unchanged_fields_do_not_generate_revisions(tmp_path):
    session = SessionStore(tmp_path).create()
    turn = session.add_turn("user", "Era en el Cerro.")
    item = session.add_derived_item("place", "el Cerro", [turn.id])

    session.update_derived_item(item.id, text="el Cerro", status="provisional")

    assert item.revisions == []


def test_withdrawal_retains_the_material_and_the_reason(tmp_path):
    session = SessionStore(tmp_path).create()
    turn = session.add_turn("user", "De eso no quiero hablar.")
    item = session.add_derived_item(
        "event", "Detención del tío", [turn.id], origin=ORIGIN_MODEL
    )

    session.withdraw_derived_item(item.id, "La persona no dijo esto; el modelo lo infirió.")

    assert item in session.derived_items
    assert item.withdrawn is True
    assert item.text == "Detención del tío"
    assert "el modelo lo infirió" in item.withdrawn_reason
    assert session.summary()["retiradas"] == 1
    assert session.summary()["interpretaciones"] == 0


def test_purging_leaves_a_trace_but_does_not_retain_the_text(tmp_path):
    session = SessionStore(tmp_path).create()
    turn = session.add_turn("user", "Algo que después se borra.")
    item = session.add_derived_item("other", "Texto que no debe sobrevivir", [turn.id])

    session.delete_derived_item(item.id)

    purge = [e for e in session.events if e.action == "interpretacion_eliminada"]
    assert len(purge) == 1
    # Deliberate destruction stays destructive.
    assert "Texto que no debe sobrevivir" not in json.dumps(session.to_dict(), ensure_ascii=False)
    assert purge[0].target_id == item.id


def test_session_record_attributes_each_action_to_an_actor(tmp_path):
    session = SessionStore(tmp_path).create()
    participant = session.add_turn("user", "Yo era chico.")
    session.add_turn("assistant", "¿Qué te acordás de esa época?")
    session.add_derived_item("theme", "Infancia", [participant.id])

    actors = {e.action: e.actor for e in session.events}
    assert actors["sesion_creada"] == ACTOR_SYSTEM
    assert actors["interpretacion_creada"] == ACTOR_RESEARCHER
    turn_events = [e for e in session.events if e.action == "turno_registrado"]
    assert [e.actor for e in turn_events] == [ACTOR_PARTICIPANT, ACTOR_MODEL]


def test_sessions_written_before_the_audit_layer_still_load(tmp_path):
    legacy = {
        "id": "session_legacy01",
        "title": "Sesión vieja",
        "turns": [{"id": "turn_1", "role": "user", "text": "Era por el 78.", "created_at": "2026-01-01T00:00:00+00:00"}],
        "annotations": [],
        "derived_items": [
            {
                "id": "item_1",
                "kind": "time",
                "text": "1978 aproximado",
                "source_turn_ids": ["turn_1"],
                "status": "provisional",
                "note": "",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ],
        "relations": [],
    }
    (tmp_path / "session_legacy01.json").write_text(json.dumps(legacy), encoding="utf-8")

    loaded = SessionStore(tmp_path).get("session_legacy01")

    assert loaded.turns[0].text == "Era por el 78."
    assert loaded.events == []
    assert loaded.is_recorded is False
    item = loaded.derived_items[0]
    assert item.origin == ORIGIN_RESEARCHER
    assert item.revisions == []
    assert item.withdrawn is False


def test_markdown_export_records_origin_withdrawal_and_the_session_log(tmp_path):
    session = SessionStore(tmp_path).create("Memoria")
    turn = session.add_turn("user", "Del Flaco me contó mi vieja.")
    session.add_derived_item(
        "entity", "el Flaco", [turn.id], origin=ORIGIN_MODEL, origin_detail={"model": "qwen3-2507"}
    )
    retired = session.add_derived_item("event", "Una inferencia de más", [turn.id])
    session.withdraw_derived_item(retired.id, "No lo dijo la persona.")

    md = export_markdown(session)

    assert "[modelo · qwen3-2507]" in md
    assert "~~Una inferencia de más~~" in md
    assert "Retirada, no eliminada: No lo dijo la persona." in md
    assert "## Registro de la sesión" in md
