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


def free(n):
    return lambda path: SimpleNamespace(free=n)


@pytest.fixture
def imports(tmp_path):
    return Imports(tmp_path / "work", disk_usage=free(10 * 2**30))


def upload(imp, id, cesta, data, mtime=MTIME_MS, relace="r1"):
    if isinstance(data, str):
        data = data.encode()
    return imp.add_file(id, relace, cesta, io.BytesIO(data), len(data),
                        mtime)


def staged(imp, id):
    return sorted(os.path.relpath(os.path.join(d, f), imp.root / id)
                  for d, _, files in os.walk(imp.root / id) for f in files)


# --- staging ---------------------------------------------------------------

def test_upload_stores_record(imports):
    id = imports.create("r1", "Spáčil, David", 100)
    e = upload(imports, id, "Fotky/a.jpg", "obsah")
    assert e["nazev"] == "a.jpg" and e["ulozeno"] == "soubory/a.jpg"
    assert e["velikost"] == 5 and e["mtime_ns"] == MTIME_MS * 1_000_000
    assert e["sha256"] == importer.hashlib.sha256(b"obsah").hexdigest()
    record = imports.get(id, "r1")
    assert [s["cesta"] for s in record["soubory"]] == ["Fotky/a.jpg"]
    with pytest.raises(KeyError):
        imports.get(id, "r2")


def test_interrupted_upload_not_recorded(imports):
    id = imports.create("r1", "x")
    with pytest.raises(Refused) as e:
        imports.add_file(id, "r1", "a.jpg", io.BytesIO(b"kratsi"), 100)
    assert e.value.code == "neuplny"

    class Broken(io.BytesIO):
        def read(self, n=-1):
            raise ConnectionError("odpojeno")
    with pytest.raises(ConnectionError):
        imports.add_file(id, "r1", "b.jpg", Broken(), 100)
    assert imports.get(id, "r1")["soubory"] == []
    assert staged(imports, id) == ["import.json"]


def test_same_path_replaces_same_name_kept_apart(imports):
    id = imports.create("r1", "x")
    upload(imports, id, "a.jpg", "1")
    upload(imports, id, "a.jpg", "22")
    upload(imports, id, "Jine/A.JPG", "333")
    assert staged(imports, id) == ["import.json", "kolize/1/A.JPG",
                                   "soubory/a.jpg"]
    assert (imports.root / id / "soubory/a.jpg").read_text() == "22"


def test_thumbs_db_dropped(imports):
    id = imports.create("r1", "x")
    assert upload(imports, id, "Fotky/Thumbs.db", "x") is None
    assert imports.get(id, "r1")["soubory"] == []


def test_space_and_size_limits(tmp_path):
    imp = Imports(tmp_path / "work", disk_usage=free(importer.RESERVE + 10))
    with pytest.raises(Refused) as e:
        imp.create("r1", "x", 11)
    assert e.value.code == "malo_mista"
    id = imp.create("r1", "x", 10)
    with pytest.raises(Refused) as e:
        upload(imp, id, "a.jpg", "x" * 11)
    assert e.value.code == "malo_mista"
    big = SimpleNamespace(read=lambda n: pytest.fail("nemá číst"))
    with pytest.raises(Refused) as e:
        imp.add_file(id, "r1", "v.mp4", big, importer.MAX_FILE + 1)
    assert e.value.code == "prilis_velky"
    assert imp.get(id, "r1")["soubory"] == []


def test_discard_and_purge(tmp_path):
    clock = [1000.0]
    imp = Imports(tmp_path / "work", clock=lambda: clock[0],
                  disk_usage=free(10 * 2**30))
    old = imp.create("r1", "x")
    clock[0] += importer.MAX_AGE - 10
    fresh = imp.create("r1", "x")
    upload(imp, fresh, "a.jpg", "x")
    gone = imp.create("r1", "x")
    imp.discard(gone, "r1")
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
    id = imports.create("r1", "x")
    for i in range(4):
        upload(imports, id, f"G9/P150{i}.JPG", f"j{i}")
        upload(imports, id, f"G9/RAW/P150{i}.RW2", f"r{i}")
    upload(imports, id, "G9/Video/b.mp4", "v1")
    upload(imports, id, "c.MOV", "v2")
    upload(imports, id, "IMG-20260427-WA0001.jpg", "w")
    upload(imports, id, "prezentace.pptx", "p")
    upload(imports, id, "Thumbs.db", "t")
    o = imports.overview(id, "r1", exiftool=fake_exiftool)
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
    real = importer.file_sha256
    monkeypatch.setattr(importer, "file_sha256",
                        lambda p: calls.append(p) or real(p))
    importer.root_hashes(akce, {1}, cache)
    importer.root_hashes(akce, {1}, cache)
    assert len(calls) == 1
    (akce / "a.jpg").write_text("y")
    os.utime(akce / "a.jpg", ns=(1, 1))
    assert "y" not in importer.root_hashes(akce, {1}, cache).values()
    assert len(calls) == 2


def test_plan_new_event_dry(tree):
    root = tree({"archiv/": {}})
    before = snapshot(root)
    plan = importer.plan(None, [entry("a.jpg", "1"), entry("a.rw2", "2")])
    assert plan_ops(plan) == [("a.jpg", "a.jpg", "ok"),
                              ("a.rw2", "RAW.ignored/a.rw2", "ok")]
    assert snapshot(root) == before


# --- provedení -------------------------------------------------------------

def make_import(imp, files):
    id = imp.create("r1", "Spáčil, David")
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
    result = imports.execute(id, "r1", path)
    assert {o["stav"] for o in result["operace"]} == {"hotovo"}
    assert result["zahozeno"] and not (imports.root / id).exists()
    assert len(list(path.glob("*.JPG"))) == 40
    raws = list((path / "RAW.ignored").iterdir())
    assert len(raws) == 40
    a = path / "P0000007.JPG"
    assert a.read_text() == "j7"
    assert a.stat().st_mtime_ns == MTIME_MS * 1_000_000
    assert not list(path.rglob(".import-*"))
    ws = Workspace(archiv, tmp_path / "work")
    assert ws.list_events()[0]["stav"] == "nezpracovano"
    assert ws.list_events()[0]["souboru"] == 40


def test_execute_collision_after_plan(imports, tree, monkeypatch):
    akce = tree({"akce/": {}}) / "akce"
    id = make_import(imports, {"a.jpg": "nový", "b.jpg": "b"})
    stale = imports.plan(id, "r1", akce)
    (akce / "A.JPG").write_text("starý")
    monkeypatch.setattr(importer, "plan", lambda *a: stale)
    result = imports.execute(id, "r1", akce)
    assert plan_ops(result) == [("a.jpg", "a.jpg", "blokovano"),
                                ("b.jpg", "b.jpg", "hotovo")]
    assert (akce / "A.JPG").read_text() == "starý"
    assert sorted(p.name for p in akce.iterdir()) == ["A.JPG", "b.jpg"]
    assert staged(imports, id) == ["import.json", "soubory/a.jpg"]


def test_execute_collision_replanned(imports, tree):
    akce = tree({"akce/": {}}) / "akce"
    id = make_import(imports, {"a.jpg": "nový"})
    imports.plan(id, "r1", akce)
    (akce / "a.jpg").write_text("starý")
    result = imports.execute(id, "r1", akce)
    assert plan_ops(result) == [("a.jpg", "a.jpg", "blokovano")]
    assert (akce / "a.jpg").read_text() == "starý"


def test_execute_copy_error_continues(imports, tree, monkeypatch):
    akce = tree({"akce/": {}}) / "akce"
    id = make_import(imports, {"a.jpg": "a", "b.jpg": "b", "c.jpg": "c"})
    real = importer._copy

    def copy(src, event_dir, dst, sha, mtime):
        if dst == "b.jpg":
            raise PermissionError(13, "Permission denied", dst)
        real(src, event_dir, dst, sha, mtime)
    monkeypatch.setattr(importer, "_copy", copy)
    result = imports.execute(id, "r1", akce)
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
        importer._copy(root / "src.jpg", root / "akce", "a.jpg", "0" * 64, 0)
    assert list((root / "akce").iterdir()) == []


def test_create_event_race(tmp_path, monkeypatch):
    name = "2026-04-28 kontrola Stezky"
    real = importer.check_new_name

    def check(archiv, nazev):
        real(archiv, nazev)
        os.mkdir(archiv / nazev)  # jiný uživatel byl rychlejší
    monkeypatch.setattr(importer, "check_new_name", check)
    with pytest.raises(Refused) as e:
        importer.create_event(tmp_path, name)
    assert e.value.code == "existuje"


# --- API -------------------------------------------------------------------

def api_upload(c, id, files, relace="r1"):
    for cesta, data in files.items():
        r = c.post(f"/api/import/{id}/soubor", data=data.encode(),
                   query_string={"relace": relace, "cesta": cesta,
                                 "mtime": MTIME_MS})
        assert r.status_code == 200, r.json


def api_client(tmp_path, monkeypatch, zapis):
    from .test_app import make_client
    return make_client(tmp_path, monkeypatch, zapis=zapis)


R1 = {"relace": "r1", "jmeno": "Spáčil, David"}
R2 = {"relace": "r2", "jmeno": "Kopáčová, Jana"}


def test_api_dev_mode_plan_only(tmp_path, monkeypatch):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=False)
    before = snapshot(archiv)
    id = c.post("/api/import", json=dict(R1, celkem=10)).json["id"]
    api_upload(c, id, {"Nove/n.jpg": "n", "v.mp4": "0123456789",
                       "x.pptx": "p"})
    o = c.get(f"/api/import/{id}", query_string={"relace": "r1"}).json
    assert o["pocty"] == {"foto": 1, "video": 1, "nepodporovany": 1}
    assert c.get(f"/api/import/{id}",
                 query_string={"relace": "r2"}).status_code == 404
    plan = c.post(f"/api/import/{id}/plan",
                  json={"relace": "r1", "cil": EVENT}).json
    assert plan_ops(plan) == [("Nove/n.jpg", "n.jpg", "ok"),
                              ("v.mp4", "v.mp4", "duplicita")]
    r = c.post(f"/api/import/{id}/plan",
               json={"relace": "r1", "nova": EVENT.upper()})
    assert r.status_code == 409 and r.json["akce"] == EVENT
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    r = c.post(f"/api/import/{id}/provest", json={"relace": "r1",
                                                  "cil": EVENT})
    assert r.status_code == 403 and r.json["chyba"] == "vyvojovy_rezim"
    assert snapshot(archiv) == before
    assert c.delete(f"/api/import/{id}", json={"relace": "r2"}) \
        .status_code == 404
    assert c.delete(f"/api/import/{id}", json={"relace": "r1"}) \
        .status_code == 200
    assert c.get(f"/api/import/{id}",
                 query_string={"relace": "r1"}).status_code == 404


def test_api_existing_event_needs_lock(tmp_path, monkeypatch):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=True)
    id = c.post("/api/import", json=R1).json["id"]
    api_upload(c, id, {"n.jpg": "n"})
    c.post(f"/api/akce/{EVENT}/zamek", json=R2)
    body = {"relace": "r1", "cil": EVENT}
    r = c.post(f"/api/import/{id}/provest", json=body)
    assert r.status_code == 423
    assert r.json["drzitel"]["jmeno"] == R2["jmeno"]
    assert not (archiv / EVENT / "n.jpg").exists()
    assert c.get(f"/api/import/{id}",
                 query_string={"relace": "r1"}).json["pocty"] == {"foto": 1}
    c.delete(f"/api/akce/{EVENT}/zamek", json={"relace": "r2"})
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    r = c.post(f"/api/import/{id}/provest", json=body).json
    assert plan_ops(r) == [("n.jpg", "n.jpg", "hotovo")]
    assert (archiv / EVENT / "n.jpg").read_text() == "n"
    nove = c.get(f"/api/akce/{EVENT}").json["metadata"]["soubory"]
    assert "n.jpg" in nove


def test_api_new_event(tmp_path, monkeypatch):
    c, archiv = api_client(tmp_path, monkeypatch, zapis=True)
    name = "2026-04-28 kontrola Stezky"
    id = c.post("/api/import", json=R1).json["id"]
    api_upload(c, id, {"a.jpg": "a", "RAW/a.rw2": "r", "x.pptx": "p"})
    r = c.post(f"/api/import/{id}/provest",
               json={"relace": "r1", "nova": name}).json
    assert r["cil"] == name and not r["zahozeno"]
    assert sorted(os.listdir(archiv / name)) == ["RAW.ignored", "a.jpg"]
    lock = c.post(f"/api/akce/{name}/zamek", json=R2)
    assert lock.status_code == 409  # drží ho relace importu
    assert c.post(f"/api/import/{id}/provest", json={
        "relace": "r1", "nova": name}).json["chyba"] == "existuje"


def test_api_upload_errors(tmp_path, monkeypatch):
    c, _ = api_client(tmp_path, monkeypatch, zapis=False)
    id = c.post("/api/import", json=R1).json["id"]
    url = f"/api/import/{id}/soubor"
    q = {"relace": "r1", "cesta": "a.jpg"}
    assert c.post(url, data=b"x", query_string=dict(q, relace="r2")) \
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
    old = imp.create("r1", "x")
    (tmp_path / "archiv").mkdir()
    monkeypatch.setattr("fotoarchiv.app.Flask.run", lambda *a, **k: None)
    main(["--archiv", str(tmp_path / "archiv"), "--work", str(work)])
    assert not (work / "import" / old).exists()
