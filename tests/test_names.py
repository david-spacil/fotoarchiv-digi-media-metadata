import json

from fotoarchiv import names

KNOWN = ["Spáčil, David", "Kopáčová, Zuzana"]


def test_suggest_without_diacritics():
    assert names.suggest("spac", KNOWN) == ["Spáčil, David"]
    assert names.suggest("david sp", KNOWN) == ["Spáčil, David"]
    assert names.suggest("KOPAC", KNOWN) == ["Kopáčová, Zuzana"]


def test_check_word_order():
    assert names.check("David Spáčil", KNOWN)["mysleli_jste"] == \
        "Spáčil, David"


def test_check_missing_diacritics():
    assert names.check("Spacil, David", KNOWN)["mysleli_jste"] == \
        "Spáčil, David"


def test_check_known():
    assert names.check("Spáčil, David", KNOWN) == \
        {"znamo": True, "mysleli_jste": None, "prevod": None}


def test_check_new_name_conversion():
    assert names.check("Jan Novák", KNOWN) == \
        {"znamo": False, "mysleli_jste": None, "prevod": "Novák, Jan"}
    assert names.check("Nováková, Eva", KNOWN)["prevod"] is None


def test_index_collects_all_levels(tmp_path):
    doc = {"akce": {"ucastnici": ["A, B"]},
           "skupiny": {"g": {"autori": ["C, D"]}},
           "soubory": {"x.jpg": {"osoby": ["E, F"], "autori": []}}}
    path = tmp_path / "_metadata.json"
    path.write_text(json.dumps(doc))
    index = names.NameIndex(lambda: [path])
    assert index.names() == ["A, B", "C, D", "E, F"]
    doc["akce"]["ucastnici"].append("Nový, Člověk")
    path.write_text(json.dumps(doc))
    import os
    os.utime(path, (1, 1))
    assert "Nový, Člověk" in index.names()
