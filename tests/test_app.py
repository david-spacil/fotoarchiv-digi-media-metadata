import json

import pytest

from fotoarchiv.__main__ import main
from fotoarchiv.app import create_app
from .conftest import make_tree, snapshot

EVENT = "2026-04-28 kontrola"


@pytest.fixture
def client(tmp_path, monkeypatch):
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    make_tree(archiv, {f"{EVENT}/": {"IMG-20260428-WA0001.jpg": "x",
                                     "RAW/": {"a.rw2": ""}}})
    monkeypatch.setattr("fotoarchiv.scan.run_exiftool",
                        lambda d, n: {})
    app = create_app(archiv, tmp_path / "work")
    app.testing = True
    return app.test_client(), archiv


def test_index_html(client):
    c, _ = client
    r = c.get("/")
    assert r.status_code == 200 and b"<html" in r.data.lower()


def test_flow_new_save_conflict(client):
    c, archiv = client
    before = snapshot(archiv)
    assert c.get("/api/akce").json[0]["stav"] == "nezpracovano"
    d = c.get(f"/api/akce/{EVENT}").json
    assert d["novy"] and d["version"] is None
    doc = d["metadata"]
    assert doc["soubory"]["IMG-20260428-WA0001.jpg"]["datum"] == "2026-04-28"
    r = c.put(f"/api/akce/{EVENT}/metadata",
              json={"metadata": doc, "version": None})
    assert r.status_code == 200
    assert c.get("/api/akce").json[0]["stav"] == "rozpracovano"
    r = c.put(f"/api/akce/{EVENT}/metadata",
              json={"metadata": doc, "version": None})
    assert r.status_code == 409
    assert snapshot(archiv) == before


def test_cleanup_endpoint(client):
    c, _ = client
    plan = c.post(f"/api/akce/{EVENT}/uklid", json={}).json
    assert plan["operace"][0]["do"] == "RAW.ignored"


def test_unknown_event_404(client):
    c, _ = client
    assert c.get("/api/akce/neni").status_code == 404


def test_missing_archive_exits(tmp_path):
    with pytest.raises(SystemExit) as e:
        main(["--archiv", str(tmp_path / "neni")])
    assert "Archiv nenalezen" in str(e.value)
