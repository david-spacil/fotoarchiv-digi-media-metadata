import json
import xml.etree.ElementTree as ET

import pytest

from fotoarchiv import xmp
from fotoarchiv.archive import Workspace
from .conftest import make_tree, snapshot

EVENT = "2026-04-28 kontrola Naučné stezky"
NS = {"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
      "dc": "http://purl.org/dc/elements/1.1/",
      "xmp": "http://ns.adobe.com/xap/1.0/",
      "exif": "http://ns.adobe.com/exif/1.0/",
      "digiKam": "http://www.digikam.org/ns/1.0/"}


def doc_with(**soubory):
    return {
        "schema": "fotoarchiv-digi-media-metadata/2",
        "dokonceno": None,
        "akce": {"nazev": "kontrola", "mista": ["Vzorkov"],
                 "ucastnici": ["Účastník, Jan"]},
        "souradnice_mist": {"Vzorkov": {"gps": [49.1234, 16.4321]}},
        "skupiny": {"g9": {"nazev": "G9",
                           "autori": ["Příkladný, Daniel", "Modelová, Zuzana"],
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
        "osoby": ["Novák, Petr"],
        "obliceje": [{"jmeno": "Vzorný, Tomáš",
                      "oblast": [0.5, 0.4, 0.08, 0.06]}]}})
    text = xmp.sidecar(doc, EVENT, "P1503712.JPG")
    r = parse(text)
    assert r["tagy"] == [f"akce/{EVENT}", "autor/Příkladný, Daniel",
                         "autor/Modelová, Zuzana"]
    assert r["gps"] == ("49,07.404000N", "16,25.926000E")
    assert r["datum"] == "2026-04-28T09:44:36+02:00"
    assert r["popis"] is None
    for leaked in ("Vzorkov", "Panasonic", "Účastník", "G9", "Novák",
                   "Vzorný", "mwg-rs"):
        assert leaked not in text


def test_event_authors_not_exported():
    """Autoři u akce (vypuštěný klíč schématu /2) se do sidecaru
    nedostanou; skupina bez autorů zůstane bez tagu autor/."""
    doc = doc_with(**{"a.jpg": {"skupina": "bez"}})
    doc["akce"]["autori"] = ["Vzorný, Tomáš"]
    doc["skupiny"]["bez"] = {"nazev": "Bez autorů"}
    r = parse(xmp.sidecar(doc, EVENT, "a.jpg"))
    assert r["tagy"] == [f"akce/{EVENT}"]


def test_tag_slash_and_duplicates():
    doc = doc_with(**{"a.jpg": {"autori": ["Novák, Petr", "Novák, Petr",
                                           "A/B"]}})
    assert parse(xmp.sidecar(doc, EVENT, "a.jpg"))["tagy"] == [
        f"akce/{EVENT}", "autor/Novák, Petr", "autor/A-B"]


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
    # Samotné datum: Immich ho bez času nepřijme, dosadí se poledne.
    ("2026-04-28", "2026-04-28T12:00:00+02:00"),
    ("2026-01-10", "2026-01-10T12:00:00+01:00"),
])
def test_format_date(value, expected):
    assert xmp.format_date(value) == expected


@pytest.mark.parametrize("value, pos, neg, expected", [
    (49.1234, "N", "S", "49,07.404000N"),
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


# --- obličeje pro obnovu -----------------------------------------------------

MWG = {"rdf": NS["rdf"],
       "mwg-rs": "http://www.metadataworkinggroup.com/schemas/regions/",
       "stDim": "http://ns.adobe.com/xap/1.0/sType/Dimensions#",
       "stArea": "http://ns.adobe.com/xmp/sType/Area#"}
FACE = {"jmeno": "Vzorný, Tomáš", "oblast": [0.5, 0.4, 0.08, 0.06]}


def parse_regions(text):
    desc = ET.fromstring(text).find("rdf:RDF/rdf:Description", NS)
    reg = desc.find("mwg-rs:Regions", MWG)
    if reg is None:
        return None
    dim = reg.find("mwg-rs:AppliedToDimensions", MWG)
    faces = []
    for li in reg.findall("mwg-rs:RegionList/rdf:Bag/rdf:li", MWG):
        area = li.find("mwg-rs:Area", MWG)
        faces.append({
            "jmeno": li.find("mwg-rs:Name", MWG).text,
            "typ": li.find("mwg-rs:Type", MWG).text,
            "jednotka": area.find("stArea:unit", MWG).text,
            "oblast": [float(area.find(f"stArea:{k}", MWG).text)
                       for k in "xywh"]})
    return {"w": int(dim.find("stDim:w", MWG).text),
            "h": int(dim.find("stDim:h", MWG).text), "obliceje": faces}


def test_regions_for_restore():
    doc = doc_with(**{"a.jpg": {"obliceje": [FACE]}})
    text = xmp.sidecar(doc, EVENT, "a.jpg", (2736, 3648, 1))
    assert parse_regions(text) == {"w": 2736, "h": 3648, "obliceje": [
        {"jmeno": "Vzorný, Tomáš", "typ": "Face", "jednotka": "normalized",
         "oblast": [0.5, 0.4, 0.08, 0.06]}]}
    # Zbytek sidecaru stejný jako běžný.
    assert parse(text) == parse(xmp.sidecar(doc, EVENT, "a.jpg"))


def test_no_regions_without_faces_or_geometry():
    doc = doc_with(**{"a.jpg": {"obliceje": [FACE]}, "b.jpg": {}})
    assert xmp.sidecar(doc, EVENT, "b.jpg", (10, 10, 1)) == \
        xmp.sidecar(doc, EVENT, "b.jpg")
    assert "mwg-rs" not in xmp.sidecar(doc, EVENT, "a.jpg")


def test_stored_area_measured_in_immich():
    # 20260909_132018.jpg (Orientation 6): ML obličej vůči otočené fotce
    # a oblast, kterou Immich z MWG umístil na totéž místo (6. 10. 2026).
    assert xmp.stored_area([0.5924, 0.457, 0.0431, 0.0453], 6) == \
        [0.457, 0.4076, 0.0453, 0.0431]


@pytest.mark.parametrize("orientation", range(1, 9))
def test_stored_area_matches_pillow(orientation):
    # Značka v uloženém obrázku; po exif_transpose se změří její oblast
    # v otočeném a převod ji musí vrátit na původní místo.
    from PIL import Image, ImageOps
    w, h, box = 200, 100, (20, 10, 60, 30)
    img = Image.new("L", (w, h))
    img.paste(255, box)
    img.getexif()[0x0112] = orientation
    shown = ImageOps.exif_transpose(img)
    x1, y1, x2, y2 = shown.getbbox()
    displayed = [(x1 + x2) / 2 / shown.width, (y1 + y2) / 2 / shown.height,
                 (x2 - x1) / shown.width, (y2 - y1) / shown.height]
    expected = [round(v, 4) for v in (
        (box[0] + box[2]) / 2 / w, (box[1] + box[3]) / 2 / h,
        (box[2] - box[0]) / w, (box[3] - box[1]) / h)]
    assert xmp.stored_area(displayed, orientation) == expected


def test_image_geometry(tmp_path):
    from PIL import Image
    img = Image.new("RGB", (40, 30))
    exif = img.getexif()
    exif[0x0112] = 6
    img.save(tmp_path / "a.jpg", exif=exif)
    assert xmp.image_geometry(tmp_path / "a.jpg") == (40, 30, 6)
    (tmp_path / "v.mp4").write_bytes(b"x")
    assert xmp.image_geometry(tmp_path / "v.mp4") is None


def test_export_with_faces_keeps_record(tmp_path):
    from PIL import Image
    ws = make_ws(tmp_path)
    Image.new("RGB", (40, 30)).save(ws.event_dir(EVENT) / "f0.jpg")
    edit(ws, lambda d: d["soubory"]["f0.jpg"].update(obliceje=[FACE]))
    xmp.export(ws, EVENT)
    version = ws.export_version(EVENT)
    plain = ws.sidecar_path(EVENT, "f0.jpg").read_text()
    assert "mwg-rs" not in plain
    result = xmp.export(ws, EVENT, obliceje=True)
    assert result == {"zapsano": 1, "nezmeneno": 2, "chyby": []}
    regions = parse_regions(ws.sidecar_path(EVENT, "f0.jpg").read_text())
    assert regions["w"] == 40 and regions["obliceje"][0]["jmeno"] == \
        "Vzorný, Tomáš"
    assert ws.export_version(EVENT) == version
    # Kontrola nanečisto hlásí sidecar s obličeji jako neaktuální.
    assert xmp.export(ws, EVENT, nanecisto=True)["zapsano"] == 1
    xmp.export(ws, EVENT)
    assert ws.sidecar_path(EVENT, "f0.jpg").read_text() == plain


def test_cli_export_faces(tmp_path, capsys):
    from PIL import Image
    from fotoarchiv.__main__ import main
    ws = make_ws(tmp_path)
    Image.new("RGB", (40, 30)).save(ws.event_dir(EVENT) / "f0.jpg")
    edit(ws, lambda d: d["soubory"]["f0.jpg"].update(obliceje=[FACE]))
    main(["exportovat", EVENT, "--archiv", str(ws.archiv), "--work",
          str(ws.work), "--obliceje"])
    assert "mwg-rs:Regions" in ws.sidecar_path(EVENT, "f0.jpg").read_text()
    assert ws.export_version(EVENT) is None


def test_editors_not_in_sidecar(tmp_path):
    ws = make_ws(tmp_path)
    edit(ws, lambda d: d.update(upravili={"Upravil, Jiný": "2026-10-14"}))
    xmp.export(ws, EVENT)
    for path in (ws.work / "xmp" / EVENT).iterdir():
        text = path.read_text(encoding="utf-8")
        assert "Upravil" not in text and "2026-10-14" not in text
