import json

import pytest

from state import SessionStore, export_markdown


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
