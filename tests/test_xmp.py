import json
import xml.etree.ElementTree as ET

import pytest

from fotoarchiv import xmp
from fotoarchiv.archive import Workspace
from .conftest import make_tree, snapshot

EVENT = "2026-04-28 kontrola Stezky"
NS = {"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
      "dc": "http://purl.org/dc/elements/1.1/",
      "xmp": "http://ns.adobe.com/xap/1.0/",
      "exif": "http://ns.adobe.com/exif/1.0/",
      "digiKam": "http://www.digikam.org/ns/1.0/"}


def doc_with(**soubory):
    return {
        "schema": "fotoarchiv-digi-media-metadata/1",
        "dokonceno": None,
        "akce": {"nazev": "kontrola", "mista": ["Holštejn"],
                 "ucastnici": ["Účastník, Jan"]},
        "souradnice_mist": {"Holštejn": {"gps": [49.4063, 16.7777]}},
        "skupiny": {"g9": {"nazev": "G9",
                           "autori": ["Spáčil, David", "Kopáčová, Zuzana"],
                           "pristroj": "Panasonic DC-G9"}},
        "soubory": soubory,
    }


def parse(text):
    desc = ET.fromstring(text).find("rdf:RDF/rdf:Description", NS)
    get = lambda path: desc.find(path, NS)  # noqa: E731
    popis = get("dc:description/rdf:Alt/rdf:li")
    datum = get("xmp:CreateDate")
    lat, lon = get("exif:GPSLatitude"), get("exif:GPSLongitude")
    return {
        "popis": popis.text if popis is not None else None,
        "datum": datum.text if datum is not None else None,
        "gps": (lat.text, lon.text) if lat is not None else None,
        "tagy": [li.text for li in
                 desc.findall("digiKam:TagsList/rdf:Bag/rdf:li", NS)],
    }


def test_inherited_authors_place_gps_and_event_tag():
    doc = doc_with(**{"P1503712.JPG": {
        "skupina": "g9", "datum": "2026-04-28T09:44:36",
        "osoby": ["Novák, Petr", "Novák, Petr", "A/B"]}})
    text = xmp.sidecar(doc, EVENT, "P1503712.JPG")
    r = parse(text)
    assert r["tagy"] == [f"akce/{EVENT}", "autor/Spáčil, David",
                         "autor/Kopáčová, Zuzana", "osoba/Novák, Petr",
                         "osoba/A-B"]
    assert r["gps"] == ("49,24.378000N", "16,46.662000E")
    assert r["datum"] == "2026-04-28T09:44:36+02:00"
    assert r["popis"] is None
    for leaked in ("Holštejn", "Panasonic", "Účastník", "G9"):
        assert leaked not in text


def test_escaping_and_empty_fields():
    doc = doc_with(**{"a.jpg": {"popis": 'A & <b> "c"', "gps": None,
                                "misto": "", "autori": [], "osoby": None}})
    r = parse(xmp.sidecar(doc, EVENT, "a.jpg"))
    assert r == {"popis": 'A & <b> "c"', "datum": None, "gps": None,
                 "tagy": [f"akce/{EVENT}"]}


def test_deterministic():
    doc = doc_with(**{"a.jpg": {"skupina": "g9", "popis": "x",
                                "datum": "2026-01-10T14:00:00"}})
    assert xmp.sidecar(doc, EVENT, "a.jpg").encode() == \
        xmp.sidecar(json.loads(json.dumps(doc)), EVENT, "a.jpg").encode()


@pytest.mark.parametrize("value, expected", [
    ("2026-04-28T09:44:36", "2026-04-28T09:44:36+02:00"),
    ("2026-01-10T14:00:00", "2026-01-10T14:00:00+01:00"),
    ("2026-01-10T14:00", "2026-01-10T14:00:00+01:00"),
    # Podzimní posun: 2:30 je dvakrát, bere se letní čas.
    ("2026-10-25T02:30:00", "2026-10-25T02:30:00+02:00"),
    ("2026-10-25T03:30:00", "2026-10-25T03:30:00+01:00"),
    ("2026-04-28", "2026-04-28"),
])
def test_format_date(value, expected):
    assert xmp.format_date(value) == expected


@pytest.mark.parametrize("value, pos, neg, expected", [
    (49.4063, "N", "S", "49,24.378000N"),
    (-33.8688, "N", "S", "33,52.128000S"),
    (-0.1276, "E", "W", "0,07.656000W"),
    (16.0, "E", "W", "16,00.000000E"),
    (15.99999999999, "E", "W", "16,00.000000E"),
])
def test_format_coord(value, pos, neg, expected):
    assert xmp.format_coord(value, pos, neg) == expected


# --- export ---------------------------------------------------------------

def make_ws(tmp_path, zapis=False, n=3):
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    files = {f"f{i}.jpg": "x" for i in range(n)}
    make_tree(archiv, {f"{EVENT}/": dict(files, **{
        "jen_na_disku.jpg": "x", "vyradit.jpg": "x",
        "RAW.ignored/": {"r.jpg": "x"}})})
    ws = Workspace(archiv, tmp_path / "work", zapis)
    soubory = {name: {"popis": name} for name in files}
    soubory.update({"vyradit.jpg": {"vyradit": True}, "neni.jpg": {},
                    "r.jpg": {}})
    ws.save(EVENT, doc_with(**soubory), None)
    return ws


def edit(ws, fn):
    doc, version = ws.load(EVENT)
    fn(doc)
    return ws.save(EVENT, doc, version)


def test_export_dev_mode_only_work(tmp_path):
    ws = make_ws(tmp_path)
    before = snapshot(ws.archiv)
    assert xmp.export(ws, EVENT) == {"zapsano": 3, "nezmeneno": 0,
                                     "chyby": []}
    assert snapshot(ws.archiv) == before
    out = ws.work / "xmp" / EVENT
    assert sorted(p.name for p in out.iterdir()) == \
        ["f0.jpg.xmp", "f1.jpg.xmp", "f2.jpg.xmp"]


def test_export_only_changed(tmp_path):
    ws = make_ws(tmp_path, zapis=True, n=100)
    assert xmp.export(ws, EVENT)["zapsano"] == 100
    assert xmp.export(ws, EVENT) == {"zapsano": 0, "nezmeneno": 100,
                                     "chyby": []}
    edit(ws, lambda d: d["soubory"]["f7.jpg"].update(popis="nový"))
    assert xmp.export(ws, EVENT) == {"zapsano": 1, "nezmeneno": 99,
                                     "chyby": []}
    event_dir = ws.archiv / EVENT
    assert (event_dir / "f7.jpg.xmp").read_text().count("nový") == 1
    assert not (event_dir / "vyradit.jpg.xmp").exists()
    assert not any(p.name.startswith(".") for p in event_dir.iterdir())
    # Sidecary se mezi soubory akce nepočítají.
    assert ws.list_events()[0]["souboru"] == 102


def test_dry_run_and_manual_edit(tmp_path):
    ws = make_ws(tmp_path, zapis=True)
    assert xmp.export(ws, EVENT, nanecisto=True)["zapsano"] == 3
    assert not (ws.archiv / EVENT / "f0.jpg.xmp").exists()
    assert ws.export_version(EVENT) is None
    xmp.export(ws, EVENT)
    path = ws.archiv / EVENT / "f1.jpg.xmp"
    path.write_text(path.read_text().replace("f1.jpg", "ručně"))
    before = snapshot(ws.archiv)
    assert xmp.export(ws, EVENT, nanecisto=True) == \
        {"zapsano": 1, "nezmeneno": 2, "chyby": []}
    assert snapshot(ws.archiv) == before


def test_export_record(tmp_path):
    ws = make_ws(tmp_path)
    assert ws.export_version(EVENT) is None
    xmp.export(ws, EVENT)
    _, version = ws.load(EVENT)
    assert ws.export_version(EVENT) == version
    assert ws.export_record_path(EVENT).parent == ws.work / "export"
    # Záznam vývojového režimu neplatí pro produkční.
    assert Workspace(ws.archiv, ws.work, True).export_version(EVENT) is None
    edit(ws, lambda d: d["soubory"]["f0.jpg"].update(popis="jiný"))
    assert ws.export_version(EVENT) == version != ws.load(EVENT)[1]


def test_export_error_keeps_record(tmp_path, monkeypatch):
    ws = make_ws(tmp_path)
    xmp.export(ws, EVENT)
    recorded = ws.export_version(EVENT)
    edit(ws, lambda d: d["soubory"]["f0.jpg"].update(popis="jiný"))
    edit(ws, lambda d: d["soubory"]["f1.jpg"].update(popis="jiný"))
    real = xmp.write_atomic

    def failing(path, data):
        if path.name == "f0.jpg.xmp":
            raise OSError("disk plný")
        real(path, data)

    monkeypatch.setattr(xmp, "write_atomic", failing)
    r = xmp.export(ws, EVENT)
    assert r["zapsano"] == 1 and r["chyby"] == [
        {"soubor": "f0.jpg", "chyba": "disk plný"}]
    assert ws.export_version(EVENT) == recorded


def test_export_without_metadata(tmp_path):
    ws = make_ws(tmp_path)
    (ws.archiv / "2020-01-01 jiná").mkdir()
    assert xmp.export(ws, "2020-01-01 jiná") is None
