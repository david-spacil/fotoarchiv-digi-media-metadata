import json

import pytest

from fotoarchiv.__main__ import main
from fotoarchiv.archive import (SCHEMA, SCHEMA_V1, Collision, Conflict,
                                Workspace, version_of)
from .conftest import make_tree, snapshot

EVENT = "2026-04-28 kontrola Naučné stezky"


@pytest.fixture
def ws(tmp_path):
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    make_tree(archiv, {
        f"{EVENT}/": {"a.jpg": "x", "b.mp4": "y", "Thumbs.db": "",
                      "RAW/": {"a.rw2": ""}},
        "2025-01-02 starší/": {},
        "přetřídit/": {"c.jpg": ""},
        "_metadata.xlsx": "",
    })
    return Workspace(archiv, tmp_path / "work")


def test_list_events_pattern_and_order(ws):
    events = ws.list_events()
    assert [e["nazev"] for e in events] == [EVENT, "2025-01-02 starší"]


def test_list_events_count_and_state(ws):
    event = ws.list_events()[0]
    assert event["souboru"] == 2
    assert event["stav"] == "nezpracovano"
    ws.save(EVENT, {"schema": "x", "dokonceno": None}, None)
    assert ws.list_events()[0]["stav"] == "rozpracovano"
    _, version = ws.load(EVENT)
    ws.save(EVENT, {"schema": "x", "dokonceno": "2026-05-01T10:00"}, version)
    assert ws.list_events()[0]["stav"] == "hotovo"


def test_event_dir_rejects_other_names(ws):
    for name in ["přetřídit", "../x", f"{EVENT}/RAW", "2026-01-01 neni"]:
        with pytest.raises(KeyError):
            ws.event_dir(name)


def test_save_new_file(ws):
    assert ws.load(EVENT) == (None, None)
    version = ws.save(EVENT, {"schema": "s"}, None)
    path = ws.metadata_path(EVENT)
    assert path == ws.work / "metadata" / EVENT / "_metadata.json"
    assert json.loads(path.read_text()) == {"schema": "s"}
    assert version == version_of(path.read_bytes())


def test_save_success_and_conflict(ws):
    v1 = ws.save(EVENT, {"n": 1}, None)
    v2 = ws.save(EVENT, {"n": 2}, v1)
    assert ws.load(EVENT) == ({"n": 2}, v2)
    # Jiný proces soubor změní.
    ws.metadata_path(EVENT).write_text('{"n": 3}')
    with pytest.raises(Conflict) as e:
        ws.save(EVENT, {"n": 4}, v2)
    assert json.loads(ws.metadata_path(EVENT).read_text()) == {"n": 3}
    assert e.value.current_version == ws.load(EVENT)[1]


def test_load_upgrades_v1_without_writing(ws):
    """Dokument /1 se načte převedený na /2, soubor na disku zůstane;
    uložení s vrácenou verzí projde a zapíše /2."""
    path = ws.metadata_path(EVENT)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "schema": SCHEMA_V1, "akce": {"nazev": "x", "autori": ["A, B"]},
        "skupiny": {}, "soubory": {"a.jpg": {"osoby": ["C, D"]}}}))
    before = path.read_bytes()
    doc, version = ws.load(EVENT)
    assert doc == {"schema": SCHEMA, "akce": {"nazev": "x"}, "skupiny": {},
                   "soubory": {"a.jpg": {}}}
    assert path.read_bytes() == before
    assert version == version_of(before)
    ws.save(EVENT, doc, version)
    assert json.loads(path.read_text())["schema"] == SCHEMA


def test_save_new_when_file_exists_conflicts(ws):
    ws.save(EVENT, {"n": 1}, None)
    with pytest.raises(Conflict):
        ws.save(EVENT, {"n": 2}, None)


def test_save_leaves_archive_and_no_temp(ws):
    before = snapshot(ws.archiv)
    v = ws.save(EVENT, {"n": 1}, None)
    ws.save(EVENT, {"n": 2}, v)
    assert snapshot(ws.archiv) == before
    assert [p.name for p in ws.metadata_path(EVENT).parent.iterdir()] == \
        ["_metadata.json"]


@pytest.fixture
def ws_prod(ws):
    return Workspace(ws.archiv, ws.work, zapis=True)


def test_production_saves_in_event_dir(ws_prod):
    v = ws_prod.save(EVENT, {"n": 1}, None)
    path = ws_prod.archiv / EVENT / "_metadata.json"
    assert ws_prod.metadata_path(EVENT) == path
    assert json.loads(path.read_text()) == {"n": 1}
    ws_prod.save(EVENT, {"n": 2}, v)
    assert sorted(p.name for p in path.parent.iterdir()) == \
        ["RAW", "Thumbs.db", "_metadata.json", "a.jpg", "b.mp4"]
    assert not ws_prod.work.exists()


def test_production_ignores_work_copy(ws, ws_prod):
    ws.save(EVENT, {"n": "work"}, None)
    assert ws_prod.load(EVENT) == (None, None)
    event = ws_prod.list_events()[0]
    assert event["stav"] == "nezpracovano"
    ws_prod.save(EVENT, {"n": "archiv"}, None)
    # Metadata se nepočítají mezi soubory akce.
    assert ws_prod.list_events()[0]["souboru"] == 2
    assert ws_prod.metadata_files() == [ws_prod.archiv / EVENT /
                                        "_metadata.json"]
    assert len(ws.metadata_files()) == 2


def test_adopt_skips_existing(ws):
    from fotoarchiv.archive import adopt
    ws.save(EVENT, {"n": "work"}, None)
    ws.save("2025-01-02 starší", {"n": "work2"}, None)
    ws.metadata_path("2025-01-02 starší").parent.with_name(
        "2020-01-01 smazaná").mkdir()
    (ws.metadata_path("2025-01-02 starší").parent.with_name(
        "2020-01-01 smazaná") / "_metadata.json").write_text("{}")
    archived = ws.archiv / EVENT / "_metadata.json"
    archived.write_text('{"n": "archiv"}')
    before = snapshot(ws.archiv)
    adopted, skipped = adopt(ws.archiv, ws.work)
    assert [n for n, _ in adopted] == ["2025-01-02 starší"]
    assert sorted(n for n, _ in skipped) == ["2020-01-01 smazaná", EVENT]
    assert archived.read_text() == '{"n": "archiv"}'
    assert snapshot(ws.archiv)[f"{EVENT}/_metadata.json"] == \
        before[f"{EVENT}/_metadata.json"]
    assert json.loads((ws.archiv / "2025-01-02 starší" /
                       "_metadata.json").read_text()) == {"n": "work2"}


def test_list_events_skips_sidecars_and_flags_changes(ws):
    from fotoarchiv import xmp
    event_dir = ws.archiv / EVENT
    (event_dir / "a.jpg.xmp").write_text("")
    (event_dir / ".xmp-abc.tmp").write_text("")
    assert ws.list_events()[0]["souboru"] == 2
    v = ws.save(EVENT, {"schema": "x", "dokonceno": "2026-05-01",
                        "soubory": {"a.jpg": {}}}, None)
    # Bez záznamu o exportu je stav neznámý, žádná poznámka.
    assert ws.list_events()[0]["zmeneno_po_exportu"] is False
    xmp.export(ws, EVENT)
    assert ws.list_events()[0]["zmeneno_po_exportu"] is False
    ws.save(EVENT, {"schema": "x", "dokonceno": "2026-05-01",
                    "soubory": {"a.jpg": {"popis": "x"}}}, v)
    event = ws.list_events()[0]
    assert event["stav"] == "hotovo" and event["zmeneno_po_exportu"]


def test_list_events_consistency(ws):
    event_dir = ws.archiv / EVENT
    # Fixture: RAW/ v kořeni je podsložka bez `.ignored`.
    assert ws.list_events()[0]["kontrola"] == {"podslozka": 1}
    (event_dir / "RAW").rename(event_dir / "RAW.ignored")
    assert ws.list_events()[0]["kontrola"] == {}
    (event_dir / "prezentace.zip").write_text("")
    (event_dir / "zprava.pdf").write_text("")
    (event_dir / "a.jpg.xmp").write_text("")
    (event_dir / "c.jpg.xmp").write_text("")
    ws.save(EVENT, {"schema": "x", "soubory": {"a.jpg": {}, "d.jpg": {}}},
            None)
    event = ws.list_events()[0]
    assert event["kontrola"] == {"nepodporovany": 2, "sirotek_xmp": 1,
                                 "chybejici": 1}
    assert event["souboru"] == 4  # a.jpg, b.mp4, zip, pdf
    assert ws.list_events()[1]["kontrola"] == {}


def test_list_events_flags_incomplete_finished(ws):
    doc = {"schema": "x", "dokonceno": None,
           "akce": {"datum": "2026-04-28", "mista": ["Brno"]},
           "skupiny": {"g": {"autori": ["Novák, Jan"]}},
           "soubory": {"a.jpg": {"skupina": "g"}, "b.mp4": {},
                       "chybi.jpg": {}}}
    v = ws.save(EVENT, doc, None)
    # Rozpracovaná akce se nehodnotí.
    assert ws.list_events()[0]["chybi"] == []
    doc["dokonceno"] = "2026-05-01"
    v = ws.save(EVENT, doc, v)
    # b.mp4 nemá autory; chybi.jpg v kořeni není, nepočítá se.
    assert ws.list_events()[0]["chybi"] == ["autori"]
    doc["soubory"]["b.mp4"] = {"vyradit": True}
    doc["akce"]["mista"] = ["Brno", "Praha"]
    v = ws.save(EVENT, doc, v)
    # Dvě místa se nedědí.
    assert ws.list_events()[0]["chybi"] == ["misto"]
    doc["soubory"]["a.jpg"]["misto"] = "Brno"
    ws.save(EVENT, doc, v)
    assert ws.list_events()[0]["chybi"] == []


# --- skrytí nedokončených akcí před Immichem (issue #13) -------------------

HIDDEN = f"{EVENT}.ignored"


def hide_event(ws):
    (ws.archiv / EVENT).rename(ws.archiv / HIDDEN)


def test_hidden_event_listed_without_suffix(ws):
    hide_event(ws)
    events = ws.list_events()
    assert [e["nazev"] for e in events] == [EVENT, "2025-01-02 starší"]
    assert events[0]["souboru"] == 2
    assert ws.event_dir(EVENT) == ws.archiv / HIDDEN
    assert ws.is_hidden(EVENT) and not ws.is_hidden("2025-01-02 starší")


def test_hidden_name_with_suffix_refused(ws):
    hide_event(ws)
    with pytest.raises(KeyError):
        ws.event_dir(HIDDEN)
    (ws.archiv / f"{HIDDEN}.ignored").mkdir()  # dvojitá přípona
    assert HIDDEN not in ws.event_names()


def test_hidden_metadata_in_event_dir(ws_prod):
    hide_event(ws_prod)
    ws_prod.save(EVENT, {"n": 1}, None)
    assert (ws_prod.archiv / HIDDEN / "_metadata.json").is_file()
    assert ws_prod.sidecar_path(EVENT, "a.jpg") == \
        ws_prod.archiv / HIDDEN / "a.jpg.xmp"
    assert ws_prod.list_events()[0]["stav"] == "rozpracovano"


def test_collision(ws_prod):
    (ws_prod.archiv / HIDDEN).mkdir()
    before = snapshot(ws_prod.archiv)
    with pytest.raises(Collision):
        ws_prod.event_dir(EVENT)
    event = ws_prod.list_events()[0]
    assert event["nazev"] == EVENT and event["stav"] == "kolize"
    assert ws_prod.event_names().count(EVENT) == 1
    with pytest.raises(Collision):
        ws_prod.publish(EVENT)
    assert snapshot(ws_prod.archiv) == before


def test_publish(ws_prod):
    hide_event(ws_prod)
    ws_prod.save(EVENT, {"n": 1}, None)
    assert ws_prod.publish(EVENT) == ws_prod.archiv / EVENT
    assert not (ws_prod.archiv / HIDDEN).exists()
    assert ws_prod.load(EVENT)[0] == {"n": 1}
    # Bez přípony nic nedělá.
    assert ws_prod.publish(EVENT) == ws_prod.archiv / EVENT


def test_publish_dev_mode_keeps_archive(ws):
    hide_event(ws)
    before = snapshot(ws.archiv)
    assert ws.publish(EVENT) == ws.archiv / HIDDEN
    assert snapshot(ws.archiv) == before


def cli_hide(ws, *flags):
    main(["skryt", "--archiv", str(ws.archiv), "--work", str(ws.work),
          *flags])


def test_cli_hide_dry_run(ws_prod, capsys):
    before = snapshot(ws_prod.archiv)
    cli_hide(ws_prod)
    out = capsys.readouterr().out
    assert f"skryje: {EVENT}" in out and "skryje: 2025-01-02 starší" in out
    assert "Ke skrytí: 2" in out
    assert snapshot(ws_prod.archiv) == before


def test_cli_hide(ws_prod, capsys):
    # nezpracovaná EVENT, rozpracovaná, dokončená, už skrytá, kolize
    ws_prod.save("2025-01-02 starší", {"dokonceno": None}, None)
    for name in ("2024-03-14 výzkum Ukázkovo", "2023-01-01 skrytá",
                 "2022-01-01 dvojí", "2022-01-01 dvojí.ignored"):
        (ws_prod.archiv / name).mkdir()
    ws_prod.save("2024-03-14 výzkum Ukázkovo",
                 {"dokonceno": "2024-04-01"}, None)
    (ws_prod.archiv / "2023-01-01 skrytá").rename(
        ws_prod.archiv / "2023-01-01 skrytá.ignored")
    cli_hide(ws_prod, "--zapis-do-archivu")
    out = capsys.readouterr().out
    assert "přeskočeno: 2022-01-01 dvojí" in out
    assert "Skryto: 2, kolizí: 1" in out
    assert sorted(p.name for p in ws_prod.archiv.iterdir()
                  if p.name[0].isdigit()) == [
        "2022-01-01 dvojí", "2022-01-01 dvojí.ignored",
        "2023-01-01 skrytá.ignored", "2024-03-14 výzkum Ukázkovo",
        "2025-01-02 starší.ignored", HIDDEN]
    # Metadata jdou se složkou.
    assert ws_prod.load("2025-01-02 starší")[0] == {"dokonceno": None}


# --- data karty v seznamu akcí (fronta-akci) --------------------------------

def test_list_events_card_data_unprocessed(ws):
    event = ws.list_events()[0]
    assert event["hotovost"] is None
    assert event["ukazky"] == ["a.jpg", "b.mp4"]
    assert event["upravili"] == {}


def test_list_events_card_data(ws):
    doc = {"schema": "x", "dokonceno": None,
           "akce": {"mista": ["Brno"]},
           "soubory": {"a.jpg": {"datum": "2026-04-28T10:00:00"},
                       "b.mp4": {"vyradit": True}},
           "upravili": {"Příkladný, Daniel": "2026-10-14T10:15:02"}}
    ws.save(EVENT, doc, None)
    event = ws.list_events()[0]
    assert event["hotovost"] == {"autori": [0, 1], "datum": [1, 1],
                                 "misto": [1, 1]}
    assert event["ukazky"] == ["a.jpg"]
    assert event["upravili"] == {"Příkladný, Daniel": "2026-10-14T10:15:02"}
    # `chybi` dál jen u hotovo.
    assert event["chybi"] == []


def test_samples_spread_over_large_event():
    from fotoarchiv.archive import samples
    present = {f"{i:03}.jpg" for i in range(200)}
    assert samples(present, None) == ["025.jpg", "075.jpg", "125.jpg",
                                      "175.jpg"]
    assert samples({"b.jpg", "a.jpg"}, None) == ["a.jpg", "b.jpg"]
    assert samples(set(), None) == []


# --- migrovat (schéma /1 → /2) ---------------------------------------------

def write_v1(ws, name, doc):
    path = ws.metadata_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(dict(doc, schema=SCHEMA_V1)).encode("utf-8")
    path.write_bytes(data)
    return version_of(data)


def mark_exported(ws, name, version):
    path = ws.export_record_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": version, "zapis": ws.zapis}))


def cli_migrate(ws, *flags):
    main(["migrovat", "--archiv", str(ws.archiv), "--work", str(ws.work),
          *flags])


OSOBY = {"akce": {"nazev": "x"}, "skupiny": {"g": {"nazev": "G"}},
         "soubory": {n: {"skupina": "g", "osoby": ["Vzorný, Tomáš"]}
                     for n in ("a.jpg", "b.jpg", "c.jpg")}}
AUTORI = {"akce": {"nazev": "y", "autori": ["Příkladný, Daniel"]},
          "skupiny": {"g": {"nazev": "G"},
                      "m": {"nazev": "M", "autori": ["Modelová, Zuzana"]}},
          "soubory": {"a.jpg": {"skupina": "g"},
                      "b.jpg": {"skupina": "g",
                                "autori": ["Modelová, Zuzana"]},
                      "c.jpg": {"skupina": "m"}}}
OLDER = "2025-01-02 starší"


def test_cli_migrate_dry_run(ws_prod, capsys):
    write_v1(ws_prod, EVENT, OSOBY)
    before = snapshot(ws_prod.archiv)
    cli_migrate(ws_prod)
    out = capsys.readouterr().out
    assert f"převede: {EVENT} (soubor.osoby 3)" in out
    assert "K převodu: 1" in out and "Archiv beze změny" in out
    assert snapshot(ws_prod.archiv) == before


def test_cli_migrate(ws_prod, capsys):
    v1 = write_v1(ws_prod, EVENT, dict(OSOBY, dokonceno="2026-05-01"))
    mark_exported(ws_prod, EVENT, v1)
    va = write_v1(ws_prod, OLDER, dict(AUTORI, dokonceno="2026-05-01"))
    mark_exported(ws_prod, OLDER, va)
    cli_migrate(ws_prod, "--zapis-do-archivu")
    out = capsys.readouterr().out
    assert f"převedeno: {EVENT} (soubor.osoby 3)" in out
    assert (f"převedeno: {OLDER} (akce.autori 1); souborů, které ztratí "
            "autory celé akce: 1") in out
    assert "Převedeno: 2" in out
    doc = json.loads(ws_prod.metadata_path(EVENT).read_text())
    assert doc["schema"] == SCHEMA
    assert all("osoby" not in r for r in doc["soubory"].values())
    # Sidecary se převodem nemění: záznam o exportu jde na novou verzi.
    assert ws_prod.export_version(EVENT) == ws_prod.load(EVENT)[1]
    # Akce s autory celé akce: sidecary se změní, záznam zůstane starý.
    doc = json.loads(ws_prod.metadata_path(OLDER).read_text())
    assert doc["akce"] == {"nazev": "y"}
    assert ws_prod.export_version(OLDER) == va != ws_prod.load(OLDER)[1]
    # Opakované spuštění nic nezmění.
    before = snapshot(ws_prod.archiv)
    cli_migrate(ws_prod, "--zapis-do-archivu")
    assert "Převedeno: 0" in capsys.readouterr().out
    assert snapshot(ws_prod.archiv) == before


def test_cli_migrate_failure_continues(ws_prod, capsys, monkeypatch):
    write_v1(ws_prod, EVENT, OSOBY)
    write_v1(ws_prod, OLDER, OSOBY)
    save = Workspace.save

    def fail_one(self, name, doc, version):
        if name == EVENT:
            raise Conflict("jiná")
        return save(self, name, doc, version)
    monkeypatch.setattr(Workspace, "save", fail_one)
    with pytest.raises(SystemExit) as e:
        cli_migrate(ws_prod, "--zapis-do-archivu")
    assert e.value.code == 1
    out = capsys.readouterr().out
    assert f"selhalo: {EVENT}: soubor se mezitím změnil" in out
    assert f"převedeno: {OLDER}" in out
