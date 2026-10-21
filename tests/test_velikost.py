import json
import os

import pytest

from fotoarchiv import trash, velikost
from fotoarchiv.archive import Workspace
from .conftest import make_tree, snapshot
from .test_app import (EVENT, R1, logged_in, login_app,  # noqa: F401
                       make_client, ndjson, prod, smazat, unsorted_tree)

AKCE = "2024-05-01 exkurze"
JINA = "2024-06-01 výzkum"


def walk_size(*paths):
    return sum(os.path.getsize(os.path.join(d, n))
               for p in paths for d, _, names in os.walk(p) for n in names)


@pytest.fixture
def ws(tmp_path):
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    make_tree(archiv, {f"{AKCE}/": {"a.jpg": "a" * 1000, "b.jpg": "b" * 1000,
                                    "_metadata.json": "m" * 10,
                                    "Thumbs.db": "t" * 5,
                                    "RAW.ignored/": {"a.rw2": "r" * 20000,
                                                     "b.rw2": "r" * 20000}},
                       f"{JINA}/": {"c.jpg": "c" * 300}})
    return Workspace(archiv, tmp_path / "work", zapis=True)


def done(v):
    while v.krok():
        pass


# --- výpočet -----------------------------------------------------------------

def test_bajtu_subfolders_and_skipped(ws):
    before = snapshot(ws.archiv)
    assert velikost.bajtu([ws.archiv / AKCE]) == 2000 + 10 + 5 + 40000
    assert snapshot(ws.archiv) == before


def test_bajtu_ignores_symlinks(ws, tmp_path):
    outside = tmp_path / "mimo"
    make_tree(outside.parent, {"mimo/": {"velky.jpg": "x" * 99999}})
    os.symlink(outside, ws.archiv / AKCE / "odkaz")
    os.symlink(outside / "velky.jpg", ws.archiv / AKCE / "odkaz.jpg")
    assert velikost.bajtu([ws.archiv / AKCE]) == 42015


def test_collision_sums_both_folders(ws):
    make_tree(ws.archiv, {f"{AKCE}.ignored/": {"x.jpg": "x" * 7}})
    v = velikost.Velikosti(ws)
    v.zmena(AKCE)
    done(v)
    assert v.akce()[AKCE]["bajtu"] == 42015 + 7


# --- cache -------------------------------------------------------------------

def test_cache_written_and_reloaded(ws):
    v = velikost.Velikosti(ws)
    assert v.akce() == {} and v.kos() == {}
    v.zmena(AKCE)
    assert v.krok() and not v.krok()
    data = json.loads((ws.work / velikost.NAME).read_text())
    assert data["akce"][AKCE]["bajtu"] == 42015 and data["kos"] == {}
    assert velikost.Velikosti(ws).akce()[AKCE]["bajtu"] == 42015


@pytest.mark.parametrize("obsah", ["{nesmysl", "[]", '{"akce": 1}',
                                   '{"akce": {"x": {"bajtu": "1"}}}'])
def test_broken_cache_is_empty(ws, obsah):
    ws.work.mkdir()
    (ws.work / velikost.NAME).write_text(obsah)
    v = velikost.Velikosti(ws)
    assert v.akce() == {} and v.kos() == {}


# --- fronta a denní přepočet -------------------------------------------------

def test_queue_without_duplicates(ws):
    v = velikost.Velikosti(ws)
    v.zmena(AKCE)
    v.zmena(AKCE)
    v.zmena_kos("x")
    assert v.fronta() == [("akce", AKCE), ("kos", "x")]
    done(v)
    assert v.fronta() == [] and v.kos() == {}   # neexistující položka koše


def test_fill_missing_at_start(ws):
    make_tree(ws.archiv, {f"{trash.TRASH}/": {"k1/": {"a.jpg": "a" * 3}}})
    v = velikost.Velikosti(ws)
    v.zmena(JINA)
    done(v)
    v.doplnit()
    assert v.fronta() == [("akce", AKCE), ("kos", "k1")]
    done(v)
    assert v.akce()[AKCE]["bajtu"] == 42015
    assert v.kos() == {"k1": {"bajtu": 3, "cas": v.kos()["k1"]["cas"]}}


def test_daily_recount_and_prune(ws):
    v = velikost.Velikosti(ws)
    v.doplnit()
    done(v)
    # Změny mimo aplikaci: přibude soubor, akce zmizí.
    (ws.archiv / AKCE / "RAW.ignored" / "c.rw2").write_text("r" * 5)
    os.rename(ws.archiv / JINA, ws.archiv / "jinam")
    assert v.akce()[AKCE]["bajtu"] == 42015       # údaj „k datu“
    v.denni()
    assert JINA not in v.akce()
    done(v)
    assert v.akce()[AKCE]["bajtu"] == 42020
    assert set(json.loads((ws.work / velikost.NAME).read_text())["akce"]) \
        == {AKCE}


# --- přesuny údaje -----------------------------------------------------------

def test_moves_between_events_and_trash(ws):
    v = velikost.Velikosti(ws)
    v.doplnit()
    done(v)
    v.presun_do_kose(AKCE, "k1")
    assert AKCE not in v.akce() and v.kos()["k1"]["bajtu"] == 42015
    assert v.fronta() == []                       # bez průchodu
    v.vratit_z_kose("k1", AKCE)
    assert v.kos() == {} and v.akce()[AKCE]["bajtu"] == 42015
    assert v.fronta() == [("akce", AKCE)]
    v.presun_do_kose(JINA, "k2")
    v.odebrat_z_kose(["k2", "neni"])
    assert v.kos() == {}


def test_move_without_value_queues_trash(ws):
    v = velikost.Velikosti(ws)
    v.presun_do_kose(AKCE, "k1")
    assert v.fronta() == [("kos", "k1")]


def test_result_of_vanished_event_dropped(ws, monkeypatch):
    v = velikost.Velikosti(ws)
    v.zmena(AKCE)
    real = velikost.bajtu

    def a_mezitim_smazano(paths):
        result = real(paths)
        os.rename(ws.archiv / AKCE, ws.archiv / "_kos.ignored")
        v.presun_do_kose(AKCE, "k1")
        return result
    monkeypatch.setattr(velikost, "bajtu", a_mezitim_smazano)
    v.krok()
    assert v.akce() == {}


# --- server ------------------------------------------------------------------

def velikosti(c):
    return c.application.config["VELIKOSTI"]


def test_list_reads_cache_only(tmp_path, monkeypatch):
    c, archiv = make_client(tmp_path, monkeypatch, zapis=False)
    before = snapshot(archiv)
    v = velikosti(c)
    calls = []
    monkeypatch.setattr(velikost, "bajtu",
                        lambda p: calls.append(p) or 0)
    [event] = c.get("/api/akce").json
    assert event["bajtu"] is None and calls == []
    assert v.fronta() == [("akce", EVENT)]
    monkeypatch.undo()
    done(v)
    size = walk_size(archiv / EVENT)
    assert c.get("/api/akce").json[0]["bajtu"] == size
    assert v.fronta() == []
    assert snapshot(archiv) == before             # jen čte


@pytest.mark.parametrize("login", ["prikladny", "novak", "modelova"])
def test_totals_for_everyone(login_app, login):
    app, archiv = login_app
    v = app.config["VELIKOSTI"]
    c = logged_in(app, login)
    assert c.get("/api/velikost").json == {"akce": 0, "kos": 0}
    make_tree(archiv, {f"{trash.TRASH}/": {"k1/": {"a.jpg": "a" * 5}}})
    v.doplnit()
    done(v)
    # Záznam akce, která zmizela mimo aplikaci, se do součtu nepočítá.
    v._data["akce"]["2020-01-01 zmizela"] = {"bajtu": 10 ** 9, "cas": ""}
    assert c.get("/api/velikost").json == {"akce": 1, "kos": 5}


def test_recount_after_cleanup_and_finish(prod):
    c, archiv = prod
    v = velikosti(c)
    v.zmena(EVENT)
    done(v)
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    r = c.post(f"/api/akce/{EVENT}/uklid/provest", json={
        "volby": {"RAW": "ponechat"}, "raw_v_koreni": True, "relace": "r1"})
    assert r.status_code == 200
    assert v.fronta() == [("akce", EVENT)]
    done(v)
    d = c.get(f"/api/akce/{EVENT}").json
    r = c.put(f"/api/akce/{EVENT}/metadata", json=dict(
        R1, metadata=d["metadata"], version=None))
    r = c.post(f"/api/akce/{EVENT}/dokoncit",
               json=dict(R1, version=r.json["version"]))
    assert r.status_code == 200, r.json
    assert v.fronta() == [("akce", EVENT)]
    done(v)
    assert v.akce()[EVENT]["bajtu"] == walk_size(archiv / EVENT)


def test_recount_after_import_from_unsorted(prod):
    c, archiv = prod
    v = velikosti(c)
    unsorted_tree(archiv)
    name = "2019-05-01 DOD Karel"
    id = c.post("/api/import", json=dict(R1, zdroj="DOD 2019")).json["id"]
    ndjson(c.post(f"/api/import/{id}/plan",
                  json={"jmeno": R1["jmeno"], "nova": name}))
    r = c.post(f"/api/import/{id}/provest", json=dict(R1, nova=name))
    assert ndjson(r)[-1]["typ"] == "vysledek"
    r.close()
    assert ("akce", name) in v.fronta()
    done(v)
    assert v.akce()[name]["bajtu"] == walk_size(archiv / f"{name}.ignored")
    # Akce bez údaje se do součtu nezapočte.
    assert c.get("/api/velikost").json["akce"] == \
        walk_size(archiv / f"{name}.ignored")


def test_trash_moves_size(login_app):
    app, archiv = login_app
    v = app.config["VELIKOSTI"]
    c = logged_in(app, "prikladny")
    v.zmena(EVENT)
    done(v)
    size = v.akce()[EVENT]["bajtu"]
    assert c.get("/api/velikost").json == {"akce": size, "kos": 0}
    id = smazat(c).json["id"]
    assert v.fronta() == []
    assert c.get("/api/velikost").json == {"akce": 0, "kos": size}
    assert c.get("/api/kos").json["akce"][0]["bajtu"] == size
    assert c.post(f"/api/kos/{id}/obnovit").status_code == 200
    assert c.get("/api/velikost").json == {"akce": size, "kos": 0}
    assert v.fronta() == [("akce", EVENT)]
    done(v)
    assert v.akce()[EVENT]["bajtu"] == size
    # Vysypání po lhůtě položku odebere.
    id = smazat(c).json["id"]
    record = archiv / trash.TRASH / id / trash.RECORD
    data = json.loads(record.read_text())
    data["smazano"] = "2026-01-01T10:00:00"
    record.write_text(json.dumps(data))
    assert c.get("/api/velikost").json["kos"] == size
    assert app.config["KOS_VYSYPAT"]() == [EVENT]
    assert c.get("/api/velikost").json == {"akce": 0, "kos": 0}


def test_dev_mode_delete_keeps_size(tmp_path, monkeypatch):
    c, archiv = make_client(tmp_path, monkeypatch, zapis=False)
    v = velikosti(c)
    v.zmena(EVENT)
    done(v)
    before = snapshot(archiv)
    assert smazat(c).json["plan"] is True
    assert EVENT in v.akce() and v.kos() == {}
    assert snapshot(archiv) == before


def test_metadata_untouched(ws):
    """Přepočet nic nezapíše do archivu ani do `_metadata.json`."""
    before = snapshot(ws.archiv)
    v = velikost.Velikosti(ws)
    v.denni()
    done(v)
    assert snapshot(ws.archiv) == before
