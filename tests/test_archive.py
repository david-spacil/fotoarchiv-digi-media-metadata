import json

import pytest

from fotoarchiv.__main__ import main
from fotoarchiv.archive import Collision, Conflict, Workspace, version_of
from .conftest import make_tree, snapshot

EVENT = "2026-04-28 kontrola Stezky"


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
    for name in ("2024-03-14 výzkum Hradisko", "2023-01-01 skrytá",
                 "2022-01-01 dvojí", "2022-01-01 dvojí.ignored"):
        (ws_prod.archiv / name).mkdir()
    ws_prod.save("2024-03-14 výzkum Hradisko",
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
        "2023-01-01 skrytá.ignored", "2024-03-14 výzkum Hradisko",
        "2025-01-02 starší.ignored", HIDDEN]
    # Metadata jdou se složkou.
    assert ws_prod.load("2025-01-02 starší")[0] == {"dokonceno": None}
