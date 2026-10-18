import re

from PIL import Image

from fotoarchiv import index
from fotoarchiv.archive import Workspace
from .conftest import make_tree, snapshot

ATRIUM = "2026-09-14 Atrium Summer School 2026"
KONF = "2026-09-08 Konference Dějiny archeologie"
VLNENA = "2026-06-19 židovská synagoga u Vlněny"


def konference():
    soubory = {f"p{i:03}.jpg": {"skupina": "a"} for i in range(108)}
    soubory["p000.jpg"] = {"skupina": "a", "misto": "Poprad",
                           "obliceje": [{"jmeno": "Fiktivní, Jan",
                                         "oblast": [0, 0, 1, 1]}]}
    soubory["p001.jpg"] = {"skupina": "a", "autori": ["Filipová, Zuzana"],
                           "obliceje": [{"jmeno": "Fiktivní, Jan",
                                         "oblast": [0, 0, 1, 1]}]}
    soubory["v.mp4"] = {"skupina": "a"}
    return {
        "akce": {"nazev": "Konference Dějiny archeologie",
                 "datum_od": "2026-09-08", "datum_do": "2026-09-10",
                 "mista": ["Markušovce", "Spišská Nová Ves"],
                 "ucastnici": ["Fiktivní, Jan"]},
        "skupiny": {"a": {"nazev": "A", "autori": ["Fiktivní, Jan"],
                          "pristroj": "Canon EOS"}},
        "soubory": soubory,
    }


def make_ws(tmp_path, zapis=False):
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    files = {f"p{i:03}.jpg": "x" for i in range(1, 108)}
    files.update({"v.mp4": "v", "pozn.txt": "x", "Thumbs.db": "x"})
    make_tree(archiv, {
        f"{ATRIUM}/": {"b.jpg": "x"},
        f"{KONF}/": files,
        f"{VLNENA}/": {"x.jpg": "x", "y.mov": "y"},
        "přetřídit/": {"z.jpg": "x"},
        "_metadata.xlsx": "ručně",
    })
    Image.new("RGB", (800, 600), "red").save(archiv / KONF / "p000.jpg")
    ws = Workspace(archiv, tmp_path / "work", zapis)
    ws.save(KONF, konference(), None)
    ws.save(ATRIUM, {"akce": {"nazev": "Atrium Summer School 2026",
                              "datum_od": "2026-09-14"},
                     "dokonceno": "2026-09-20", "soubory": {}}, None)
    return ws


def by_name(records):
    return {r["slozka"]: r for r in records}


def test_collect(tmp_path):
    ws = make_ws(tmp_path)
    records = index.collect(ws)
    assert [r["slozka"] for r in records] == [ATRIUM, KONF, VLNENA]
    r = by_name(records)
    assert r[ATRIUM]["stav"] == "hotovo"
    k = r[KONF]
    assert k["stav"] == "rozpracovano"
    assert (k["foto"], k["video"]) == (108, 1)
    assert k["mista_akce"] == ["Markušovce", "Spišská Nová Ves"]
    assert k["mista"] == ["Markušovce", "Spišská Nová Ves", "Poprad"]
    assert k["osoby"] == [("Fiktivní, Jan", 2)]
    assert k["ucastnici"] == ["Fiktivní, Jan"]
    assert k["pristroje"] == ["Canon EOS"]
    assert k["nahled"]  # p000.jpg je jediný platný JPEG a první
    v = r[VLNENA]
    assert v == dict(v, stav="nezpracovano", nazev="židovská synagoga u "
                     "Vlněny", datum_od="2026-06-19", foto=1, video=1,
                     mista=[], autori=[], osoby=[], pristroje=[])
    assert v["nahled"] is None  # x.jpg není obrázek


def test_authors_order():
    soubory = {f"f{i}.jpg": {"skupina": "g"} for i in range(100)}
    for i in range(5):
        soubory[f"k{i}.jpg"] = {"skupina": "g",
                                "autori": ["Modelová, Zuzana"]}
    soubory["obe.jpg"] = {"skupina": "g", "autori": ["Modelová, Zuzana",
                                                     "Příkladný, Daniel"]}
    doc = {"akce": {"nazev": "x", "autori": ["Nikdo, Nefotil"]},
           "skupiny": {"g": {"autori": ["Příkladný, Daniel"]}},
           "soubory": soubory}
    d = index.details(doc)
    assert d["autori"] == [("Příkladný, Daniel", 101), ("Modelová, Zuzana", 6)]
    assert index.authors_text(d) == "Příkladný D.; Modelová Z."


def test_authors_tie_by_name():
    doc = {"soubory": {"a.jpg": {"autori": ["Zeman, A"]},
                       "b.jpg": {"autori": ["Adam, B"]}}}
    assert index.details(doc)["autori"] == [("Adam, B", 1), ("Zeman, A", 1)]


def test_short_name():
    assert index.short_name("Příkladný, Daniel") == "Příkladný D."
    assert index.short_name("Erdoğan, Hüseyin") == "Erdoğan H."
    assert index.short_name("Fiktivní") == "Fiktivní"


def test_render_md(tmp_path):
    md = index.render_md(index.collect(make_ws(tmp_path)))
    assert md.startswith("# ")
    assert "Generováno automaticky" in md and "přepíšou" in md
    row = next(line for line in md.splitlines() if "Konference" in line)
    cells = [c.strip() for c in row.strip("│").split("│")]
    assert cells == ["2026-09-08", "Konference Dějiny archeologie",
                     "Markušovce; Spišská Nová Ves",
                     "Fiktivní J.; Filipová Z.", "108", "1"]
    assert "Poprad" not in md
    assert "╒" in md and "Místa" in md
    # Bez času generování: jen datum akcí, žádný čas.
    assert not re.search(r"\d{1,2}:\d{2}", md)
    assert md.index(ATRIUM[11:]) < md.index("Konference") < \
        md.index("Vlněny")


def test_render_html(tmp_path):
    ws = make_ws(tmp_path)
    text = index.render_html(index.collect(ws), index.link(ws))
    assert text.count('<article class="karta') == 3
    assert 'class="karta kompakt"' in text  # nezpracovaná akce
    assert "data:image/jpeg;base64," in text
    assert "bez náhledu" in text
    assert "rozpracováno" in text and "hotovo" in text
    assert "Spišská Nová Ves; Poprad" in text
    assert "Fiktivní J. <small>2×</small>" in text
    assert "8.–10. 9. 2026" in text
    assert "přetřídit" not in text
    # Upozornění jen v komentáři, žádné externí zdroje.
    assert "<!--\n  GENEROVÁNO AUTOMATICKY" in text
    assert "Generováno" not in re.sub(r"<!--.*?-->", "", text, flags=re.S)
    assert not re.search(r"(src|href)=\"(https?:)?//", text)
    assert "<link" not in text and "@import" not in text
    # Bez JS jsou karty vidět, skrytý je jen panel filtrů.
    assert '<div class="filtry" hidden>' in text
    assert text.count(" hidden") == 1
    href = (ws.archiv / KONF).as_uri() + "/"
    assert f'href="{href}"' in text


def test_date_text():
    assert index.date_text("2026-09-08", "2026-09-08") == "8. 9. 2026"
    assert index.date_text("2026-09-30", "2026-10-02") == \
        "30. 9. – 2. 10. 2026"
    assert index.date_text("2025-12-30", "2026-01-02") == \
        "30. 12. 2025 – 2. 1. 2026"


def test_write_dev(tmp_path):
    ws = make_ws(tmp_path)
    before = snapshot(ws.archiv)
    assert index.write(ws) == []
    out = tmp_path / "work" / "index"
    assert (out / "_INDEX.html").exists() and (out / "_INDEX.md").exists()
    assert {(out / n).stat().st_mode & 0o777 for n in index.NAMES} == {0o644}
    assert snapshot(ws.archiv) == before
    mtimes = snapshot(out)
    assert index.write(ws) == []
    assert snapshot(out) == mtimes


def test_write_prod(tmp_path):
    ws = make_ws(tmp_path, zapis=True)
    xlsx = (ws.archiv / "_metadata.xlsx").stat().st_mtime_ns
    assert index.write(ws) == []
    text = (ws.archiv / "_INDEX.html").read_text()
    assert 'href="./2026-09-08%20Konference%20D%C4%9Bjiny%20archeologie/"' \
        in text
    assert (ws.archiv / "_INDEX.md").exists()
    assert (ws.archiv / "_metadata.xlsx").stat().st_mtime_ns == xlsx
    assert (ws.archiv / "_metadata.xlsx").read_text() == "ručně"
    # Index v kořeni není akce.
    assert [r["slozka"] for r in index.collect(ws)] == [ATRIUM, KONF, VLNENA]


def test_write_failure_is_warning(tmp_path, monkeypatch):
    ws = make_ws(tmp_path)

    def failing(path, data, mode=None):
        if path.name == "_INDEX.html":
            raise OSError("zamčeno")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    monkeypatch.setattr("fotoarchiv.xmp.write_atomic", failing)
    warnings = index.write(ws)
    assert len(warnings) == 1 and "_INDEX.html" in warnings[0]
    assert (tmp_path / "work" / "index" / "_INDEX.md").exists()


def test_editors_not_in_index(tmp_path):
    ws = make_ws(tmp_path)
    doc, version = ws.load(KONF)
    doc["upravili"] = {"Upravil, Jiný": "2026-10-14T10:15:02"}
    ws.save(KONF, doc, version)
    records = index.collect(ws)
    md = index.render_md(records)
    html = index.render_html(records, index.link(ws))
    for text in (md, html, repr(records)):
        assert "Upravil" not in text and "10:15:02" not in text
