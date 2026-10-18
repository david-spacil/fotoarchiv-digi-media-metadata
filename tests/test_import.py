import io
import json
import os
from types import SimpleNamespace

import pytest

from fotoarchiv import importer, scan
from fotoarchiv.archive import Workspace
from fotoarchiv.importer import Imports, Refused
from .conftest import make_tree, snapshot

EVENT = "2026-04-28 kontrola"
MTIME_MS = 1777363200123  # 2026-04-28
ME = "Příkladný, Daniel"


def free(n):
    return lambda path: SimpleNamespace(free=n)


@pytest.fixture
def imports(tmp_path):
    return Imports(tmp_path / "work", disk_usage=free(10 * 2**30))


def upload(imp, id, cesta, data, mtime=MTIME_MS, jmeno=ME):
    if isinstance(data, str):
        data = data.encode()
    return imp.add_file(id, jmeno, cesta, io.BytesIO(data), len(data),
                        mtime)


def last(events):
    """Poslední událost generátoru (plán / výsledek)."""
    *_, final = events
    return final


def no_check(events):
    """Události bez průběhu kontroly poškozených souborů (`kontrola*`)."""
    return [e for e in events if not e["typ"].startswith("kontrola")]


def until(chunks, word):
    """První blok streamu se slovem `word` (přeskočí průběh kontroly)."""
    for chunk in chunks:
        if word in chunk:
            return chunk
    raise AssertionError(word)


def staged(imp, id):
    return sorted(os.path.relpath(os.path.join(d, f), imp.root / id)
                  for d, _, files in os.walk(imp.root / id) for f in files)


# --- staging ---------------------------------------------------------------

def test_upload_stores_record(imports):
    id = imports.create(ME, 100)
    e = upload(imports, id, "Fotky/a.jpg", "obsah")
    assert e["nazev"] == "a.jpg" and e["ulozeno"] == "soubory/a.jpg"
    assert e["velikost"] == 5 and e["mtime_ns"] == MTIME_MS * 1_000_000
    assert e["sha256"] == importer.hashlib.sha256(b"obsah").hexdigest()
    record = imports.get(id, ME)
    assert [s["cesta"] for s in record["soubory"]] == ["Fotky/a.jpg"]
    # Vlastník podle jména: jiné pořadí slov a diakritika nevadí.
    assert imports.get(id, "daniel prikladny") == record
    for other in ("Modelová, Jana", "", None):
        with pytest.raises(KeyError):
            imports.get(id, other)


def test_interrupted_upload_not_recorded(imports):
    id = imports.create(ME)
    with pytest.raises(Refused) as e:
        imports.add_file(id, ME, "a.jpg", io.BytesIO(b"kratsi"), 100)
    assert e.value.code == "neuplny"

    class Broken(io.BytesIO):
        def read(self, n=-1):
            raise ConnectionError("odpojeno")
    with pytest.raises(ConnectionError):
        imports.add_file(id, ME, "b.jpg", Broken(), 100)
    assert imports.get(id, ME)["soubory"] == []
    assert staged(imports, id) == ["import.json"]


def test_same_path_replaces_same_name_kept_apart(imports):
    id = imports.create(ME)
    upload(imports, id, "a.jpg", "1")
    upload(imports, id, "a.jpg", "22")
    upload(imports, id, "Jine/A.JPG", "333")
    assert staged(imports, id) == ["import.json", "kolize/1/A.JPG",
                                   "soubory/a.jpg"]
    assert (imports.root / id / "soubory/a.jpg").read_text() == "22"


def test_thumbs_db_dropped(imports):
    id = imports.create(ME)
    assert upload(imports, id, "Fotky/Thumbs.db", "x") is None
    assert imports.get(id, ME)["soubory"] == []


def test_space_and_size_limits(tmp_path):
    imp = Imports(tmp_path / "work", disk_usage=free(importer.RESERVE + 10))
    with pytest.raises(Refused) as e:
        imp.create(ME, 11)
    assert e.value.code == "malo_mista"
    id = imp.create(ME, 10)
    with pytest.raises(Refused) as e:
        upload(imp, id, "a.jpg", "x" * 11)
    assert e.value.code == "malo_mista"
    big = SimpleNamespace(read=lambda n: pytest.fail("nemá číst"))
    with pytest.raises(Refused) as e:
        imp.add_file(id, ME, "v.mp4", big, importer.MAX_FILE + 1)
    assert e.value.code == "prilis_velky"
    assert imp.get(id, ME)["soubory"] == []


def test_discard_and_purge(tmp_path):
    clock = [1000.0]
    imp = Imports(tmp_path / "work", clock=lambda: clock[0],
                  disk_usage=free(10 * 2**30))
    old = imp.create(ME)
    clock[0] += importer.MAX_AGE - 10
    fresh = imp.create(ME)
    upload(imp, fresh, "a.jpg", "x")
    gone = imp.create(ME)
    imp.discard(gone, ME)
    assert not (imp.root / gone).exists()
    clock[0] += 20
    assert imp.purge() == [old]
    assert sorted(p.name for p in imp.root.iterdir()) == [fresh]


def test_import_tmp_is_not_media(tmp_path):
    archiv = tmp_path / "archiv"
    make_tree(archiv.parent, {"archiv/": {f"{EVENT}/": {
        "a.jpg": "", ".import-x1.tmp": "", "RAW.ignored/": {}}}})
    ws = Workspace(archiv, tmp_path / "work")
    assert ws.list_events()[0]["souboru"] == 1
    media, other = scan.root_files(archiv / EVENT)
    assert [n for n, _ in media] == ["a.jpg"] and other == []


# --- přehled a plán --------------------------------------------------------

def fake_exiftool(event_dir, names):
    return {n: {"DateTimeOriginal": f"2026:04:{28 + i % 2}:09:00:00".replace(
        ":09", " 09"), "Make": "Panasonic", "Model": "DC-G9"}
        for i, n in enumerate(sorted(names)) if n.startswith("P")}


def test_overview_mixed(imports):
    id = imports.create(ME)
    for i in range(4):
        upload(imports, id, f"G9/P150{i}.JPG", f"j{i}")
        upload(imports, id, f"G9/RAW/P150{i}.RW2", f"r{i}")
    upload(imports, id, "G9/Video/b.mp4", "v1")
    upload(imports, id, "c.MOV", "v2")
    upload(imports, id, "IMG-20260427-WA0001.jpg", "w")
    upload(imports, id, "prezentace.pptx", "p")
    upload(imports, id, "Thumbs.db", "t")
    o = imports.overview(id, ME, exiftool=fake_exiftool)
    assert o["pocty"] == {"foto": 5, "raw": 4, "video": 2,
                          "nepodporovany": 1}
    assert o["od"] == "2026-04-27" and o["do"] == "2026-04-29"
    assert o["pristroje"] == ["Panasonic DC-G9"]
    assert o["nepodporovane"] == ["prezentace.pptx"]
    assert "G9/Video/b.mp4" in [s["cesta"] for s in o["soubory"]]


def test_new_name_validation(tmp_path):
    make_tree(tmp_path, {"2026-04-28 Kontrola/": {}, "jine/": {}})
    for bad in ("kontrola", "2026-04-28", "2026-13-01 x", "2026-04-28 a/b",
                "2026-04-28 a\\b", "2026-04-28 x ", "2026-04-28 x.", None):
        with pytest.raises(Refused) as e:
            importer.check_new_name(tmp_path, bad)
        assert e.value.code == "neplatny_nazev", bad
    with pytest.raises(Refused) as e:
        importer.check_new_name(tmp_path, "2026-04-28 kontrola")
    assert e.value.code == "existuje"
    assert e.value.detail["akce"] == "2026-04-28 Kontrola"
    importer.check_new_name(tmp_path, "2026-04-28 kontrola Stezky")


def entry(cesta, data, ulozeno=None):
    name = cesta.rsplit("/", 1)[-1]
    data = data.encode()
    return {"nazev": name, "cesta": cesta, "ulozeno": ulozeno or
            f"soubory/{name}", "velikost": len(data),
            "mtime_ns": MTIME_MS * 1_000_000,
            "sha256": importer.hashlib.sha256(data).hexdigest()}


def plan_ops(plan):
    return [(o["z"], o["do"], o["stav"]) for o in plan["operace"]]


def test_plan_collision_and_duplicates(tree, tmp_path):
    root = tree({"akce/": {"P1503712.JPG": "stary", "jine.jpg": "123456",
                           "RAW.ignored/": {"P1.rw2": ""}}})
    akce = root / "akce"
    entries = [entry("P1503712.JPG", "novy"),
               entry("kopie.jpg", "stary"),
               entry("a/x.jpg", "1"), entry("b/X.jpg", "2", "kolize/1/X.jpg"),
               entry("c/y.jpg", "3"), entry("d/y2.jpg", "3"),
               entry("P1.RW2", "r"), entry("P2.RW2", "r2"),
               entry("pozn.txt", "t"), entry("Thumbs.db", "")]
    cache = tmp_path / "sha.json"
    plan = importer.plan(akce, entries, cache)
    assert plan_ops(plan) == [
        ("P1.RW2", "RAW.ignored/P1.RW2", "blokovano"),
        ("P1503712.JPG", "P1503712.JPG", "blokovano"),
        ("P2.RW2", "RAW.ignored/P2.RW2", "ok"),
        ("a/x.jpg", "x.jpg", "blokovano"),
        ("b/X.jpg", "X.jpg", "blokovano"),
        ("c/y.jpg", "y.jpg", "ok"),
        ("d/y2.jpg", "y2.jpg", "duplicita"),
        ("kopie.jpg", "kopie.jpg", "duplicita"),
    ]
    dup = plan["operace"][-1]
    assert dup["blocked"] and "P1503712.JPG" in dup["duvod"]
    assert plan["nepodporovane"] == ["pozn.txt"]
    # Hash jen souborů shodné velikosti (jine.jpg má 6 B, nikdo z výběru ne).
    assert set(json.loads(cache.read_text())) == {"P1503712.JPG"}


def test_root_hashes_cached(tree, tmp_path, monkeypatch):
    akce = tree({"akce/": {"a.jpg": "x"}}) / "akce"
    cache = tmp_path / "sha.json"
    calls = []
    real = importer._sha256_steps

    def counting(path):
        calls.append(path)
        return (yield from real(path))
    monkeypatch.setattr(importer, "_sha256_steps", counting)
    importer.root_hashes(akce, {1}, cache)
    importer.root_hashes(akce, {1}, cache)
    assert len(calls) == 1
    (akce / "a.jpg").write_text("y")
    os.utime(akce / "a.jpg", ns=(1, 1))
    assert "y" not in importer.root_hashes(akce, {1}, cache).values()
    assert len(calls) == 2


def test_plan_progress_events(tree, tmp_path, monkeypatch):
    monkeypatch.setattr(importer, "STEP", 4)
    monkeypatch.setattr(importer, "CHUNK", 2)
    akce = tree({"akce/": {"a.jpg": "1234567890", "b.jpg": "abcdefghij",
                           "c.jpg": "kratsi"}}) / "akce"
    cache = tmp_path / "sha.json"
    importer.root_hashes(akce, {10}, cache)  # a, b v cache
    (akce / "d.jpg").write_text("0123456789")
    events = list(importer.iter_plan(akce, [entry("n.jpg", "x" * 10)],
                                     cache))
    assert events == [
        {"typ": "hash", "souboru": 3, "bajtu": 30},
        # z cache hned hotové, pak d.jpg po 4 B a po souboru
        {"typ": "hash_prubeh", "hotovo_souboru": 2, "hotovo_bajtu": 20},
        {"typ": "hash_prubeh", "hotovo_souboru": 2, "hotovo_bajtu": 24},
        {"typ": "hash_prubeh", "hotovo_souboru": 2, "hotovo_bajtu": 28},
        {"typ": "hash_prubeh", "hotovo_souboru": 3, "hotovo_bajtu": 30},
    ]
    # Bez souborů shodné velikosti se nic neporovnává.
    assert list(importer.iter_plan(akce, [entry("n.jpg", "x")], cache)) == []


def test_plan_new_event_dry(tree):
    root = tree({"archiv/": {}})
    before = snapshot(root)
    plan = importer.plan(None, [entry("a.jpg", "1"), entry("a.rw2", "2")])
    assert plan_ops(plan) == [("a.jpg", "a.jpg", "ok"),
                              ("a.rw2", "RAW.ignored/a.rw2", "ok")]
    assert snapshot(root) == before


# --- provedení -------------------------------------------------------------

def make_import(imp, files):
    id = imp.create(ME)
    for cesta, data in files.items():
        upload(imp, id, cesta, data)
    return id


def test_execute_new_event(imports, tmp_path):
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    files = {f"P{i:07}.JPG": f"j{i}" for i in range(40)}
    files.update({f"RAW/P{i:07}.RW2": f"r{i}" for i in range(40)})
    id = make_import(imports, files)
    path = importer.create_event(archiv, "2026-04-28 kontrola Stezky")
    result = last(imports.execute(id, ME, path))
    assert result["typ"] == "vysledek" and result["smazano"] == []
    assert {o["stav"] for o in result["operace"]} == {"hotovo"}
    assert result["zahozeno"] and not (imports.root / id).exists()
    assert len(list(path.glob("*.JPG"))) == 40
    raws = list((path / "RAW.ignored").iterdir())
    assert len(raws) == 40
    a = path / "P0000007.JPG"
    assert a.read_text() == "j7"
    umask = os.umask(0)
    os.umask(umask)
    assert a.stat().st_mode & 0o777 == 0o666 & ~umask
    assert a.stat().st_mtime_ns == MTIME_MS * 1_000_000
    assert not list(path.rglob(".import-*"))
    ws = Workspace(archiv, tmp_path / "work")
    assert ws.list_events()[0]["stav"] == "nezpracovano"
    assert ws.list_events()[0]["souboru"] == 40


def summary(e):
    o = e.get("operace") if e["typ"] == "soubor" else {}
    return (e["typ"], e.get("z") or o.get("z"),
            e.get("bajtu") or o.get("stav"))


def test_execute_events(imports, tree, monkeypatch):
    monkeypatch.setattr(importer, "STEP", 4)
    monkeypatch.setattr(importer, "CHUNK", 4)
    akce = tree({"akce/": {"x.jpg": "x"}}) / "akce"
    id = make_import(imports, {"a.jpg": "0123456789", "b.jpg": "b",
                               "c.jpg": "x"})
    events = no_check(imports.execute(id, ME, akce))
    assert [summary(e) for e in events] == [
        ("hash", None, 1), ("hash_prubeh", None, None),
        ("start", None, 11),
        ("prubeh", "a.jpg", 4), ("prubeh", "a.jpg", 8),
        ("soubor", "a.jpg", "hotovo"),
        ("soubor", "b.jpg", "hotovo"),
        ("soubor", "c.jpg", "duplicita"),
        ("vysledek", None, None),
    ]


def test_copy_progress_after_fsync(tree, monkeypatch):
    """Průběh kopie = data zapsaná na disk, ne do cache (SMB)."""
    monkeypatch.setattr(importer, "STEP", 4)
    monkeypatch.setattr(importer, "CHUNK", 4)
    root = tree({"src.jpg": "0123456789", "akce/": {}})
    synced = []
    real = os.fsync
    monkeypatch.setattr(importer.os, "fsync",
                        lambda fd: synced.append(os.fstat(fd).st_size)
                        or real(fd))
    sha = importer.file_sha256(root / "src.jpg")
    steps = list(importer._copy(root / "src.jpg", root / "akce", "a.jpg",
                                sha, 0))
    assert steps == [4, 8] and synced[:2] == [4, 8]


def test_execute_interrupted(imports, tree, monkeypatch):
    """Zavření záložky = zavření generátoru uprostřed kopie."""
    monkeypatch.setattr(importer, "STEP", 4)
    monkeypatch.setattr(importer, "CHUNK", 4)
    akce = tree({"akce/": {}}) / "akce"
    id = make_import(imports, {"a.jpg": "a", "b.jpg": "0123456789",
                               "c.jpg": "c"})
    events = imports.execute(id, ME, akce)
    for e in events:
        if e["typ"] == "prubeh":
            break
    # a.jpg je už pryč ze stagingu i z import.json, b.jpg se kopíruje.
    assert staged(imports, id) == ["import.json", "soubory/b.jpg",
                                   "soubory/c.jpg"]
    assert any(p.name.startswith(".import-") for p in akce.iterdir())
    events.close()
    assert sorted(p.name for p in akce.iterdir()) == ["a.jpg"]
    assert [s["cesta"] for s in imports.get(id, ME)["soubory"]] == \
        ["b.jpg", "c.jpg"]
    upload(imports, id, "d.jpg", "d")  # příznak provádění je pryč


def test_execute_running_refuses(imports, tree):
    akce = tree({"akce/": {}}) / "akce"
    id = make_import(imports, {"a.jpg": "a", "b.jpg": "b"})
    first = imports.execute(id, ME, akce)
    # Příznak provádění platí od první události (průběh kontroly).
    assert next(first)["typ"] == "kontrola"
    for action in (lambda: upload(imports, id, "c.jpg", "c"),
                   lambda: imports.discard(id, ME),
                   lambda: next(imports.execute(id, ME, akce))):
        with pytest.raises(Refused) as e:
            action()
        assert e.value.code == "probiha"
    assert imports.owned(ME)[0]["probiha"]
    result = last(first)
    assert [o["stav"] for o in result["operace"]] == ["hotovo", "hotovo"]
    assert sorted(p.name for p in akce.iterdir()) == ["a.jpg", "b.jpg"]


def test_purge_stale_tmp(imports, tree):
    akce = tree({"akce/": {".import-stary.tmp": "", ".import-cerstvy.tmp": "",
                           ".metadata-x.tmp": "", ".import-x.part": "",
                           "RAW.ignored/": {".import-raw.tmp": ""}}}) / "akce"
    old = importer.time.time() - importer.TMP_AGE - 60
    for name in (".import-stary.tmp", ".metadata-x.tmp", ".import-x.part",
                 "RAW.ignored/.import-raw.tmp"):
        os.utime(akce / name, (old, old))
    id = make_import(imports, {"a.jpg": "a"})
    result = last(imports.execute(id, ME, akce))
    assert result["smazano"] == [".import-stary.tmp",
                                 "RAW.ignored/.import-raw.tmp"]
    assert sorted(p.name for p in akce.iterdir()) == [
        ".import-cerstvy.tmp", ".import-x.part", ".metadata-x.tmp",
        "RAW.ignored", "a.jpg"]
    assert list((akce / "RAW.ignored").iterdir()) == []


def test_execute_collision_after_plan(imports, tree, monkeypatch):
    akce = tree({"akce/": {}}) / "akce"
    id = make_import(imports, {"a.jpg": "nový", "b.jpg": "b"})
    stale = last(imports.plan(id, ME, akce))
    (akce / "A.JPG").write_text("starý")

    def stale_plan(*a):
        return stale
        yield
    monkeypatch.setattr(importer, "iter_plan", stale_plan)
    result = last(imports.execute(id, ME, akce))
    assert plan_ops(result) == [("a.jpg", "a.jpg", "blokovano"),
                                ("b.jpg", "b.jpg", "hotovo")]
    assert (akce / "A.JPG").read_text() == "starý"
    assert sorted(p.name for p in akce.iterdir()) == ["A.JPG", "b.jpg"]
    assert staged(imports, id) == ["import.json", "soubory/a.jpg"]


def test_execute_collision_replanned(imports, tree):
    akce = tree({"akce/": {}}) / "akce"
    id = make_import(imports, {"a.jpg": "nový"})
    last(imports.plan(id, ME, akce))
    (akce / "a.jpg").write_text("starý")
    result = last(imports.execute(id, ME, akce))
    assert plan_ops(result) == [("a.jpg", "a.jpg", "blokovano")]
    assert (akce / "a.jpg").read_text() == "starý"


def test_execute_copy_error_continues(imports, tree, monkeypatch):
    akce = tree({"akce/": {}}) / "akce"
    id = make_import(imports, {"a.jpg": "a", "b.jpg": "b", "c.jpg": "c"})
    real = importer._copy

    def copy(src, event_dir, dst, sha, mtime):
        if dst == "b.jpg":
            raise PermissionError(13, "Permission denied", dst)
        return (yield from real(src, event_dir, dst, sha, mtime))
    monkeypatch.setattr(importer, "_copy", copy)
    result = last(imports.execute(id, ME, akce))
    assert plan_ops(result) == [("a.jpg", "a.jpg", "hotovo"),
                                ("b.jpg", "b.jpg", "chyba"),
                                ("c.jpg", "c.jpg", "hotovo")]
    assert "Permission denied" in result["operace"][1]["chyba"]
    assert sorted(p.name for p in akce.iterdir()) == ["a.jpg", "c.jpg"]
    assert staged(imports, id) == ["import.json", "soubory/b.jpg"]
    assert not result["zahozeno"]


def test_copy_cleans_tmp_on_changed_content(tree):
    root = tree({"src.jpg": "jiný obsah", "akce/": {}})
    with pytest.raises(OSError):
        importer._drain(importer._copy(root / "src.jpg", root / "akce",
                                       "a.jpg", "0" * 64, 0))
    assert list((root / "akce").iterdir()) == []


@pytest.mark.parametrize("folder", ["", ".ignored"])
def test_create_event_race(tmp_path, monkeypatch, folder):
    name = "2026-04-28 kontrola Stezky"
    real = importer.check_new_name

    def check(archiv, nazev):
        real(archiv, nazev)
        os.mkdir(archiv / (nazev + folder))  # jiný uživatel byl rychlejší
    monkeypatch.setattr(importer, "check_new_name", check)
    with pytest.raises(Refused) as e:
        importer.create_event(tmp_path, name)
    assert e.value.code == "existuje"
    assert os.listdir(tmp_path) == [name + folder]


def test_create_event_hidden(tmp_path):
    """Nová akce vzniká skrytá před Immichem (issue #13)."""
    name = "2026-04-28 kontrola Stezky"
    path = importer.create_event(tmp_path, name)
    assert path == tmp_path / f"{name}.ignored" and path.is_dir()
    assert os.listdir(tmp_path) == [f"{name}.ignored"]


@pytest.mark.parametrize("existing", [
    "2026-04-28 kontrola Stezky", "2026-04-28 kontrola Stezky.ignored",
    "2026-04-28 KONTROLA Stezky.ignored"])
def test_check_new_name_hidden_exists(tmp_path, existing):
    os.mkdir(tmp_path / existing)
    with pytest.raises(Refused) as e:
        importer.check_new_name(tmp_path, "2026-04-28 kontrola Stezky")
    assert e.value.code == "existuje"
    assert e.value.detail["akce"] == existing.removesuffix(".ignored")


@pytest.mark.parametrize("name", [
    "2026-04-28 kontrola Stezky.ignored", "2026-04-28 Stezky.IGNORED"])
def test_check_new_name_suffix_refused(tmp_path, name):
    with pytest.raises(Refused) as e:
        importer.check_new_name(tmp_path, name)
    assert e.value.code == "neplatny_nazev"


def test_activity_in_other_tab(imports, tree):
    id = make_import(imports, {"a.jpg": "a"})
    seen = []

    class Slow(io.BytesIO):
        def read(self, n=-1):
            chunk = super().read(2)
            if chunk:  # uprostřed nahrávání se dívá jiná záložka
                seen.append(imports.activity(id, "r2")["nahrava"])
                seen.append(imports.activity(id, "r1")["nahrava"])
            return chunk
    imports.add_file(id, ME, "v.mp4", Slow(b"0123"), 4, relace="r1")
    assert seen[0] == [{"cesta": "v.mp4", "prijato": 0, "velikost": 4}]
    assert seen[1] == []  # vlastní záložka
    assert imports.activity(id, "r2") == {"nahrava": [], "probiha": False}
    akce = tree({"akce/": {}}) / "akce"
    events = imports.execute(id, ME, akce, "r1")
    next(events)
    assert imports.activity(id, "r2")["probiha"]
    assert not imports.activity(id, "r1")["probiha"]
    events.close()
    assert not imports.activity(id, "r2")["probiha"]


def test_owned_and_target(imports):
    mine = make_import(imports, {"a.jpg": "a", "b.jpg": "bb"})
    imports.create("Modelová, Jana")
    imports.set_target(mine, ME, EVENT, False)
    [item] = imports.owned("daniel Prikladny")
    assert item["id"] == mine and item["souboru"] == 2
    assert item["velikost"] == 3 and item["cil"] == EVENT
    assert not item["nova"] and not item["probiha"]
    assert imports.overview(mine, ME, exiftool=fake_exiftool)["cil"] == EVENT
    assert imports.owned("Novák, Petr") == []


# --- skupiny ---------------------------------------------------------------

DOD = ["DOD 2015/DOD 2015_Jana/P1.JPG", "DOD 2015/DOD 2015_Jana/IMG_1.jpg",
       "DOD 2015/DOD 2015_Jana/RAW/P1.RW2",
       "DOD 2015/DOD 2015_Pavla/hloubka/a.mp4",
       "DOD 2015/DOD 2015_Pavla/b.jpg", "DOD 2015/c.jpg"]
DOD_DEVICES = {"P1.JPG": "Panasonic DC-G9", "IMG_1.jpg": "Apple iPhone 6",
               "b.jpg": "Samsung SM-A515F"}


def groups_of(entries, existing=None, devices=DOD_DEVICES, pripojit=None,
              **volba):
    chosen = {e["cesta"] for e in entries}
    return importer.group_plan(entries, chosen, devices, existing, volba,
                               pripojit)


def members(g):
    """{název skupiny: [soubory]}."""
    result = {}
    for name, gid in sorted(g["prirazeni"].items()):
        result.setdefault(g["skupiny"][gid]["nazev"], []).append(name)
    return result


def test_groups_by_subfolder():
    entries = [entry(c, c) for c in DOD]
    g = groups_of(entries, rezim="podslozky")
    # Dva přístroje v jedné podsložce = jedna skupina; RAW bez skupiny.
    assert members(g) == {"DOD 2015": ["c.jpg"],
                          "DOD 2015_Jana": ["IMG_1.jpg", "P1.JPG"],
                          "DOD 2015_Pavla": ["a.mp4", "b.jpg"]}
    assert g["nove"] == ["dod-2015", "dod-2015-jana", "dod-2015-pavla"]
    assert g["shody"] == {gid: [] for gid in g["nove"]}
    # Jen vybraná média (např. ok v plánu); kořen ze všech nahraných.
    g = importer.group_plan(entries, {DOD[1]}, {}, None,
                            {"rezim": "podslozky"})
    assert members(g) == {"DOD 2015_Jana": ["IMG_1.jpg"]}


def test_groups_without_subfolders_and_empty_root():
    flat = [entry("a.jpg", "a"), entry("b.jpg", "b")]
    assert groups_of(flat, rezim="podslozky")["prirazeni"] == {}
    assert members(groups_of(flat, rezim="jedna", nazev=" Import 2026 ")) \
        == {"Import 2026": ["a.jpg", "b.jpg"]}
    # Víc přetažení bez společného kořene.
    mixed = [entry("A/x.jpg", "x"), entry("B/C/y.jpg", "y"),
             entry("z.jpg", "z")]
    assert importer.selection_root(mixed) == []
    assert members(groups_of(mixed, rezim="podslozky")) == {
        "A": ["x.jpg"], "B": ["y.jpg"]}
    assert groups_of(mixed, rezim="zadne")["prirazeni"] == {}


def test_groups_auto_and_existing():
    entries = [entry(c, c) for c in DOD]
    g = groups_of(entries, rezim="auto")
    assert members(g)["Panasonic DC-G9"] == ["P1.JPG"]
    assert "P1.RW2" not in g["prirazeni"]
    existing = {"g9": {"nazev": "G9"}, "mobil": {"nazev": "Mobil"}}
    g = groups_of(entries, existing, rezim="existujici", skupina="g9")
    assert set(g["prirazeni"].values()) == {"g9"} and g["nove"] == []
    assert len(g["prirazeni"]) == 5
    for volba, code in (({"rezim": "x"}, "neplatne_skupiny"),
                        ({"rezim": "jedna", "nazev": " "},
                         "bez_nazvu_skupiny"),
                        ({"rezim": "existujici", "skupina": "jina"},
                         "neznama_skupina")):
        with pytest.raises(Refused) as e:
            importer.check_groups(volba, existing)
        assert e.value.code == code
    importer.check_groups(None, existing)


def test_groups_matches_not_joined():
    entries = [entry("DOD/DOD 2015_Jana/x.jpg", "x"),
               entry("DOD/DOD 2015_Verča/b.jpg", "b")]
    existing = {"dod-2015-jana": {"nazev": "dod 2015_JANA"},
                "mobil": {"nazev": "Mobil", "pristroj": "Samsung SM-A515F"},
                "verca": {"nazev": "DOD 2015_Verca"}}
    g = groups_of(entries, existing, rezim="podslozky")
    # Název odlišný od existujících (pořadové číslo), gid bez kolize.
    assert g["nove"] == ["dod-2015-jana-2", "dod-2015-verca-2"]
    assert g["skupiny"]["dod-2015-jana-2"]["nazev"] == "DOD 2015_Jana 2"
    assert g["skupiny"]["dod-2015-verca-2"]["nazev"] == "DOD 2015_Verča 2"
    assert g["shody"] == {"dod-2015-jana-2": ["dod-2015-jana"],
                          "dod-2015-verca-2": ["mobil", "verca"]}
    g = groups_of(entries, existing, rezim="podslozky",
                  pripojit={"dod-2015-jana-2": "dod-2015-jana",
                            "dod-2015-verca-2": "neni"})
    assert g["prirazeni"] == {"x.jpg": "dod-2015-jana",
                              "b.jpg": "dod-2015-verca-2"}
    assert g["nove"] == ["dod-2015-verca-2"]
    assert set(g["skupiny"]) == {"dod-2015-jana", "dod-2015-verca-2"}


def test_groups_auto_same_device_new_group():
    existing = {"sm-a515f": {"nazev": "Samsung SM-A515F",
                             "pristroj": "Samsung SM-A515F"}}
    g = groups_of([entry("b.jpg", "b"), entry("b2.jpg", "b2")], existing,
                  devices={"b.jpg": "Samsung SM-A515F",
                           "b2.jpg": "Samsung SM-A515F"}, rezim="auto")
    assert g["nove"] == ["samsung-sm-a515f-2"]
    assert set(g["prirazeni"].values()) == {"samsung-sm-a515f-2"}
    assert g["shody"]["samsung-sm-a515f-2"] == ["sm-a515f"]


def test_defaults_without_replan(imports, tree, monkeypatch):
    monkeypatch.setattr(scan, "run_exiftool", fake_exiftool)
    akce = tree({"akce/": {"x.jpg": "starý"}}) / "akce"
    id = make_import(imports, {"D/A/a.jpg": "a", "D/A/x.jpg": "x",
                               "D/B/P1.jpg": "b", "D/B/b.rw2": "r"})
    with pytest.raises(Refused) as e:
        imports.defaults(id, ME, {}, {"rezim": "auto"})
    assert e.value.code == "bez_planu"
    plan = last(imports.plan(id, ME, akce))
    assert "skupiny" not in plan
    assert all("skupina" not in o for o in plan["operace"])

    def replan(*a, **k):
        raise AssertionError("plán se počítá znovu")
    monkeypatch.setattr(importer, "iter_plan", replan)
    existing = {"a": {"nazev": "A"}}
    volba = {"rezim": "podslozky"}
    g = imports.defaults(id, ME, existing, volba)
    # Jen přenášená média: blokovaný x.jpg a RAW chybí.
    assert [(f["cesta"], f["pristroj"]) for f in g["soubory"]] == [
        ("D/A/a.jpg", None), ("D/B/P1.jpg", "Panasonic DC-G9")]
    assert members(g) == {"A 2": ["a.jpg"], "B": ["P1.jpg"]}
    assert g["shody"] == {"a-2": ["a"], "b": []}
    assert imports.overview(id, ME, exiftool=fake_exiftool)["skupiny"] \
        == volba
    g = imports.defaults(id, ME, existing, {"rezim": "auto"})
    assert set(g["prirazeni"]) == {"a.jpg", "P1.jpg"}
    assert g["skupiny"][g["prirazeni"]["P1.jpg"]]["pristroj"] == \
        "Panasonic DC-G9"
    g = imports.defaults(id, ME, existing,
                         {"rezim": "existujici", "skupina": "a"})
    assert g["prirazeni"] == {"a.jpg": "a", "P1.jpg": "a"}
    assert imports.get(id, ME)["existujici"] == ["a"]


def test_description_saved(imports):
    id = make_import(imports, {"a.jpg": "a"})
    popis = {"akce": {"autori": [ME]}, "skupiny": {"g": {"nazev": "G"}},
             "soubory": {"a.jpg": {"skupina": "g"}}, "pripojit": {}}
    imports.set_description(id, ME, popis)
    assert imports.overview(id, ME, exiftool=fake_exiftool)["popis"] == popis
    for bad in (None, [], {"akce": {}}, dict(popis, skupiny={"g": "G"}),
                dict(popis, soubory={"a.jpg": {"skupina": 7}}),
                dict(popis, pripojit={"g": None})):
        with pytest.raises(Refused) as e:
            imports.set_description(id, ME, bad)
        assert e.value.code == "neplatny_popis", bad
    with pytest.raises(KeyError):
        imports.set_description(id, "Modelová, Jana", popis)


def test_describe():
    popis = {"skupiny": {"g9": {"nazev": "G9"},  # existující, jen čte
                         "jana": {"nazev": "Jana", "autori": ["Novák, J"],
                                  "obliceje": []},
                         "verca": {"nazev": "Verča"},
                         "prazdna": {"nazev": "Prázdná"}},
             "soubory": {"a.jpg": {"skupina": "g9"},
                         "b.jpg": {"skupina": "jana"},
                         "c.jpg": {"skupina": "verca"},
                         "d.jpg": {"skupina": "prazdna"},
                         "e.jpg": {}},
             "pripojit": {"verca": "v"}}
    # `jana` mezitím obsadila jiná skupina; d.jpg se nepřenesl.
    existing = {"g9": {"nazev": "G9"}, "v": {"nazev": "V"},
                "jana": {"nazev": "Jiná"}}
    g = importer.describe(popis, ["a.jpg", "b.jpg", "c.jpg", "e.jpg"],
                          existing, {"g9", "v"})
    assert g["prirazeni"] == {"a.jpg": "g9", "b.jpg": "jana-2",
                              "c.jpg": "v"}
    assert g["skupiny"] == {"jana-2": {"nazev": "Jana",
                                       "autori": ["Novák, J"]}}
    assert g["nove"] == ["jana-2"]
    assert g["nazvy"] == {"g9": "G9", "jana-2": "Jana", "v": "V"}
    # Existující skupina, která mezitím zmizela: soubor bez skupiny.
    assert importer.describe(popis, ["a.jpg"], {}, {"g9"})["prirazeni"] == {}
    assert importer.describe(None, ["a.jpg"], {}, set())["prirazeni"] == {}


def test_proposal_merge(imports):
    assert imports.proposal(EVENT) is None
    imports.add_proposal(EVENT, {"skupiny": {"a": {"nazev": "A"}},
                                 "prirazeni": {"a.jpg": "a"}})
    imports.add_proposal(EVENT, {"skupiny": {"b": {"nazev": "B"}},
                                 "prirazeni": {"b.jpg": "b", "a.jpg": "b"}})
    assert imports.proposal(EVENT) == {
        "skupiny": {"a": {"nazev": "A"}, "b": {"nazev": "B"}},
        "prirazeni": {"a.jpg": "a", "b.jpg": "b"}}
    imports.drop_proposal(EVENT)
    assert imports.proposal(EVENT) is None


def test_apply_proposal():
    files = [{"nazev": "a.jpg", "pristroj": "Panasonic DC-G9"},
             {"nazev": "c.jpg", "pristroj": "Panasonic DC-G9"}]
    proposal = {"skupiny": {"dc-g9": {"nazev": "Jana"},
                            "prazdna": {"nazev": "Bez souborů"}},
                "prirazeni": {"a.jpg": "dc-g9", "pryc.jpg": "prazdna"}}
    g = importer.apply_proposal(files, proposal)
    assert g == {"skupiny": {"dc-g9": {"nazev": "Jana"},
                             "dc-g9-2": {"nazev": "Panasonic DC-G9",
                                         "pristroj": "Panasonic DC-G9"}},
                 "prirazeni": {"a.jpg": "dc-g9", "c.jpg": "dc-g9-2"}}


# --- API -------------------------------------------------------------------

def api_upload(c, id, files, jmeno=ME):
    for cesta, data in files.items():
        r = c.post(f"/api/import/{id}/soubor", data=data.encode(),
                   query_string={"jmeno": jmeno, "cesta": cesta,
                                 "mtime": MTIME_MS})
        assert r.status_code == 200, r.json


def api_client(tmp_path, monkeypatch, zapis):
    from .test_app import make_client
    return make_client(tmp_path, monkeypatch, zapis=zapis)


def stream(r):
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.mimetype == "application/x-ndjson"
    return [json.loads(line) for line in r.get_data(as_text=True).splitlines()]


R1 = {"relace": "r1", "jmeno": ME}
R2 = {"relace": "r2", "jmeno": "Modelová, Jana"}


def test_api_dev_mode_plan_only(tmp_path, monkeypatch):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=False)
    before = snapshot(archiv)
    id = c.post("/api/import", json=dict(R1, celkem=10)).json["id"]
    api_upload(c, id, {"Nove/n.jpg": "n", "v.mp4": "0123456789",
                       "x.pptx": "p"})
    o = c.get(f"/api/import/{id}", query_string={"jmeno": ME}).json
    assert o["pocty"] == {"foto": 1, "video": 1, "nepodporovany": 1}
    assert c.get(f"/api/import/{id}",
                 query_string={"jmeno": R2["jmeno"]}).status_code == 404
    events = stream(c.post(f"/api/import/{id}/plan",
                           json={"jmeno": ME, "cil": EVENT}))
    # IMG-…jpg, pozn.txt a v.mp4 v akci mají velikost jako nahrané
    assert [e["typ"] for e in no_check(events)] == ["hash"] + \
        ["hash_prubeh"] * 3 + ["plan"]
    plan = events[-1]
    assert plan["cil"] == EVENT and not plan["nova"]
    assert plan_ops(plan) == [("Nove/n.jpg", "n.jpg", "ok"),
                              ("v.mp4", "v.mp4", "duplicita")]
    r = c.post(f"/api/import/{id}/plan",
               json={"jmeno": ME, "nova": EVENT.upper()})
    assert r.status_code == 409 and r.json["akce"] == EVENT
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    r = c.post(f"/api/import/{id}/provest", json=dict(R1, cil=EVENT))
    assert r.status_code == 403 and r.json["chyba"] == "vyvojovy_rezim"
    assert snapshot(archiv) == before
    assert c.delete(f"/api/import/{id}", json={"jmeno": R2["jmeno"]}) \
        .status_code == 404
    assert c.delete(f"/api/import/{id}", json={"jmeno": ME}) \
        .status_code == 200
    assert c.get(f"/api/import/{id}",
                 query_string={"jmeno": ME}).status_code == 404


def test_api_list(tmp_path, monkeypatch):
    c, _ = api_client(tmp_path, monkeypatch, zapis=False)
    id = c.post("/api/import", json=R1).json["id"]
    api_upload(c, id, {"a.jpg": "a"})
    c.post("/api/import", json=R2)
    stream(c.post(f"/api/import/{id}/plan",
                  json={"jmeno": ME, "nova": "2026-04-28 nová"}))
    [item] = c.get("/api/import", query_string={"jmeno": "prikladny daniel"}) \
        .json["importy"]
    assert item["id"] == id and item["cil"] == "2026-04-28 nová"
    assert item["nova"] and item["souboru"] == 1
    assert c.get("/api/import").json["importy"] == []


def test_api_existing_event_needs_lock(tmp_path, monkeypatch):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=True)
    id = c.post("/api/import", json=R1).json["id"]
    api_upload(c, id, {"n.jpg": "n"})
    c.post(f"/api/akce/{EVENT}/zamek", json=R2)
    body = dict(R1, cil=EVENT)
    r = c.post(f"/api/import/{id}/provest", json=body)
    assert r.status_code == 423
    assert r.json["drzitel"]["jmeno"] == R2["jmeno"]
    assert not (archiv / EVENT / "n.jpg").exists()
    assert c.get(f"/api/import/{id}",
                 query_string={"jmeno": ME}).json["pocty"] == {"foto": 1}
    c.delete(f"/api/akce/{EVENT}/zamek", json={"relace": "r2"})
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    events = stream(c.post(f"/api/import/{id}/provest", json=body))
    assert [e["typ"] for e in no_check(events)] == [
        "hash", "hash_prubeh", "hash_prubeh", "start", "soubor",
        "vysledek"]
    r = events[-1]
    assert r["cil"] == EVENT and r["zahozeno"]
    assert plan_ops(r) == [("n.jpg", "n.jpg", "hotovo")]
    assert (archiv / EVENT / "n.jpg").read_text() == "n"
    nove = c.get(f"/api/akce/{EVENT}").json["metadata"]["soubory"]
    assert "n.jpg" in nove


def test_api_new_event(tmp_path, monkeypatch):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=True)
    name = "2026-04-28 kontrola Stezky"
    id = c.post("/api/import", json=R1).json["id"]
    api_upload(c, id, {"a.jpg": "a", "RAW/a.rw2": "r", "x.pptx": "p"})
    r = stream(c.post(f"/api/import/{id}/provest",
                      json=dict(R1, nova=name)))[-1]
    assert r["cil"] == name and not r["zahozeno"]
    # Skrytá před Immichem do dokončení; akce se jmenuje bez přípony.
    assert not (archiv / name).exists()
    assert sorted(os.listdir(archiv / f"{name}.ignored")) == [
        "RAW.ignored", "_metadata.json", "a.jpg"]
    assert name in [e["nazev"] for e in c.get("/api/akce").json]
    assert r["index"] == []
    row = next(line for line in (archiv / "_INDEX.md").read_text()
               .splitlines() if "kontrola Stezky" in line)
    assert [c.strip() for c in row.strip("│").split("│")][-2:] == ["1", "0"]
    html = (archiv / "_INDEX.html").read_text()
    assert 'data-stav="rozpracovano"' in html
    assert 'href="./2026-04-28%20kontrola%20Stezky.ignored/"' in html
    lock = c.post(f"/api/akce/{name}/zamek", json=R2)
    assert lock.status_code == 409  # drží ho relace importu
    assert c.post(f"/api/import/{id}/provest", json=dict(
        R1, nova=name)).json["chyba"] == "existuje"


def test_api_new_event_interrupted_releases_lock(tmp_path, monkeypatch):
    """Zavřená záložka zámek nové akce nepřevezme; server ho uvolní."""
    monkeypatch.setattr(importer, "STEP", 4)
    monkeypatch.setattr(importer, "CHUNK", 4)
    c, archiv = api_client(tmp_path, monkeypatch, zapis=True)
    name = "2026-04-28 kontrola Stezky"
    id = c.post("/api/import", json=R1).json["id"]
    api_upload(c, id, {"a.jpg": "0123456789", "b.jpg": "b"})
    r = c.post(f"/api/import/{id}/provest", json=dict(R1, nova=name),
               buffered=False)
    chunks = iter(r.response)
    until(chunks, b'"start"')
    assert b'"prubeh"' in next(chunks)
    r.close()
    assert os.listdir(archiv / f"{name}.ignored") == []
    assert c.post(f"/api/akce/{name}/zamek", json=R2).status_code == 200


def test_api_running_refused(tmp_path, monkeypatch):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=True)
    imports = c.application.config["IMPORTS"]
    id = c.post("/api/import", json=R1).json["id"]
    api_upload(c, id, {"a.jpg": "a"})
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    imports._running[id] = "r2"  # provedení v jiné záložce
    r = c.post(f"/api/import/{id}/soubor", data=b"b",
               query_string={"jmeno": ME, "cesta": "b.jpg"})
    assert r.status_code == 409 and r.json["chyba"] == "probiha"
    for r in (c.delete(f"/api/import/{id}", json={"jmeno": ME}),
              c.post(f"/api/import/{id}/provest", json=dict(R1, cil=EVENT))):
        assert r.status_code == 409 and r.json["chyba"] == "probiha"
    assert not (archiv / EVENT / "a.jpg").exists()


def test_api_upload_errors(tmp_path, monkeypatch):
    c, _ = api_client(tmp_path, monkeypatch, zapis=False)
    id = c.post("/api/import", json=R1).json["id"]
    url = f"/api/import/{id}/soubor"
    q = {"jmeno": ME, "cesta": "a.jpg"}
    assert c.post(url, data=b"x", query_string=dict(q, jmeno=R2["jmeno"])) \
        .status_code == 404
    assert c.post(url, data=b"x", query_string=dict(q, cesta="")) \
        .status_code == 400
    assert c.post(url, data=b"x", query_string=dict(q, mtime="x")) \
        .status_code == 400
    assert c.post("/api/import/neni/soubor", data=b"x", query_string=q) \
        .status_code == 404


def test_purge_on_start(tmp_path, monkeypatch):
    from fotoarchiv.__main__ import main
    work = tmp_path / "work"
    imp = Imports(work, clock=lambda: 0, disk_usage=free(10 * 2**30))
    old = imp.create(ME)
    (tmp_path / "archiv").mkdir()
    monkeypatch.setattr("fotoarchiv.__main__.serve", lambda *a, **k: None)
    main(["--archiv", str(tmp_path / "archiv"), "--work", str(work)])
    assert not (work / "import" / old).exists()


# --- API: skupiny ----------------------------------------------------------

def open_event(c, name=EVENT, relace=R1):
    """Průvodce akcí: první uložení `_metadata.json`."""
    c.post(f"/api/akce/{name}/zamek", json=relace)
    d = c.get(f"/api/akce/{name}").json
    r = c.put(f"/api/akce/{name}/metadata", json=dict(
        relace, metadata=d["metadata"], version=d["version"]))
    assert r.status_code == 200, r.json
    return d


def plan_and_defaults(c, id, volba, **target):
    """Plán a výchozí rozdělení (`POST …/skupiny`) jako klient."""
    stream(c.post(f"/api/import/{id}/plan", json=dict(jmeno=ME, **target)))
    r = c.post(f"/api/import/{id}/skupiny",
               json={"jmeno": ME, "skupiny": volba})
    assert r.status_code == 200, r.json
    return r.json


def save_description(c, id, d, akce=None, autori=None, pripojit=None):
    """Popis z rozdělení `d` ({skupiny, prirazeni}); `autori` = {gid:
    autoři skupiny}."""
    autori = autori or {}
    popis = {"akce": akce or {},
             "skupiny": {gid: dict(g, **({"autori": autori[gid]}
                                         if gid in autori else {}))
                         for gid, g in d["skupiny"].items()},
             "soubory": {n: {"skupina": gid}
                         for n, gid in d["prirazeni"].items()},
             "pripojit": pripojit or {}}
    r = c.put(f"/api/import/{id}/popis", json={"jmeno": ME, "popis": popis})
    assert r.status_code == 200, r.json
    return popis


def jpeg(color="red"):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), color).save(buf, "JPEG")
    return buf.getvalue()


def test_api_description_and_thumbs(tmp_path, monkeypatch):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=False)
    before = snapshot(archiv)
    id = c.post("/api/import", json=R1).json["id"]
    api_upload_bytes(c, id, {"W/a.jpg": jpeg(), "W/b.jpg": b"neni obrazek"})
    url = f"/api/import/{id}/popis"
    popis = {"akce": {}, "skupiny": {}, "soubory": {}, "pripojit": {}}
    assert c.put(url, json={"jmeno": ME, "popis": {"akce": {}}}) \
        .status_code == 400
    assert c.put(url, json={"jmeno": R2["jmeno"], "popis": popis}) \
        .status_code == 404
    assert c.put(url, json={"jmeno": ME, "popis": popis}).status_code == 200
    assert c.get(f"/api/import/{id}", query_string={"jmeno": ME}) \
        .json["popis"] == popis
    r = c.post(f"/api/import/{id}/skupiny",
               json={"jmeno": ME, "skupiny": {"rezim": "auto"}})
    assert r.status_code == 409 and r.json["chyba"] == "bez_planu"

    thumb = f"/api/import/{id}/nahled/W/a.jpg"
    r = c.get(thumb, query_string={"jmeno": ME})
    assert r.status_code == 200 and r.mimetype == "image/jpeg"
    assert c.get(thumb, query_string={"jmeno": ME, "velikost": 1600}) \
        .status_code == 200
    assert c.get(thumb, query_string={"jmeno": R2["jmeno"]}) \
        .status_code == 404
    for bad in ("W/neni.jpg", "W/b.jpg", "../import.json"):
        assert c.get(f"/api/import/{id}/nahled/{bad}",
                     query_string={"jmeno": ME}).status_code == 404, bad
    assert snapshot(archiv) == before


def test_api_source_thumb(tmp_path, monkeypatch):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=False)
    src = archiv / "přetřídit" / "DOD 2016"
    (src / "A").mkdir(parents=True)
    (src / "x.ignored").mkdir()
    (src / "A" / "a.jpg").write_bytes(jpeg())
    (src / "x.ignored" / "b.jpg").write_bytes(jpeg("blue"))
    before = snapshot(src)
    id = c.post("/api/import", json=dict(R1, zdroj="DOD 2016")).json["id"]
    url = f"/api/import/{id}/nahled/DOD 2016"
    assert c.get(f"{url}/A/a.jpg", query_string={"jmeno": ME}) \
        .status_code == 200
    for bad in ("x.ignored/b.jpg", "A/../x.ignored/b.jpg"):
        assert c.get(f"{url}/{bad}", query_string={"jmeno": ME}) \
            .status_code == 404, bad
    assert c.get(f"{url}/A/a.jpg", query_string={"jmeno": R2["jmeno"]}) \
        .status_code == 404
    assert snapshot(src) == before


def test_api_groups_into_event(tmp_path, monkeypatch):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=True)
    assert c.get(f"/api/akce/{EVENT}/skupiny").json == {
        "skupiny": None, "zdroj": None}
    open_event(c)
    before = c.get(f"/api/akce/{EVENT}").json["metadata"]
    assert c.get(f"/api/akce/{EVENT}/skupiny").json == {
        "skupiny": before["skupiny"], "zdroj": "metadata"}
    id = c.post("/api/import", json=R1).json["id"]
    files = {f"W/n{i}.jpg": f"n{i}" for i in range(3)}
    files["W/foto.jpg"] = "jiná"  # kolize jména s fotkou v akci
    api_upload(c, id, files)
    stream(c.post(f"/api/import/{id}/plan", json={"jmeno": ME, "cil": EVENT}))
    url = f"/api/import/{id}/skupiny"
    r = c.post(url, json={"jmeno": ME,
                          "skupiny": {"rezim": "jedna", "nazev": ""}})
    assert r.status_code == 409 and r.json["chyba"] == "bez_nazvu_skupiny"
    d = c.post(url, json={"jmeno": ME, "skupiny": {
        "rezim": "jedna", "nazev": "Workshop"}}).json
    assert d["nove"] == ["workshop"] and d["existujici"] == before["skupiny"]
    assert [f["nazev"] for f in d["soubory"]] == ["n0.jpg", "n1.jpg",
                                                 "n2.jpg"]
    assert d["akce_autori"] is None and d["cil"] == EVENT and not d["nova"]
    save_description(c, id, d, autori={"workshop": ["Modelová, Zuzana"]})
    r = stream(c.post(f"/api/import/{id}/provest",
                      json=dict(R1, cil=EVENT)))[-1]
    assert r["skupiny"]["zapsano"] and r["skupiny"]["nove"] == ["workshop"]
    assert [o["skupina"] for o in r["operace"]] == [None] + ["workshop"] * 3
    doc = c.get(f"/api/akce/{EVENT}").json["metadata"]
    assert doc["skupiny"] == dict(before["skupiny"], workshop={
        "nazev": "Workshop", "autori": ["Modelová, Zuzana"]})
    for i in range(3):
        assert doc["soubory"][f"n{i}.jpg"]["skupina"] == "workshop"
    assert "autori" not in doc["akce"]
    # Blokovaný soubor: existující záznam beze změny.
    assert doc["soubory"]["foto.jpg"] == before["soubory"]["foto.jpg"]
    assert (archiv / EVENT / "foto.jpg").read_bytes() != b"jin\xc3\xa1"

    # Zvolené připojení a autoři celé akce.
    id = c.post("/api/import", json=R1).json["id"]
    api_upload(c, id, {"X/m.jpg": "m"})
    d = plan_and_defaults(c, id, {"rezim": "jedna", "nazev": "Workshop"},
                          cil=EVENT)
    assert d["nove"] == ["workshop-2"]
    assert d["shody"] == {"workshop-2": ["workshop"]}
    save_description(c, id, d, akce={"autori": [ME]},
                     autori={"workshop-2": ["Jiný, Autor"]},
                     pripojit={"workshop-2": "workshop"})
    r = stream(c.post(f"/api/import/{id}/provest",
                      json=dict(R1, cil=EVENT)))[-1]
    assert r["skupiny"]["nove"] == [] and r["skupiny"]["nazvy"] == {
        "workshop": "Workshop"}
    doc = c.get(f"/api/akce/{EVENT}").json["metadata"]
    assert doc["soubory"]["m.jpg"]["skupina"] == "workshop"
    assert "workshop-2" not in doc["skupiny"]
    assert doc["skupiny"]["workshop"]["autori"] == ["Modelová, Zuzana"]
    assert doc["akce"]["autori"] == [ME]


def test_api_groups_conflict_keeps_files(tmp_path, monkeypatch):
    from fotoarchiv.archive import Conflict
    c, archiv = api_client(tmp_path, monkeypatch, zapis=True)
    open_event(c)
    ws = c.application.config["WORKSPACE"]

    def conflict(*a):
        raise Conflict("jina")
    monkeypatch.setattr(ws, "save", conflict)
    id = c.post("/api/import", json=R1).json["id"]
    api_upload(c, id, {"n.jpg": "n"})
    save_description(c, id, {"skupiny": {"x": {"nazev": "X"}},
                             "prirazeni": {"n.jpg": "x"}})
    r = stream(c.post(f"/api/import/{id}/provest",
                      json=dict(R1, cil=EVENT)))[-1]
    assert r["skupiny"]["zapsano"] is False
    assert r["skupiny"]["chyba"] == "konflikt"
    assert (archiv / EVENT / "n.jpg").read_text() == "n"


def test_api_new_event_description(tmp_path, monkeypatch):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=True)
    name = "2026-04-28 kontrola Stezky"
    id = c.post("/api/import", json=R1).json["id"]
    api_upload(c, id, {"S/a.jpg": "a", "S/dup/a2.jpg": "a", "S/c.jpg": "c",
                       "S/RAW/a.rw2": "r"})
    akce = {"nazev": "kontrola Stezky", "datum_od": "2026-04-28",
            "datum_do": "2026-04-29", "popis": "Kontrola", "mista": [],
            "ucastnici": [ME], "autori": ["Modelová, Zuzana"]}
    save_description(c, id, {
        "skupiny": {"g": {"nazev": "G", "autori": [ME]},
                    "prazdna": {"nazev": "Prázdná"}},
        "prirazeni": {"a.jpg": "g", "c.jpg": "g", "a2.jpg": "prazdna"}},
        akce=akce)
    r = stream(c.post(f"/api/import/{id}/provest",
                      json=dict(R1, nova=name)))[-1]
    assert r["skupiny"]["zapsano"] and not r["skupiny"]["navrh"]
    assert (archiv / f"{name}.ignored" / "_metadata.json").exists()
    d = c.get(f"/api/akce/{name}").json
    assert not d["novy"]
    doc = d["metadata"]
    assert doc["akce"] == {k: v for k, v in akce.items() if v}
    # Duplicita bez záznamu, skupina bez přeneseného souboru nevznikne.
    assert doc["skupiny"] == {"g": {"nazev": "G", "autori": [ME]}}
    assert {n: r["skupina"] for n, r in doc["soubory"].items()} == {
        "a.jpg": "g", "c.jpg": "g"}
    [e] = [e for e in c.get("/api/akce").json if e["nazev"] == name]
    assert e["stav"] == "rozpracovano"
    row = next(line for line in (archiv / "_INDEX.md").read_text()
               .splitlines() if "kontrola Stezky" in line)
    # Skupina přepisuje autory akce vlastními.
    assert "Příkladný" in row and "Modelová" not in row
    assert 'data-stav="rozpracovano"' in (archiv / "_INDEX.html").read_text()


def test_api_groups_proposal(tmp_path, monkeypatch):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=True)
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    id = c.post("/api/import", json=R1).json["id"]
    api_upload(c, id, {"DOD 2015/DOD 2015_Jana/a.jpg": "a",
                       "DOD 2015/DOD 2015_Pavla/b.jpg": "b"})
    volba = {"rezim": "podslozky"}
    d = plan_and_defaults(c, id, volba, cil=EVENT)
    assert d["existujici"] == {} and d["akce_autori"] is None
    save_description(c, id, d, akce={"autori": [ME]},
                     autori={"dod-2015-jana": ["Nováková, Jana"]})
    r = stream(c.post(f"/api/import/{id}/provest",
                      json=dict(R1, cil=EVENT)))[-1]
    assert r["skupiny"]["zapsano"] and r["skupiny"]["navrh"]
    assert not (archiv / EVENT / "_metadata.json").exists()
    g = c.get(f"/api/akce/{EVENT}/skupiny").json
    assert g["zdroj"] == "navrh"
    assert sorted(x["nazev"] for x in g["skupiny"].values()) == [
        "DOD 2015_Jana", "DOD 2015_Pavla"]

    # Druhý import: skupiny návrhu jsou existující, nic se nepřipojí.
    id = c.post("/api/import", json=R1).json["id"]
    api_upload(c, id, {"DOD/DOD 2015_Jana/c.jpg": "c"})
    d = plan_and_defaults(c, id, volba, cil=EVENT)
    assert d["nove"] == ["dod-2015-jana-2"]
    assert d["shody"] == {"dod-2015-jana-2": ["dod-2015-jana"]}
    assert d["akce_autori"] == [ME]
    save_description(c, id, d, akce={"autori": [ME]},
                     autori={"dod-2015-jana-2": ["Pokusná, Bára"]})
    stream(c.post(f"/api/import/{id}/provest", json=dict(R1, cil=EVENT)))
    g = c.get(f"/api/akce/{EVENT}/skupiny").json["skupiny"]
    assert {x["nazev"]: x.get("autori") for x in g.values()} == {
        "DOD 2015_Jana": ["Nováková, Jana"], "DOD 2015_Pavla": None,
        "DOD 2015_Jana 2": ["Pokusná, Bára"]}

    # Průvodce: návrh z importu s autory, soubor mimo návrh automaticky.
    d = c.get(f"/api/akce/{EVENT}").json
    assert d["novy"]
    doc = d["metadata"]
    assert doc["akce"]["autori"] == [ME]
    named = {n: doc["skupiny"][r["skupina"]] for n, r in
             doc["soubory"].items() if r.get("skupina")}
    assert named["a.jpg"] == {"nazev": "DOD 2015_Jana",
                              "autori": ["Nováková, Jana"]}
    assert named["b.jpg"]["nazev"] == "DOD 2015_Pavla"
    assert named["c.jpg"]["autori"] == ["Pokusná, Bára"]
    assert named["IMG-20260428-WA0001.jpg"]["nazev"] == "WhatsApp"
    r = c.put(f"/api/akce/{EVENT}/metadata",
              json=dict(R1, metadata=doc, version=None))
    assert r.status_code == 200
    assert c.get(f"/api/akce/{EVENT}/skupiny").json["zdroj"] == "metadata"
    assert not (tmp_path / "work" / "navrhy-skupin" / f"{EVENT}.json") \
        .exists()


# --- zdroj v přetřídit -----------------------------------------------------

@pytest.fixture
def source(tmp_path):
    """(Imports se zdrojem, archiv); `build(spec)` naplní `přetřídit`."""
    archiv = tmp_path / "archiv"
    (archiv / "přetřídit").mkdir(parents=True)
    imp = Imports(tmp_path / "work", disk_usage=free(10 * 2**30),
                  source_root=archiv / "přetřídit")

    def build(spec):
        make_tree(archiv / "přetřídit", spec)
        return imp, archiv
    return build


def test_source_create(source):
    imp, archiv = source({"DOD 2019/": {"a.jpg": "a"},
                          "_duplicity.ignored/": {}, "x.txt": "x"})
    for bad in ("../x", "..", "a/b", "_duplicity.ignored", "x.txt", "neni",
                "", 7):
        with pytest.raises(Refused) as e:
            imp.create(ME, zdroj=bad)
        assert e.value.code == "neplatny_zdroj", bad
    id = imp.create(ME, zdroj="DOD 2019", cil="2019-05-01 DOD 2019",
                    nova=True)
    assert imp.create("daniel prikladny", zdroj="DOD 2019") == id
    other = imp.create("Modelová, Jana", zdroj="DOD 2019")
    assert other != id
    [item] = imp.owned(ME)
    assert item["zdroj"] == "DOD 2019" and item["souboru"] == 1
    assert item["cil"] == "2019-05-01 DOD 2019" and item["nova"]
    with pytest.raises(Refused) as e:
        upload(imp, id, "b.jpg", "b")
    assert e.value.code == "ma_zdroj"
    assert sorted(os.listdir(imp.root / id)) == ["import.json"]


def test_source_overview_skips_ignored(source):
    imp, _ = source({"Procházka 60/": {
        "a.jpg": "a", "Thumbs.db": "t", "JPEG orig.ignored/": {"a.jpg": "x"},
        "NEF/": {"a.nef": "r"}}})
    id = imp.create(ME, zdroj="Procházka 60")
    o = imp.overview(id, ME, exiftool=fake_exiftool)
    assert [s["cesta"] for s in o["soubory"]] == [
        "Procházka 60/NEF/a.nef", "Procházka 60/a.jpg"]
    assert o["pocty"] == {"foto": 1, "raw": 1} and o["zdroj"] == "Procházka 60"


def test_source_groups_and_paths(source, monkeypatch):
    monkeypatch.setattr(scan, "run_exiftool", fake_exiftool)
    imp, archiv = source({"Vánoční večírek 2019_Pavlov/": {
        "Pavlov/": {"a.jpg": "a", "b.jpg": "bb"},
        "Pavlov2/": {"c.jpg": "ccc"}, "x.ignored/": {"d.jpg": "d"}}})
    name = "Vánoční večírek 2019_Pavlov"
    id = imp.create(ME, zdroj=name)
    last(imp.plan(id, ME, None))
    g = imp.defaults(id, ME, {}, {"rezim": "podslozky"})
    assert members(g) == {"Pavlov": ["a.jpg", "b.jpg"], "Pavlov2": ["c.jpg"]}
    root = archiv / "přetřídit" / name
    assert imp.file_path(id, ME, f"{name}/Pavlov/a.jpg") == \
        root / "Pavlov" / "a.jpg"
    for bad in ("Jiná/a.jpg", f"{name}/../x", f"{name}/x.ignored/d.jpg",
                name, f"{name}//a.jpg"):
        assert imp.file_path(id, ME, bad) is None, bad


def counting_sha(monkeypatch):
    calls = []
    real = importer._sha256_steps

    def counting(path):
        calls.append(os.path.basename(path))
        return (yield from real(path))
    monkeypatch.setattr(importer, "_sha256_steps", counting)
    return calls


def test_source_hash_only_same_size(source, monkeypatch):
    imp, archiv = source({"HLOZEK/": {"a.jpg": "1", "b.jpg": "22",
                                      "c.txt": "333"}})
    make_tree(archiv, {f"{EVENT}/": {"x.jpg": "4444", "y.txt": "1"}})
    calls = counting_sha(monkeypatch)
    id = imp.create(ME, zdroj="HLOZEK")
    events = list(imp.plan(id, ME, archiv / EVENT))
    # a.jpg má velikost jako y.txt v akci: hashuje se a.jpg a y.txt; sha256
    # zdroje už spočítala kontrola (jedno čtení), plán čte jen y.txt.
    assert calls == ["y.txt"]
    assert "HLOZEK/a.jpg" in json.loads(
        imp._source_sha_cache(imp.get(id, ME)).read_text())
    assert [e["typ"] for e in events][-1] == "plan"
    calls.clear()
    last(imp.plan(id, ME, None))
    assert calls == []  # nová akce, žádné shodné velikosti


def test_source_duplicate_stays(source):
    imp, archiv = source({"HLOZEK/": {"a.jpg": "dup", "b.jpg": "jiny",
                                      "c.jpg": "aaa", "d/": {"e.jpg": "aaa"}}})
    make_tree(archiv, {f"{EVENT}/": {"x.jpg": "dup"}})
    id = imp.create(ME, zdroj="HLOZEK")
    last(imp.plan(id, ME, archiv / EVENT))
    result = last(imp.execute(id, ME, archiv / EVENT))
    assert plan_ops(result) == [
        ("HLOZEK/a.jpg", "a.jpg", "duplicita"),
        ("HLOZEK/b.jpg", "b.jpg", "hotovo"),
        ("HLOZEK/c.jpg", "c.jpg", "hotovo"),
        ("HLOZEK/d/e.jpg", "e.jpg", "duplicita")]
    src = archiv / "přetřídit" / "HLOZEK"
    assert sorted(p.name for p in src.rglob("*")) == ["a.jpg", "d", "e.jpg"]
    assert result["zdroj_zbyva"] == {"foto": 2}
    assert not result["zdroj_smazan"] and not result["zahozeno"]
    assert imp.owned(ME)[0]["souboru"] == 2


def test_source_execute_moves(source):
    # Různé velikosti: bez možné duplicity se pro plán nic nehashuje.
    files = {f"P{i}.JPG": "j" * (i + 2) for i in range(5)}
    imp, archiv = source({"BONGO ZK/": files | {"Thumbs.db": "t",
                                                "RAW/": {"P0.RW2": "r"}}})
    src = archiv / "přetřídit" / "BONGO ZK"
    os.utime(src / "P3.JPG", ns=(MTIME_MS * 10**6, MTIME_MS * 10**6))
    id = imp.create(ME, zdroj="BONGO ZK")
    last(imp.plan(id, ME, None))
    path = importer.create_event(archiv, "2017-05-10 BONGO ZK")
    events = no_check(imp.execute(id, ME, path))
    assert [e["typ"] for e in events] == ["start"] + ["soubor"] * 6 + \
        ["vysledek"]
    result = events[-1]
    assert {o["stav"] for o in result["operace"]} == {"hotovo"}
    assert sorted(os.listdir(path)) == [f"P{i}.JPG" for i in range(5)] + [
        "RAW.ignored"]
    assert (path / "RAW.ignored" / "P0.RW2").read_text() == "r"
    assert (path / "P3.JPG").read_text() == "jjjjj"
    assert (path / "P3.JPG").stat().st_mtime_ns == MTIME_MS * 10**6
    assert not src.exists()
    assert result["zdroj_smazan"] and result["zdroj_zbyva"] == {}
    assert result["zahozeno"] and not (imp.root / id).exists()


def test_source_execute_blocked_and_vanished(source, monkeypatch):
    imp, archiv = source({"DOD/": {"a.jpg": "novy", "b.jpg": "b",
                                   "c.jpg": "c", "d.jpg": "d"}})
    make_tree(archiv, {f"{EVENT}/": {"A.JPG": "stary"}})
    src = archiv / "přetřídit" / "DOD"
    real = importer._move

    def move(s, event_dir, dst):
        if dst == "c.jpg":
            os.unlink(s)  # mezitím zmizel ze zdroje
        if dst == "d.jpg":
            raise OSError(18, "Invalid cross-device link")
        return (yield from real(s, event_dir, dst))
    monkeypatch.setattr(importer, "_move", move)
    id = imp.create(ME, zdroj="DOD")
    last(imp.plan(id, ME, archiv / EVENT))
    result = last(imp.execute(id, ME, archiv / EVENT))
    assert plan_ops(result) == [("DOD/a.jpg", "a.jpg", "blokovano"),
                                ("DOD/b.jpg", "b.jpg", "hotovo"),
                                ("DOD/c.jpg", "c.jpg", "chyba"),
                                ("DOD/d.jpg", "d.jpg", "chyba")]
    assert "už není" in result["operace"][2]["chyba"]
    assert "cross-device" in result["operace"][3]["chyba"]
    assert (archiv / EVENT / "A.JPG").read_text() == "stary"
    assert sorted(os.listdir(src)) == ["a.jpg", "d.jpg"]
    assert result["zdroj_zbyva"] == {"foto": 2}


def test_source_prune_leftovers(source):
    imp, archiv = source({"DOD 2016/": {
        "a.jpg": "a", "DOD 2016 _ fb/": {"b.jpg": "b", "x.docx": "d"},
        "prazdna/": {"Thumbs.db": "t", "hloubka/": {}},
        "JPEG orig.ignored/": {"a.jpg": "a"}}})
    id = imp.create(ME, zdroj="DOD 2016")
    last(imp.plan(id, ME, None))
    path = importer.create_event(archiv, "2016-05-01 DOD 2016")
    result = last(imp.execute(id, ME, path))
    src = archiv / "přetřídit" / "DOD 2016"
    assert sorted(os.listdir(src)) == ["DOD 2016 _ fb", "JPEG orig.ignored"]
    assert os.listdir(src / "DOD 2016 _ fb") == ["x.docx"]
    assert os.listdir(src / "JPEG orig.ignored") == ["a.jpg"]
    assert result["zdroj_zbyva"] == {"nepodporovany": 1}
    assert not result["zdroj_smazan"]
    assert result["zahozeno"]  # nic přenositelného nezůstalo


def test_source_discard_keeps_source(source):
    imp, archiv = source({"FotoKoule/": {"a.jpg": "a", "b/": {"c.jpg": "c"}}})
    before = snapshot(archiv)
    id = imp.create(ME, zdroj="FotoKoule")
    imp.overview(id, ME, exiftool=fake_exiftool)
    last(imp.plan(id, ME, None))
    imp.discard(id, ME)
    assert not (imp.root / id).exists()
    assert snapshot(archiv) == before


def test_source_against_last_plan(source):
    imp, archiv = source({"DOD/": {"a.jpg": "a", "b.jpg": "bb",
                                   "c.jpg": "ccc"}})
    src = archiv / "přetřídit" / "DOD"
    id = imp.create(ME, zdroj="DOD")
    with pytest.raises(Refused) as e:
        next(imp.execute(id, ME, archiv))
    assert e.value.code == "bez_planu"
    last(imp.plan(id, ME, None))
    (src / "a.jpg").unlink()                 # zmizel po plánu
    (src / "b.jpg").write_text("bbbb")       # změnil se po plánu
    (src / "nova.jpg").write_text("n")       # přibyl po plánu
    path = importer.create_event(archiv, "2019-05-01 DOD")
    result = last(imp.execute(id, ME, path))
    assert plan_ops(result) == [("DOD/a.jpg", "a.jpg", "chyba"),
                                ("DOD/b.jpg", "b.jpg", "blokovano"),
                                ("DOD/c.jpg", "c.jpg", "hotovo")]
    assert result["operace"][0]["chyba"] == "ve zdroji už není"
    assert result["operace"][1]["duvod"] == "změnil se po plánu"
    assert result["po_planu"] == ["DOD/nova.jpg"]
    assert os.listdir(path) == ["c.jpg"]
    assert sorted(os.listdir(src)) == ["b.jpg", "nova.jpg"]
    assert not result["zahozeno"]
    # Snímek je spotřebovaný: další provedení chce nový plán.
    with pytest.raises(Refused) as e:
        next(imp.execute(id, ME, path))
    assert e.value.code == "bez_planu"


# --- poškozené soubory (issue #10) -------------------------------------------
# Dekodéry nahrazuje conftest; test nul běží naostro: nečitelný = jen nuly,
# podezřelý = 64 KiB nul na konci.

UNREADABLE = bytes(70_000)
SUSPECT = b"x" * 4096 + bytes(64 * 1024)


def damaged_import(imp):
    id = imp.create(ME)
    upload(imp, id, "a.jpg", "zdrava")
    for cesta, data in (("b.jpg", UNREADABLE), ("c.jpg", SUSPECT)):
        imp.add_file(id, ME, cesta, io.BytesIO(data), len(data), MTIME_MS)
    return id


def checked(imp, id):
    return importer._drain(imp.iter_check(id, imp.get(id, ME)))


def kontrola(overview):
    return {f["cesta"]: f["kontrola"] and f["kontrola"]["stav"]
            for f in overview["soubory"]}


def test_check_overview_cached(imports, monkeypatch):
    id = damaged_import(imports)
    assert kontrola(imports.overview(id, ME, fake_exiftool)) == \
        {"a.jpg": None, "b.jpg": None, "c.jpg": None}
    results = checked(imports, id)
    assert {c: r["stav"] for c, r in results.items()} == {
        "a.jpg": "ok", "b.jpg": "necitelny", "c.jpg": "podezrely"}
    assert results["c.jpg"]["duvody"] == ["64 KiB nul na konci"]

    # Návrat k importu: výsledky hned, bez čtení.
    def no_read(*a, **k):
        raise AssertionError("čte soubor")
    monkeypatch.setattr(importer.integrity, "iter_check", no_read)
    o = imports.overview(id, ME, fake_exiftool)
    assert kontrola(o) == {"a.jpg": "ok", "b.jpg": "necitelny",
                           "c.jpg": "podezrely"}
    assert o["povolene_poskozene"] == []
    assert checked(imports, id) == results


def test_plan_damaged_and_allowed(imports):
    id = damaged_import(imports)
    plan = last(imports.plan(id, ME, None))
    assert plan_ops(plan) == [("a.jpg", "a.jpg", "ok"),
                              ("b.jpg", "b.jpg", "poskozeny"),
                              ("c.jpg", "c.jpg", "poskozeny")]
    b = plan["operace"][1]
    assert b["poskozeni"] == "necitelny" and b["blocked"]
    assert b["duvod"] == "soubor obsahuje jen nuly"
    # Povolit jde jen podezřelý; nečitelný se nepřenese ani s povolením.
    assert imports.set_allowed(id, ME, ["c.jpg", "b.jpg"]) == \
        ["b.jpg", "c.jpg"]
    assert plan_ops(last(imports.plan(id, ME, None))) == [
        ("a.jpg", "a.jpg", "ok"), ("b.jpg", "b.jpg", "poskozeny"),
        ("c.jpg", "c.jpg", "ok")]
    with pytest.raises(Refused):
        imports.set_allowed(id, ME, "c.jpg")


def test_execute_damaged_stays(imports, tree):
    akce = tree({"akce/": {}}) / "akce"
    id = damaged_import(imports)
    result = last(imports.execute(id, ME, akce))
    assert plan_ops(result) == [("a.jpg", "a.jpg", "hotovo"),
                                ("b.jpg", "b.jpg", "poskozeny"),
                                ("c.jpg", "c.jpg", "poskozeny")]
    assert os.listdir(akce) == ["a.jpg"]
    assert not result["zahozeno"]
    assert staged(imports, id) == ["import.json", "soubory/b.jpg",
                                   "soubory/c.jpg"]


def test_plan_rechecks_changed_file(imports):
    id = damaged_import(imports)
    checked(imports, id)
    path = imports.dir(id) / "soubory" / "a.jpg"
    path.write_bytes(UNREADABLE)
    os.utime(path, ns=(1, 1))
    ops = plan_ops(last(imports.plan(id, ME, None)))
    assert ops[0] == ("a.jpg", "a.jpg", "poskozeny")


# --- odebraná poloha (blokovat-odebranou-polohu, úkoly 2.1, 2.2) -------------
# Ověřený výstup exiftoolu: odebraná {"GPSVersionID": "0 0 0 0",
# "GPSLatitude": "", "GPSLongitude": ""} (Pixel 8a, Android 17).

def poloha_exiftool(event_dir, names):
    return {n: ({"GPSVersionID": "0 0 0 0", "GPSLatitude": "",
                 "GPSLongitude": ""} if "bez-polohy" in n else {})
            for n in names}


def stripped_import(imp):
    id = imp.create(ME)
    upload(imp, id, "ok.jpg", "data")
    upload(imp, id, "bez-polohy.jpg", "data2")
    return id


def test_overview_odebrana_poloha(imports):
    id = stripped_import(imports)
    o = imports.overview(id, ME, exiftool=poloha_exiftool)
    assert o["odebrana_poloha"] == ["bez-polohy.jpg"]
    assert {f["cesta"]: f["poloha_odebrana"] for f in o["soubory"]} == \
        {"bez-polohy.jpg": True, "ok.jpg": False}


def test_plan_odebrana_poloha_blocked(imports):
    id = stripped_import(imports)
    imports.overview(id, ME, exiftool=poloha_exiftool)
    plan = last(imports.plan(id, ME, None))
    assert plan_ops(plan) == [("bez-polohy.jpg", "bez-polohy.jpg",
                               "poskozeny"),
                              ("ok.jpg", "ok.jpg", "ok")]
    o = plan["operace"][0]
    assert o["poskozeni"] == "bez_polohy" and o["blocked"]
    assert o["duvod"] == "telefon odebral polohu"
    # Povolení jako u podezřelého se nenabízí: ani po set_allowed
    # se fotka nepřenese.
    assert imports.set_allowed(id, ME, ["bez-polohy.jpg"]) == \
        ["bez-polohy.jpg"]
    assert plan_ops(last(imports.plan(id, ME, None)))[0] == \
        ("bez-polohy.jpg", "bez-polohy.jpg", "poskozeny")


def test_execute_odebrana_poloha_stays(imports, tree):
    akce = tree({"akce/": {}}) / "akce"
    id = stripped_import(imports)
    imports.overview(id, ME, exiftool=poloha_exiftool)
    result = last(imports.execute(id, ME, akce))
    assert plan_ops(result) == [("bez-polohy.jpg", "bez-polohy.jpg",
                                 "poskozeny"),
                                ("ok.jpg", "ok.jpg", "hotovo")]
    assert os.listdir(akce) == ["ok.jpg"]
    assert not result["zahozeno"]
    assert "soubory/bez-polohy.jpg" in staged(imports, id)


def test_source_odebrana_poloha_stays(source):
    imp, archiv = source({"PXL/": {"ok.jpg": "a"}})
    src = archiv / "přetřídit" / "PXL"
    (src / "bez-polohy.jpg").write_text("x")
    id = imp.create(ME, zdroj="PXL")
    o = imp.overview(id, ME, exiftool=poloha_exiftool)
    assert o["odebrana_poloha"] == ["PXL/bez-polohy.jpg"]
    last(imp.plan(id, ME, None))
    path = importer.create_event(archiv, "2026-10-09 PXL")
    result = last(imp.execute(id, ME, path))
    assert plan_ops(result) == [
        ("PXL/bez-polohy.jpg", "bez-polohy.jpg", "poskozeny"),
        ("PXL/ok.jpg", "ok.jpg", "hotovo")]
    assert result["operace"][0]["poskozeni"] == "bez_polohy"
    assert os.listdir(src) == ["bez-polohy.jpg"]
    assert result["zdroj_zbyva"] == {"foto": 1}
    assert not result["zdroj_smazan"] and not result["zahozeno"]


def test_delete_damaged_upload(imports, caplog):
    id = damaged_import(imports)
    with pytest.raises(Refused) as e:
        imports.delete_damaged(id, ME, "b.jpg")
    assert e.value.code == "nezkontrolovano"
    checked(imports, id)
    imports.set_allowed(id, ME, ["c.jpg"])
    for cesta, code in (("a.jpg", "neni_poskozeny"), ("x.jpg", "nenalezen")):
        with pytest.raises(Refused) as e:
            imports.delete_damaged(id, ME, cesta)
        assert e.value.code == code
    with caplog.at_level("INFO"):
        assert imports.delete_damaged(id, ME, "c.jpg")["stav"] == "podezrely"
    assert "smazán poškozený soubor" in caplog.text
    record = imports.get(id, ME)
    assert [s["cesta"] for s in record["soubory"]] == ["a.jpg", "b.jpg"]
    assert record["povolene_poskozene"] == []
    assert staged(imports, id) == ["import.json", "soubory/a.jpg",
                                   "soubory/b.jpg"]
    with pytest.raises(KeyError):
        imports.delete_damaged(id, "Modelová, Jana", "b.jpg")


def test_delete_damaged_refused_while_running(imports, tree):
    akce = tree({"akce/": {}}) / "akce"
    id = damaged_import(imports)
    checked(imports, id)
    running = imports.execute(id, ME, akce)
    next(running)
    for action in (lambda: imports.delete_damaged(id, ME, "b.jpg"),
                   lambda: imports.set_allowed(id, ME, ["c.jpg"])):
        with pytest.raises(Refused) as e:
            action()
        assert e.value.code == "probiha"
    running.close()


def test_changed_after_check_not_deleted(imports):
    id = damaged_import(imports)
    checked(imports, id)
    path = imports.dir(id) / "soubory" / "b.jpg"
    os.utime(path, ns=(1, 1))
    with pytest.raises(Refused) as e:
        imports.delete_damaged(id, ME, "b.jpg")
    assert e.value.code == "nezkontrolovano"
    assert path.exists()


def test_size_mismatch_after_copy(imports, tree, monkeypatch):
    akce = tree({"akce/": {}}) / "akce"
    id = make_import(imports, {"a.jpg": "obsah"})
    monkeypatch.setattr(importer, "_target_size", lambda path: 1)
    result = last(imports.execute(id, ME, akce))
    (o,) = result["operace"]
    assert (o["stav"], o["chyba"]) == ("chyba", "velikost v cíli nesouhlasí")
    assert (akce / "a.jpg").read_text() == "obsah"  # v archivu zůstane
    assert staged(imports, id) == ["import.json", "soubory/a.jpg"]


def test_source_damaged_stays(source):
    imp, archiv = source({"HLOZEK/": {"a.jpg": "zdrava"}})
    src = archiv / "přetřídit" / "HLOZEK"
    (src / "20151107_140851.jpg").write_bytes(UNREADABLE)
    id = imp.create(ME, zdroj="HLOZEK")
    last(imp.plan(id, ME, None))
    path = importer.create_event(archiv, "2015-11-07 Hlozek")
    result = last(imp.execute(id, ME, path))
    assert plan_ops(result) == [
        ("HLOZEK/20151107_140851.jpg", "20151107_140851.jpg", "poskozeny"),
        ("HLOZEK/a.jpg", "a.jpg", "hotovo")]
    assert os.listdir(src) == ["20151107_140851.jpg"]
    assert result["zdroj_zbyva"] == {"foto": 1}
    assert not result["zdroj_smazan"] and not result["zahozeno"]


def test_source_delete_damaged(source):
    imp, archiv = source({"HLOZEK/": {"a.jpg": "zdrava"}})
    src = archiv / "přetřídit" / "HLOZEK"
    (src / "bad.jpg").write_bytes(UNREADABLE)
    id = imp.create(ME, zdroj="HLOZEK")
    last(imp.plan(id, ME, None))
    imp.delete_damaged(id, ME, "HLOZEK/bad.jpg")
    assert os.listdir(src) == ["a.jpg"]
    # Smazaný není „zmizelý po plánu“: provedení ho nehlásí jako chybu.
    path = importer.create_event(archiv, "2015-11-07 Hlozek")
    result = last(imp.execute(id, ME, path))
    assert plan_ops(result) == [("HLOZEK/a.jpg", "a.jpg", "hotovo")]
    assert result["zdroj_smazan"]


def test_source_size_mismatch_after_move(source, monkeypatch):
    imp, archiv = source({"HLOZEK/": {"a.jpg": "zdrava"}})
    id = imp.create(ME, zdroj="HLOZEK")
    last(imp.plan(id, ME, None))
    path = importer.create_event(archiv, "2015-11-07 Hlozek")
    monkeypatch.setattr(importer, "_target_size", lambda p: 0)
    (o,) = last(imp.execute(id, ME, path))["operace"]
    assert (o["stav"], o["chyba"]) == ("chyba", "velikost v cíli nesouhlasí")
    assert (path / "a.jpg").read_text() == "zdrava"


def test_source_check_feeds_plan_hashes(source, monkeypatch):
    # Plán po kontrole zdroj znovu nečte (sha256 z téhož průchodu).
    imp, archiv = source({"HLOZEK/": {"a.jpg": "1", "b.jpg": "2"}})
    id = imp.create(ME, zdroj="HLOZEK")
    checked(imp, id)
    calls = counting_sha(monkeypatch)
    monkeypatch.setattr(importer.integrity, "iter_check",
                        lambda *a: (_ for _ in ()).throw(AssertionError))
    plan = last(imp.plan(id, ME, None))
    # Stejná velikost: plán sha256 potřebuje (duplicity), bere je z cache.
    assert calls == []
    assert plan_ops(plan) == [("HLOZEK/a.jpg", "a.jpg", "ok"),
                              ("HLOZEK/b.jpg", "b.jpg", "ok")]


def api_upload_bytes(c, id, files, jmeno=ME):
    for cesta, data in files.items():
        r = c.post(f"/api/import/{id}/soubor", data=data,
                   query_string={"jmeno": jmeno, "cesta": cesta,
                                 "mtime": MTIME_MS})
        assert r.status_code == 200, r.json


def test_api_check_allow_delete(tmp_path, monkeypatch):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=False)
    before = snapshot(archiv)
    id = c.post("/api/import", json=dict(R1, celkem=10)).json["id"]
    api_upload_bytes(c, id, {"a.jpg": b"zdrava", "b.jpg": UNREADABLE,
                             "c.jpg": SUSPECT})
    r = c.post(f"/api/import/{id}/kontrola", json={"jmeno": ME})
    events = stream(r)
    assert [e["typ"] for e in events] == ["kontrola"] + \
        ["kontrola_prubeh"] * 3 + ["kontrola_hotovo"]
    assert {k: v["stav"] for k, v in events[-1]["vysledky"].items()} == {
        "a.jpg": "ok", "b.jpg": "necitelny", "c.jpg": "podezrely"}
    assert c.post(f"/api/import/{id}/kontrola",
                  json={"jmeno": R2["jmeno"]}).status_code == 404
    o = c.get(f"/api/import/{id}", query_string={"jmeno": ME}).json
    assert kontrola(o)["b.jpg"] == "necitelny"

    r = c.post(f"/api/import/{id}/poskozene",
               json={"jmeno": ME, "povolene": ["c.jpg"]})
    assert r.json == {"povolene": ["c.jpg"]}
    assert c.post(f"/api/import/{id}/poskozene",
                  json={"jmeno": ME, "povolene": "c"}).status_code == 400
    plan = stream(c.post(f"/api/import/{id}/plan",
                         json={"jmeno": ME, "nova": "2026-05-01 Nova"}))[-1]
    assert plan_ops(plan) == [("a.jpg", "a.jpg", "ok"),
                              ("b.jpg", "b.jpg", "poskozeny"),
                              ("c.jpg", "c.jpg", "ok")]

    r = c.delete(f"/api/import/{id}/soubor", json=dict(R1, cesta="a.jpg"))
    assert r.status_code == 409 and r.json["chyba"] == "neni_poskozeny"
    r = c.delete(f"/api/import/{id}/soubor", json=dict(R1, cesta="x.jpg"))
    assert r.status_code == 404
    r = c.delete(f"/api/import/{id}/soubor", json=dict(R2, cesta="b.jpg"))
    assert r.status_code == 404
    r = c.delete(f"/api/import/{id}/soubor", json=dict(R1, cesta="b.jpg"))
    assert r.status_code == 200 and r.json["smazano"] == "b.jpg"
    o = c.get(f"/api/import/{id}", query_string={"jmeno": ME}).json
    assert sorted(kontrola(o)) == ["a.jpg", "c.jpg"]
    # Nahraný soubor jde smazat i ve vývojovém režimu; archiv se nemění.
    assert snapshot(archiv) == before


def source_client(tmp_path, monkeypatch, zapis):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=zapis)
    src = archiv / "přetřídit" / "HLOZEK"
    src.mkdir(parents=True)
    (src / "a.jpg").write_text("zdrava")
    (src / "bad.jpg").write_bytes(UNREADABLE)
    id = c.post("/api/import", json=dict(R1, zdroj="HLOZEK")).json["id"]
    stream(c.post(f"/api/import/{id}/kontrola", json={"jmeno": ME}))
    return c, src, id


def test_api_source_delete_dev_mode_refused(tmp_path, monkeypatch):
    c, src, id = source_client(tmp_path, monkeypatch, zapis=False)
    r = c.delete(f"/api/import/{id}/soubor",
                 json=dict(R1, cesta="HLOZEK/bad.jpg"))
    assert r.status_code == 403 and r.json["chyba"] == "vyvojovy_rezim"
    assert sorted(os.listdir(src)) == ["a.jpg", "bad.jpg"]


def test_api_source_delete(tmp_path, monkeypatch):
    c, src, id = source_client(tmp_path, monkeypatch, zapis=True)
    locks = c.application.config["LOCKS"]
    locks.acquire("přetřídit/HLOZEK", "jina#přetřídit", "Modelová, Jana")
    r = c.delete(f"/api/import/{id}/soubor",
                 json=dict(R1, cesta="HLOZEK/bad.jpg"))
    assert r.status_code == 409 and r.json["chyba"] == "zdroj_obsazen"
    assert sorted(os.listdir(src)) == ["a.jpg", "bad.jpg"]
    locks.release("přetřídit/HLOZEK", "jina#přetřídit")
    r = c.delete(f"/api/import/{id}/soubor",
                 json=dict(R1, cesta="HLOZEK/bad.jpg"))
    assert r.status_code == 200
    assert os.listdir(src) == ["a.jpg"]
    assert locks.holder("přetřídit/HLOZEK") is None
