import json

import pytest

from fotoarchiv.archive import Conflict, Workspace, version_of
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
