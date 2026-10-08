import json
import stat
from urllib.parse import parse_qs, urlsplit

import pytest

from fotoarchiv import immich
from fotoarchiv.app import create_app
from fotoarchiv.archive import SCHEMA
from .conftest import make_tree

EVENT = "2026-09-08 Konference Dějiny archeologie"
OTHER = "2026-09-20 bez metadat"
URL = "http://immich.test:2283"
KEY = "tajny-klic-W4No"
ROOT = "/mnt/media/fotoarchiv/fotoarchiv_fotodokumentace_digitalni_ARUB"


def face(name, box=(252, 296, 293, 352), size=(1000, 750)):
    return {"imageWidth": size[0], "imageHeight": size[1],
            "boundingBoxX1": box[0], "boundingBoxY1": box[1],
            "boundingBoxX2": box[2], "boundingBoxY2": box[3],
            "sourceType": "machine-learning",
            "person": {"id": f"p-{name}", "name": name} if name is not None
            else None}


class FakeImmich:
    """Podvržené API: osoby, assety (id → cesta) a obličeje assetů."""

    def __init__(self):
        self.people = []
        self.paths = {}
        self.faces = {}
        self.fail = None        # část URL, na které dotaz selže
        self.calls = []

    def add(self, asset_id, path, *faces):
        self.paths[asset_id] = path
        self.faces[asset_id] = list(faces)
        for f in faces:
            p = f["person"]
            if p and p not in self.people:
                self.people.append(p)

    def __call__(self, method, url, klic, body=None):
        self.calls.append((method, url))
        assert klic == KEY
        if self.fail and self.fail in url:
            raise immich.ImmichError(f"HTTP 403 {url}")
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        if parts.path == "/api/server/version":
            return {"major": 3, "minor": 3, "patch": 0, "prerelease": 2}
        if parts.path == "/api/people":
            page, size = int(query["page"][0]), int(query["size"][0])
            chunk = self.people[(page - 1) * size:page * size]
            return {"people": chunk, "total": len(self.people),
                    "hasNextPage": page * size < len(self.people)}
        if parts.path == "/api/search/metadata":
            ids = [a for a in sorted(self.paths) if not body.get("personIds")
                   or any((f["person"] or {}).get("id") in body["personIds"]
                          for f in self.faces[a])]
            page, size = body["page"], body["size"]
            chunk = ids[(page - 1) * size:page * size]
            more = page * size < len(ids)
            return {"assets": {
                "items": [{"id": a, "originalPath": self.paths[a]}
                          for a in chunk],
                "nextPage": str(page + 1) if more else None}}
        if parts.path == "/api/faces":
            return self.faces[query["id"][0]]
        raise AssertionError(url)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    make_tree(archiv, {f"{EVENT}/": {"P9109996.JPG": "x", "b.jpg": "x"},
                       f"{OTHER}/": {"c.jpg": "x"}})
    monkeypatch.setattr("fotoarchiv.scan.run_exiftool", lambda d, n: {})
    fake = FakeImmich()
    app = create_app(archiv, tmp_path / "work", immich_fetch=fake,
                     prihlaseni=False)
    app.testing = True
    ws = app.config["WORKSPACE"]
    ws.save(EVENT, {"schema": SCHEMA, "akce": {"nazev": "Konference"},
                    "skupiny": {}, "soubory": {"P9109996.JPG": {},
                                               "b.jpg": {}}}, None)
    immich.Settings(ws.work).save(URL, KEY)
    return app, fake


def faces_of(app, soubor, akce=EVENT):
    doc, _ = app.config["WORKSPACE"].load(akce)
    return doc["soubory"][soubor].get("obliceje")


# --- nastavení -------------------------------------------------------------

def test_settings_file_private_and_key_not_returned(tmp_path):
    app = create_app(tmp_path, tmp_path / "work", prihlaseni=False)
    c = app.test_client()
    assert c.get("/api/immich").json["nastaveno"] is False
    assert c.get("/api/info").json["immich"] is False
    r = c.put("/api/immich", json={"adresa": URL + "/", "klic": KEY})
    assert r.status_code == 200
    assert r.json["klic"] == "…W4No" and r.json["adresa"] == URL
    assert KEY not in r.get_data(as_text=True)
    assert KEY not in c.get("/api/immich").get_data(as_text=True)
    path = tmp_path / "work" / "immich.json"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text()) == {"adresa": URL, "klic": KEY}
    assert c.get("/api/info").json["immich"] is True


def test_address_change_needs_key(tmp_path):
    app = create_app(tmp_path, tmp_path / "work", prihlaseni=False)
    c = app.test_client()
    assert c.put("/api/immich", json={"adresa": URL}).status_code == 400
    c.put("/api/immich", json={"adresa": URL, "klic": KEY})
    # Stejná adresa bez klíče: klíč zůstane.
    assert c.put("/api/immich", json={"adresa": URL}).status_code == 200
    r = c.put("/api/immich", json={"adresa": "http://jinam:2283"})
    assert r.status_code == 400 and r.json["chyba"] == "klic_povinny"
    assert immich.Settings(tmp_path / "work").load()["adresa"] == URL
    assert c.put("/api/immich", json={"adresa": "ftp://x", "klic": KEY}) \
        .status_code == 400


def test_delete_settings(setup):
    app, _ = setup
    c = app.test_client()
    assert c.delete("/api/immich").json["nastaveno"] is False
    assert c.post("/api/immich/test").status_code == 409


def test_connection_ok(setup):
    app, fake = setup
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    r = app.test_client().post("/api/immich/test")
    assert r.status_code == 200
    assert r.json == {"ok": True, "verze": "3.3.0-rc2", "osob": 1}
    assert any("/api/faces" in url for _, url in fake.calls)


def test_connection_without_face_permission(setup):
    app, fake = setup
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.fail = "/api/faces"
    r = app.test_client().post("/api/immich/test")
    assert r.status_code == 502
    assert r.json["ok"] is False and r.json["chyba"].startswith("obličeje")


# --- přepočet a párování ---------------------------------------------------

def test_area():
    assert immich.area(face("x")) == [0.2725, 0.432, 0.041, 0.0747]


def test_area_other_scale():
    # Stejný obličej ve zmenšenině 1440 × 1920 a v originálu 2736 × 3648.
    small = face("x", (519, 760, 568, 839), (1440, 1920))
    k = 2736 / 1440
    big = face("x", tuple(v * k for v in (519, 760, 568, 839)),
               (2736, 3648))
    assert immich.area(small) == immich.area(big)


def test_file_key_ignores_root():
    assert immich.file_key(f"{ROOT}/{EVENT}/P9109996.JPG") == \
        (EVENT, "P9109996.JPG")


# --- synchronizace ---------------------------------------------------------

def test_new_face_named(setup):
    app, fake = setup
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    status = app.config["IMMICH"].run()
    assert faces_of(app, "P9109996.JPG") == [
        {"jmeno": "Hlava, Miloš", "oblast": [0.2725, 0.432, 0.041, 0.0747]}]
    assert faces_of(app, "b.jpg") is None
    assert status["posledni"]["zmenene"] == [EVENT]
    assert status["posledni_uspesny"]["ok"] is True


def test_unnamed_ignored_and_sorted(setup):
    app, fake = setup
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG",
             face("Tichý, Rudolf", (500, 0, 510, 10)), face(""),
             face(None), face("Hlava, Miloš", (100, 0, 110, 10)))
    app.config["IMMICH"].run()
    assert [f["jmeno"] for f in faces_of(app, "P9109996.JPG")] == \
        ["Hlava, Miloš", "Tichý, Rudolf"]


def test_removed_person(setup):
    app, fake = setup
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    sync = app.config["IMMICH"]
    sync.run()
    fake.faces["a1"] = [face("")]
    sync.run()
    doc, _ = app.config["WORKSPACE"].load(EVENT)
    assert "obliceje" not in doc["soubory"]["P9109996.JPG"]


def test_written_only_on_change(setup):
    app, fake = setup
    ws = app.config["WORKSPACE"]
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    sync = app.config["IMMICH"]
    sync.run()
    mtime = ws.metadata_path(EVENT).stat().st_mtime_ns
    assert sync.run()["posledni"]["zmenene"] == []
    assert ws.metadata_path(EVENT).stat().st_mtime_ns == mtime


def test_known_name_form(setup):
    app, fake = setup
    ws = app.config["WORKSPACE"]
    doc, version = ws.load(EVENT)
    doc["akce"]["ucastnici"] = ["Hlava, Miloš"]
    ws.save(EVENT, doc, version)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Miloš Hlava"),
             face("Rudolf Tichý", (0, 0, 10, 10)))
    app.config["IMMICH"].run()
    assert [f["jmeno"] for f in faces_of(app, "P9109996.JPG")] == \
        ["Hlava, Miloš", "Rudolf Tichý"]


def test_event_without_metadata_untouched(setup):
    app, fake = setup
    fake.add("a1", f"{ROOT}/{OTHER}/c.jpg", face("Hlava, Miloš"))
    app.config["IMMICH"].run()
    ws = app.config["WORKSPACE"]
    assert ws.load(OTHER) == (None, None)
    assert {e["nazev"]: e["stav"] for e in ws.list_events()}[OTHER] == \
        "nezpracovano"


def test_collision_skipped(tmp_path, monkeypatch):
    """Akce se složkou s příponou `.ignored` i bez ní sync nezastaví."""
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    make_tree(archiv, {f"{EVENT}/": {"b.jpg": "x"},
                       f"{EVENT}.ignored/": {"b.jpg": "x"},
                       f"{OTHER}/": {"c.jpg": "x"}})
    fake = FakeImmich()
    app = create_app(archiv, tmp_path / "work", True, immich_fetch=fake,
                     prihlaseni=False)
    ws = app.config["WORKSPACE"]
    ws.save(OTHER, {"schema": SCHEMA, "akce": {}, "skupiny": {},
                    "soubory": {"c.jpg": {}}}, None)
    immich.Settings(ws.work).save(URL, KEY)
    fake.add("a1", f"{ROOT}/{OTHER}/c.jpg", face("Hlava, Miloš"))
    status = app.config["IMMICH"].run()
    assert status["posledni"]["zmenene"] == [OTHER]


def test_locked_event_skipped(setup):
    app, fake = setup
    app.config["LOCKS"].acquire(EVENT, "r1", "Spáčil, David")
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    status = app.config["IMMICH"].run()
    assert faces_of(app, "P9109996.JPG") is None
    assert status["posledni"]["preskocene"] == [EVENT]
    # Zámek uživatele zůstal.
    assert app.config["LOCKS"].holds(EVENT, "r1")


def test_lock_released_after_write(setup):
    app, fake = setup
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    app.config["IMMICH"].run()
    assert app.config["LOCKS"].holder(EVENT) is None


def test_failed_query_writes_nothing(setup):
    app, fake = setup
    ws = app.config["WORKSPACE"]
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    sync = app.config["IMMICH"]
    sync.run()
    ok = sync.status()["posledni_uspesny"]
    before = ws.metadata_path(EVENT).read_bytes()
    # Úspěšný běh by oblast změnil; dotaz na obličeje ale selže.
    fake.faces["a1"] = [face("Hlava, Miloš", (0, 0, 10, 10))]
    fake.fail = "/api/faces"
    status = sync.run()
    assert ws.metadata_path(EVENT).read_bytes() == before
    assert status["posledni"]["ok"] is False
    assert "HTTP 403" in status["posledni"]["chyba"]
    assert status["posledni_uspesny"] == ok


def test_export_stays_current(setup):
    app, fake = setup
    ws = app.config["WORKSPACE"]
    from fotoarchiv import xmp
    xmp.export(ws, EVENT)
    _, version = ws.load(EVENT)
    assert ws.export_version(EVENT) == version
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    app.config["IMMICH"].run()
    _, new_version = ws.load(EVENT)
    assert new_version != version
    assert ws.export_version(EVENT) == new_version
    assert xmp.export(ws, EVENT, nanecisto=True)["zapsano"] == 0


def test_stale_export_not_shifted(setup):
    app, fake = setup
    ws = app.config["WORKSPACE"]
    from fotoarchiv import xmp
    xmp.export(ws, EVENT)
    doc, version = ws.load(EVENT)
    doc["akce"]["popis"] = "změna po exportu"
    ws.save(EVENT, doc, version)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    app.config["IMMICH"].run()
    assert ws.export_version(EVENT) == version


def test_paging(setup):
    app, fake = setup
    for i in range(5):
        fake.add(f"a{i}", f"{ROOT}/{EVENT}/P9109996.JPG",
                 face(f"Osoba{i}, X", (i * 10, 0, i * 10 + 5, 5)))
    client = immich.Client(URL, KEY, fake)
    assert len(client.people(size=2)[0]) == 5
    assert len(client.assets(size=2)) == 5


def test_sync_endpoint(setup, monkeypatch):
    app, _ = setup
    sync = app.config["IMMICH"]
    called = []
    monkeypatch.setattr(sync, "run", lambda: called.append(1))
    r = app.test_client().post("/api/immich/sync")
    assert r.status_code == 200 and r.json["synchronizace"]["bezi"] is True


def test_settings_admin_only(tmp_path):
    from fotoarchiv import auth
    work = tmp_path / "work"
    work.mkdir()
    (work / "uzivatele.json").write_text(json.dumps(
        {"kopacova": {"jmeno": "Kopáčová, Jana"}}))
    auth.Passwords(work).set("kopacova", "tajne-heslo-1")
    app = create_app(tmp_path, work)
    c = app.test_client()
    c.post("/api/prihlaseni",
           json={"login": "kopacova", "heslo": "tajne-heslo-1"})
    assert c.get("/api/ja").status_code == 200
    for method, path in [("put", "/api/immich"), ("get", "/api/immich"),
                         ("delete", "/api/immich"),
                         ("post", "/api/immich/test"),
                         ("post", "/api/immich/sync")]:
        r = getattr(c, method)(path, json={"adresa": URL, "klic": KEY})
        assert r.status_code == 403, path
    assert not (work / "immich.json").exists()
