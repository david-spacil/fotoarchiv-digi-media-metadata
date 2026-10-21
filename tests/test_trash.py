import json
import os
from datetime import datetime, timedelta

import pytest

from fotoarchiv import albums, immich, index, names, naming, thumbs, trash
from fotoarchiv.archive import SCHEMA, Collision, Workspace
from .conftest import make_tree, snapshot
from .test_immich import KEY, URL, FakeImmich

EVENT = "2026-04-28 kontrola Naučné stezky"
OTHER = "2026-03-14 výzkum Ukázkovo"
NOW = datetime(2026, 10, 19, 14, 30, 12)


@pytest.fixture
def setup(tmp_path):
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    make_tree(archiv, {f"{EVENT}/": {"a.jpg": "x", "b.jpg": "yy",
                                     "Thumbs.db": "",
                                     "RAW.ignored/": {"a.rw2": "r"}},
                       f"{OTHER}/": {"c.jpg": "x"}})
    ws = Workspace(archiv, tmp_path / "work", zapis=True)
    ws.save(EVENT, {"schema": SCHEMA, "akce": {"nazev": "kontrola"},
                    "skupiny": {}, "soubory": {
                        "a.jpg": {"autori": ["Unikátní, Jméno"]}}}, None)
    work = ws.work
    stav = trash.Stav(ws, albums.Stavy(work), albums.Osoby(work),
                      naming.Odlozene(work))
    return ws, stav


def delete(ws, stav, nazev=EVENT, now=NOW, jmeno="Novák, Jan",
           duvod="duplicita"):
    return trash.delete(ws, nazev, jmeno, duvod, stav, now=now)


def record_of(ws, id):
    return json.loads((trash.root(ws) / id / trash.RECORD).read_text())


def with_state(ws, stav, nazev=EVENT):
    stav.alba.nastav(nazev, stav="rozpoznano", album="alb1")
    stav.osoby.nastav(nazev, 2, 3)
    stav.odlozene.odlozit("jan", nazev, "p1")
    ws.export_record_path(nazev).parent.mkdir(parents=True, exist_ok=True)
    ws.export_record_path(nazev).write_text(
        json.dumps({"version": "v1", "zapis": True}))


# --- smazání -----------------------------------------------------------------

def test_delete_moves_folder_with_record(setup):
    ws, stav = setup
    before = snapshot(ws.archiv / EVENT)
    result = delete(ws, stav)
    assert not (ws.archiv / EVENT).exists()
    path = trash.root(ws) / result["id"]
    assert result["id"].startswith("20261019T143012-")
    assert result["vysypat"] == "2026-10-26T14:30:12"
    after = snapshot(path)
    del after[trash.RECORD]
    assert after == before
    record = record_of(ws, result["id"])
    assert record == {"schema": trash.SCHEMA, "nazev": EVENT,
                      "slozka": EVENT, "smazal": "Novák, Jan",
                      "smazano": "2026-10-19T14:30:12",
                      "duvod": "duplicita", "stav": {}}
    assert ws.event_names() == [OTHER]
    with pytest.raises(KeyError):
        ws.event_dir(EVENT)


def test_delete_hidden_event(setup):
    ws, stav = setup
    os.rename(ws.archiv / EVENT, ws.archiv / f"{EVENT}.ignored")
    result = delete(ws, stav)
    assert record_of(ws, result["id"])["slozka"] == f"{EVENT}.ignored"
    assert not (ws.archiv / f"{EVENT}.ignored").exists()


def test_same_name_deleted_twice(setup):
    ws, stav = setup
    first = delete(ws, stav)
    make_tree(ws.archiv, {f"{EVENT}/": {"d.jpg": "z"}})
    second = delete(ws, stav)
    assert first["id"] != second["id"]
    assert (trash.root(ws) / first["id"] / "a.jpg").is_file()
    assert (trash.root(ws) / second["id"] / "d.jpg").is_file()


def test_failed_move_leaves_event_and_work(setup, monkeypatch):
    ws, stav = setup
    with_state(ws, stav)
    before = snapshot(ws.archiv / EVENT)

    def fail(src, dst):
        raise OSError("soubor drží jiný počítač")
    monkeypatch.setattr(trash.os, "rename", fail)
    with pytest.raises(OSError):
        delete(ws, stav)
    assert snapshot(ws.archiv / EVENT) == before
    assert stav.alba.polozka(EVENT)["album"] == "alb1"
    assert stav.odlozene.seznam("jan", EVENT) == ["p1"]
    assert ws.export_record_path(EVENT).is_file()


def test_collision_refused(setup):
    ws, stav = setup
    make_tree(ws.archiv, {f"{EVENT}.ignored/": {"e.jpg": "x"}})
    before = snapshot(ws.archiv)
    with pytest.raises(Collision):
        delete(ws, stav)
    assert snapshot(ws.archiv) == before


def test_development_mode_only_plans(setup):
    ws, stav = setup
    dev = Workspace(ws.archiv, ws.work, zapis=False)
    before = snapshot(ws.archiv)
    result = trash.delete(dev, EVENT, "Novák, Jan", "test", stav, now=NOW)
    assert result["id"] is None and result["slozka"] == EVENT
    assert result["vysypat"] == "2026-10-26T14:30:12"
    assert snapshot(ws.archiv) == before


# --- stav pracovního adresáře ----------------------------------------------

def test_state_moves_to_record_and_back(setup):
    ws, stav = setup
    with_state(ws, stav)
    cache = ws.work / "cache" / "kontrola" / f"{EVENT}.json"
    cache.parent.mkdir(parents=True)
    cache.write_text("{}")
    result = delete(ws, stav)
    record = record_of(ws, result["id"])["stav"]
    assert record["album"]["album"] == "alb1"
    assert record["osoby"]["pojmenovane"] == 2
    assert record["odlozene"] == {"jan": ["p1"]}
    assert record["export"] == {"version": "v1", "zapis": True}
    # Nová akce stejného názvu začíná s čistým stavem.
    assert stav.alba.polozka(EVENT) is None
    assert stav.osoby.polozka(EVENT) is None
    assert stav.odlozene.seznam("jan", EVENT) == []
    assert not ws.export_record_path(EVENT).exists()
    assert not cache.exists()
    assert trash.restore(ws, result["id"], stav) == EVENT
    assert stav.alba.polozka(EVENT)["album"] == "alb1"
    assert stav.osoby.polozka(EVENT)["celkem"] == 3
    assert stav.odlozene.seznam("jan", EVENT) == ["p1"]
    assert ws.export_version(EVENT) == "v1"


def test_other_event_state_untouched(setup):
    ws, stav = setup
    with_state(ws, stav, OTHER)
    delete(ws, stav)
    assert stav.alba.polozka(OTHER)["album"] == "alb1"
    assert stav.odlozene.seznam("jan", OTHER) == ["p1"]


# --- obnovení ----------------------------------------------------------------

def test_restore_hidden_event(setup):
    ws, stav = setup
    os.rename(ws.archiv / EVENT, ws.archiv / f"{EVENT}.ignored")
    result = delete(ws, stav)
    trash.restore(ws, result["id"], stav)
    path = ws.archiv / f"{EVENT}.ignored"
    assert (path / "a.jpg").is_file() and (path / "_metadata.json").is_file()
    assert not (path / trash.RECORD).exists()
    assert ws.event_names() == [EVENT, OTHER]
    assert not (trash.root(ws) / result["id"]).exists()


@pytest.mark.parametrize("nova", [EVENT, f"{EVENT}.ignored"])
def test_restore_refused_when_name_taken(setup, nova):
    ws, stav = setup
    result = delete(ws, stav)
    make_tree(ws.archiv, {f"{nova}/": {"d.jpg": "z"}})
    before = snapshot(ws.archiv)
    with pytest.raises(trash.Refused) as e:
        trash.restore(ws, result["id"], stav)
    assert e.value.code == "obsazeno"
    assert snapshot(ws.archiv) == before


def test_unknown_folder(setup):
    ws, stav = setup
    make_tree(ws.archiv, {f"{trash.TRASH}/": {"cizi/": {"x.jpg": "x"}}})
    assert trash.entries(ws, NOW) == [{"id": "cizi", "neznama": True,
                                       "bajtu": None}]
    with pytest.raises(trash.Refused) as e:
        trash.restore(ws, "cizi", stav)
    assert e.value.code == "neznama"
    for bad in ("..", "../archiv", ".skryta", "neni"):
        with pytest.raises(KeyError):
            trash.restore(ws, bad, stav)


def test_entries(setup):
    ws, stav = setup
    first = delete(ws, stav, now=NOW - timedelta(days=2))
    second = delete(ws, stav, nazev=OTHER, now=NOW - timedelta(hours=1),
                    jmeno="Modelová, Zuzana", duvod="test")
    items = trash.entries(ws, NOW)
    assert [i["id"] for i in items] == [second["id"], first["id"]]
    assert items[1] == {"id": first["id"], "nazev": EVENT,
                        "smazal": "Novák, Jan",
                        "smazano": "2026-10-17T14:30:12",
                        "duvod": "duplicita", "souboru": 2, "bajtu": None,
                        "vysypat": "2026-10-24T14:30:12", "zbyva_dni": 5}
    assert items[0]["zbyva_dni"] == 7
    velikosti = {first["id"]: {"bajtu": 3_000, "cas": "2026-10-19T14:00"}}
    items = trash.entries(ws, NOW, velikosti=velikosti)
    assert [i["bajtu"] for i in items] == [None, 3_000]


# --- akce v koši jinde nejsou ------------------------------------------------

def test_trashed_event_invisible(setup):
    ws, stav = setup
    known = names.NameIndex(ws.metadata_files)
    assert "Unikátní, Jméno" in known.names()
    delete(ws, stav)
    assert ws.event_names() == [OTHER]
    assert [e["nazev"] for e in ws.list_events()] == [OTHER]
    assert "Unikátní, Jméno" not in known.names()
    assert [r["nazev"] for r in index.collect(ws)] == ["výzkum Ukázkovo"]


def test_new_event_with_trashed_name(setup):
    ws, stav = setup
    delete(ws, stav)
    make_tree(ws.archiv, {f"{EVENT}/": {"d.jpg": "z"}})
    assert ws.load(EVENT) == (None, None)
    assert ws.event_names() == [EVENT, OTHER]


# --- vysypání ----------------------------------------------------------------

def test_purge_after_deadline(setup):
    ws, stav = setup
    old = delete(ws, stav, now=NOW - timedelta(days=8))
    young = delete(ws, stav, nazev=OTHER, now=NOW - timedelta(days=6))
    assert trash.purge(ws, NOW) == [EVENT]
    assert not (trash.root(ws) / old["id"]).exists()
    assert (trash.root(ws) / young["id"] / "c.jpg").is_file()


def test_purge_skips_folder_without_record(setup):
    ws, stav = setup
    make_tree(ws.archiv, {f"{trash.TRASH}/": {"cizi/": {"x.jpg": "x"}}})
    old = os.path.getmtime(ws.archiv / trash.TRASH / "cizi") - 30 * 86400
    os.utime(ws.archiv / trash.TRASH / "cizi", (old, old))
    assert trash.purge(ws, NOW) == []
    assert (trash.root(ws) / "cizi" / "x.jpg").is_file()


def test_purge_does_not_follow_symlinks(setup, tmp_path):
    ws, stav = setup
    outside = tmp_path / "venku"
    make_tree(tmp_path, {"venku/": {"cenne.jpg": "x"}})
    os.symlink(outside, ws.archiv / EVENT / "odkaz")
    os.symlink(outside / "cenne.jpg", ws.archiv / EVENT / "soubor.jpg")
    old = delete(ws, stav, now=NOW - timedelta(days=8))
    os.symlink(outside, trash.root(ws) / "odkaz-ven")
    assert trash.purge(ws, NOW) == [EVENT]
    assert not (trash.root(ws) / old["id"]).exists()
    assert (outside / "cenne.jpg").is_file()
    assert (trash.root(ws) / "odkaz-ven").is_symlink()


def test_purge_nothing_in_development_mode(setup):
    ws, stav = setup
    delete(ws, stav, now=NOW - timedelta(days=8))
    dev = Workspace(ws.archiv, ws.work, zapis=False)
    before = snapshot(ws.archiv)
    assert trash.purge(dev, NOW) == []
    assert snapshot(ws.archiv) == before


def test_purge_drops_thumbnails(setup):
    ws, stav = setup
    cache = ws.work / "cache"

    def make(src, dst, size):
        open(dst, "wb").write(b"jpg")
    thumb = thumbs.thumbnail(ws.archiv / EVENT / "a.jpg", cache,
                             make_image=make)
    other = thumbs.thumbnail(ws.archiv / OTHER / "c.jpg", cache,
                             make_image=make)
    delete(ws, stav, now=NOW - timedelta(days=8))
    assert thumb.exists()           # obnovení náhledy dál použije
    trash.purge(ws, NOW)
    assert not thumb.exists() and other.exists()


def test_purge_interrupted_finishes_later(setup, monkeypatch):
    ws, stav = setup
    old = delete(ws, stav, now=NOW - timedelta(days=8))
    real = trash.os.unlink
    calls = []

    def flaky(path, **kw):
        if str(path).endswith("b.jpg") and not calls:
            calls.append(path)
            raise OSError("soubor drží jiný počítač")
        real(path, **kw)
    monkeypatch.setattr(trash.os, "unlink", flaky)
    assert trash.purge(ws, NOW) == []
    assert (trash.root(ws) / old["id"] / trash.RECORD).is_file()
    assert trash.purge(ws, NOW) == [EVENT]
    assert not (trash.root(ws) / old["id"]).exists()


# --- album v Immichi ---------------------------------------------------------

def client_for(fake):
    return immich.Client(URL, KEY, fake)


def test_purge_deletes_album(setup):
    ws, stav = setup
    fake = FakeImmich()
    fake.albums["alb1"] = {"id": "alb1", "albumName": EVENT,
                           "assetIds": ["a1"]}
    fake.albums["alb2"] = {"id": "alb2", "albumName": OTHER,
                           "assetIds": []}
    with_state(ws, stav)
    delete(ws, stav, now=NOW - timedelta(days=8))
    trash.purge(ws, NOW, client=client_for(fake))
    assert list(fake.albums) == ["alb2"]
    assert ("DELETE", "/api/albums/alb1", None) in fake.writes
    assert albums.KosAlba(ws.work).nacti() == {}


def test_album_retried_when_immich_fails(setup):
    ws, stav = setup
    fake = FakeImmich()
    fake.albums["alb1"] = {"id": "alb1", "albumName": EVENT,
                           "assetIds": []}
    with_state(ws, stav)
    old = delete(ws, stav, now=NOW - timedelta(days=8))
    fake.fail = "/api/albums/alb1"
    assert trash.purge(ws, NOW, client=client_for(fake)) == [EVENT]
    assert not (trash.root(ws) / old["id"]).exists()
    assert albums.KosAlba(ws.work).nacti() == {"alb1": EVENT}
    fake.fail = None
    trash.purge(ws, NOW, client=client_for(fake))
    assert fake.albums == {}
    assert albums.KosAlba(ws.work).nacti() == {}


def test_missing_album_leaves_queue(setup):
    ws, stav = setup
    with_state(ws, stav)
    delete(ws, stav, now=NOW - timedelta(days=8))
    trash.purge(ws, NOW, client=client_for(FakeImmich()))  # 404
    assert albums.KosAlba(ws.work).nacti() == {}
