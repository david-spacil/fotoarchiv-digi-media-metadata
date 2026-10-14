import json
from pathlib import Path

import pytest

from fotoarchiv import model

FIXTURES = sorted((Path(__file__).parent / "fixtures" / "inheritance")
                  .glob("*.json"))


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_inheritance_fixtures(path):
    case = json.loads(path.read_text(encoding="utf-8"))
    for filename, expected in case["ocekavano"].items():
        assert model.resolve(case["metadata"], filename) == expected


def test_new_document_prefill():
    files = [
        {"nazev": "a.jpg", "datum": "2026-04-28T15:00:00",
         "pristroj": "x", "gps": None},
        {"nazev": "b.jpg", "datum": "2026-04-29T09:00:00",
         "pristroj": "x", "gps": [49.0, 16.0]},
        {"nazev": "c.jpg", "datum": None, "pristroj": None, "gps": None},
    ]
    groups = {"skupiny": {"x": {"nazev": "x"}},
              "prirazeni": {"a.jpg": "x", "b.jpg": "x", "c.jpg": "x"}}
    doc = model.new_document(
        "2026-04-28 kontrola Stezky Drahanskou vrchovinou", files, groups)
    assert doc["schema"] == "fotoarchiv-digi-media-metadata/1"
    assert doc["akce"] == {"nazev": "kontrola Stezky Drahanskou vrchovinou",
                           "datum_od": "2026-04-28",
                           "datum_do": "2026-04-29"}
    assert doc["soubory"]["b.jpg"] == {"datum": "2026-04-29T09:00:00",
                                       "pristroj": "x", "gps": [49.0, 16.0],
                                       "skupina": "x"}


def test_new_document_date_from_folder():
    doc = model.new_document("2026-04-28 x", [],
                             {"skupiny": {}, "prirazeni": {}})
    assert doc["akce"]["datum_od"] == doc["akce"]["datum_do"] == "2026-04-28"


def test_merge_scan_keeps_manual_and_adds_new():
    doc = {"soubory": {
        "a.jpg": {"skupina": "g", "datum": "2026-04-28T10:00:00",
                  "popis": "ručně"},
        "zmizel.jpg": {"skupina": "g"},
    }}
    files = [
        {"nazev": "a.jpg", "datum": "2026-04-28T09:00:00",
         "pristroj": "x", "gps": None},
        {"nazev": "novy.jpg", "datum": "2026-04-28T11:00:00",
         "pristroj": "x", "gps": None},
    ]
    added, missing = model.merge_scan(doc, files)
    assert added == ["novy.jpg"]
    assert missing == ["zmizel.jpg"]
    assert doc["soubory"]["a.jpg"]["datum"] == "2026-04-28T10:00:00"
    assert doc["soubory"]["a.jpg"]["popis"] == "ručně"
    assert "skupina" not in doc["soubory"]["novy.jpg"]
    assert doc["soubory"]["novy.jpg"]["datum"] == "2026-04-28T11:00:00"
    assert "zmizel.jpg" in doc["soubory"]


def test_merge_scan_nfc_nfd():
    doc = {"soubory": {"č.jpg": {}}}                 # č v NFC
    added, missing = model.merge_scan(
        doc, [{"nazev": "č.jpg"}])                  # č v NFD
    assert added == [] and missing == []


def test_unknown_technical_values_not_stored():
    # Neznámý přístroj nesmí přepsat přístroj zděděný ze skupiny.
    files = [{"nazev": "v.mp4", "datum": "2026-04-28T14:49:02",
              "pristroj": None, "gps": None}]
    groups = {"skupiny": {"s": {"nazev": "S", "pristroj": "samsung"}},
              "prirazeni": {"v.mp4": "s"}}
    doc = model.new_document("2026-04-28 x", files, groups)
    assert doc["soubory"]["v.mp4"] == {"datum": "2026-04-28T14:49:02",
                                       "skupina": "s"}
    assert model.resolve(doc, "v.mp4")["pristroj"]["uroven"] == "skupina"
    doc2 = {"soubory": {}}
    model.merge_scan(doc2, files)
    assert doc2["soubory"]["v.mp4"] == {"datum": "2026-04-28T14:49:02"}


def test_clean_drops_legacy_people_and_misplaced_faces():
    face = {"jmeno": "Hlava, Miloš", "oblast": [0.5, 0.4, 0.08, 0.06]}
    doc = {"akce": {"nazev": "x", "osoby": ["A, B"], "obliceje": [face]},
           "skupiny": {"g": {"osoby": ["A, B"], "obliceje": [face]}},
           "soubory": {"a.jpg": {"osoby": ["A, B"], "obliceje": [face]}}}
    model.clean(doc)
    assert doc == {"akce": {"nazev": "x"}, "skupiny": {"g": {}},
                   "soubory": {"a.jpg": {"obliceje": [face]}}}


def test_keep_faces_from_stored_version():
    face = {"jmeno": "Hlava, Miloš", "oblast": [0.5, 0.4, 0.08, 0.06]}
    stored = {"soubory": {"a.jpg": {"obliceje": [face]}, "b.jpg": {}}}
    doc = {"soubory": {"a.jpg": {"popis": "x"},
                       "b.jpg": {"obliceje": [face]}}}
    model.keep_faces(doc, stored)
    assert doc == {"soubory": {"a.jpg": {"popis": "x", "obliceje": [face]},
                               "b.jpg": {}}}


def test_incomplete_authors_only_on_event():
    doc = {"akce": {"autori": ["Spáčil, David"]},
           "skupiny": {"g9": {"nazev": "G9"}},
           "soubory": {"P1503712.JPG": {"skupina": "g9"},
                       "IMG-20260428-WA0001.jpg": {}}}
    present = {"P1503712.JPG", "IMG-20260428-WA0001.jpg"}
    assert "autori" not in model.incomplete(doc, present)


def test_completeness_counts_per_field():
    # Scénář Rozpracovaná akce s mezerami: 40 souborů, 2 k vyřazení.
    soubory = {}
    for i in range(40):
        record = {"skupina": "g"}
        if i < 30:
            record["datum"] = "2026-04-28T10:00:00"
        if i < 10:
            record["misto"] = "Brno"
        soubory[f"{i:02}.jpg"] = record
    soubory["38.jpg"]["vyradit"] = True
    soubory["39.jpg"]["vyradit"] = True
    doc = {"akce": {"mista": ["Brno", "Praha"]},
           "skupiny": {"g": {"autori": ["Novák, Jan"]}},
           "soubory": soubory}
    hotovost = model.completeness(doc, set(soubory))
    assert hotovost == {"autori": [38, 38], "datum": [30, 38],
                        "misto": [10, 38]}
    assert model.incomplete(doc, set(soubory)) == ["datum", "misto"]


def test_completeness_place_inherited_from_event():
    soubory = {f"{i}.jpg": {} for i in range(20)}
    doc = {"akce": {"mista": ["Brno"]}, "soubory": soubory}
    assert model.completeness(doc, set(soubory))["misto"] == [20, 20]


def test_completeness_only_present_files():
    doc = {"soubory": {"a.jpg": {"datum": "x"}, "zmizel.jpg": {}}}
    assert model.completeness(doc, {"a.jpg", "jen_na_disku.jpg"}) == {
        "autori": [0, 1], "datum": [1, 1], "misto": [0, 1]}


def test_touch_first_save():
    doc = {"akce": {}}
    model.touch(doc, None, "Spáčil, David", "2026-10-14T10:15:02")
    assert doc["upravili"] == {"Spáčil, David": "2026-10-14T10:15:02"}


def test_touch_second_user_keeps_first():
    stored = {"upravili": {"Spáčil, David": "2026-10-14T10:15:02"}}
    doc = {}
    model.touch(doc, stored, "Kopáčová, Zuzana", "2026-10-14T11:00:00")
    assert doc["upravili"] == {"Spáčil, David": "2026-10-14T10:15:02",
                               "Kopáčová, Zuzana": "2026-10-14T11:00:00"}
    # Uložená verze se nemění.
    assert stored["upravili"] == {"Spáčil, David": "2026-10-14T10:15:02"}


def test_touch_ignores_client_value():
    stored = {"upravili": {"Spáčil, David": "2026-10-14T10:15:02"}}
    doc = {"upravili": {"Podvržený, Pán": "2030-01-01T00:00:00",
                        "Spáčil, David": "2030-01-01T00:00:00"}}
    model.touch(doc, stored, "Kopáčová, Zuzana", "2026-10-14T11:00:00")
    assert doc["upravili"] == {"Spáčil, David": "2026-10-14T10:15:02",
                               "Kopáčová, Zuzana": "2026-10-14T11:00:00"}


USER = {"jmeno": "Kopáčová, Zuzana", "admin": False, "archivar": False}
ARCHIVAR = {"jmeno": "Novák, Petr", "admin": False, "archivar": True}


def test_can_edit_by_editors():
    doc = {"upravili": {"Spáčil, David": "2026-10-14T10:15:02"}}
    assert not model.can_edit(USER, doc)
    doc["upravili"]["Kopáčová, Zuzana"] = "2026-10-14T10:16:00"
    assert model.can_edit(USER, doc)


def test_can_edit_name_without_diacritics():
    doc = {"upravili": {"Kopacova, Zuzana": "2026-10-14T10:15:02"}}
    assert model.can_edit(USER, doc)
    doc = {"upravili": {"zuzana kopacova": "2026-10-14T10:15:02"}}
    assert model.can_edit(USER, doc)


def test_can_edit_without_editors_only_archivist():
    for doc in (None, {}, {"upravili": None}):
        assert not model.can_edit(USER, doc)
        assert model.can_edit(ARCHIVAR, doc)
