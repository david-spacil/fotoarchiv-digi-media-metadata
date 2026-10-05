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
