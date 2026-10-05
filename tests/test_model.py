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
