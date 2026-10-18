import json

from fotoarchiv import names

KNOWN = ["Příkladný, Daniel", "Modelová, Zuzana"]


def test_suggest_without_diacritics():
    assert names.suggest("prikl", KNOWN) == ["Příkladný, Daniel"]
    assert names.suggest("daniel pr", KNOWN) == ["Příkladný, Daniel"]
    assert names.suggest("MODEL", KNOWN) == ["Modelová, Zuzana"]


def test_check_word_order():
    assert names.check("Daniel Příkladný", KNOWN)["mysleli_jste"] == \
        "Příkladný, Daniel"


def test_check_missing_diacritics():
    assert names.check("Prikladny, Daniel", KNOWN)["mysleli_jste"] == \
        "Příkladný, Daniel"


def test_check_known():
    assert names.check("Příkladný, Daniel", KNOWN) == \
        {"znamo": True, "mysleli_jste": None, "prevod": None}


def test_check_new_name_conversion():
    assert names.check("Jan Novák", KNOWN) == \
        {"znamo": False, "mysleli_jste": None, "prevod": "Novák, Jan"}
    assert names.check("Nováková, Eva", KNOWN)["prevod"] is None


def test_index_collects_all_levels(tmp_path):
    doc = {"akce": {"ucastnici": ["A, B"]},
           "skupiny": {"g": {"autori": ["C, D"]}},
           "soubory": {"x.jpg": {"osoby": ["X, Y"], "autori": [],
                                 "obliceje": [{"jmeno": "E, F",
                                               "oblast": [0, 0, 0, 0]}]}}}
    path = tmp_path / "_metadata.json"
    path.write_text(json.dumps(doc))
    index = names.NameIndex(lambda: [path])
    assert index.names() == ["A, B", "C, D", "E, F"]
    doc["akce"]["ucastnici"].append("Nový, Člověk")
    path.write_text(json.dumps(doc))
    import os
    os.utime(path, (1, 1))
    assert "Nový, Člověk" in index.names()


def test_known_form():
    known = ["Vzorný, Tomáš", "Tomáš Vzorný", "Příkladný, Daniel"]
    assert names.known_form("Tomáš Vzorný", known) == "Vzorný, Tomáš"
    assert names.known_form("tomas  vzorny", known) == "Vzorný, Tomáš"
    assert names.known_form("Rudolf Smyšlený", known) == "Rudolf Smyšlený"
