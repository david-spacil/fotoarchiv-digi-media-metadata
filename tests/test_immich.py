import json
import stat
import time
from urllib.parse import parse_qs, urlsplit

import pytest

from fotoarchiv import albums, immich
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
    """Podvržené API: osoby, assety (id → cesta), obličeje a alba.

    Zapisovací dotazy (POST/PUT/DELETE) zaznamenává do `writes` jako
    (metoda, cesta, tělo). Asset ze `search/metadata` má `type`
    a `thumbhash` (None u id ve `bez_nahledu`); album v odpovědi jako
    v Immichi 3 bez seznamu assetů (členy jen přes `albumIds`),
    `no_admin` blokuje administrátorské knihovny i fronty (403),
    `fail` částí URL simuluje chybu (403) i na albích.
    """

    def __init__(self):
        self.people = []
        self.paths = {}
        self.faces = {}
        self.fail = None        # část URL, na které dotaz selže
        self.calls = []
        self.writes = []        # (metoda, cesta, tělo) zápisových dotazů
        self.permissions = ["all"]
        self.libraries = [{"id": "lib-1", "name": "Archiv"}]
        self.no_admin = False   # GET /api/libraries a fronty odpovědí 403
        self.queues = {}        # název → statistics (default = nuly)
        self.albums = {}        # id → {id, albumName, assetIds}
        self.album_seq = 0
        self.bez_nahledu = set()  # assety bez zmenšeniny (thumbhash None)
        self.typy = {}          # id → type (výchozí IMAGE)

    def add(self, asset_id, path, *faces):
        self.paths[asset_id] = path
        self.faces[asset_id] = list(faces)
        for f in faces:
            p = f["person"]
            if p and p not in self.people:
                self.people.append(p)

    @staticmethod
    def _album(album):
        """`AlbumResponseDto` Immiche 3: bez seznamu assetů."""
        return {"id": album["id"], "albumName": album["albumName"],
                "assetCount": len(album["assetIds"])}

    def thumbnail(self, method, url, klic):
        """Podvržený binární dotaz (`fetch_bytes`) na zmenšeninu."""
        self.calls.append((method, url))
        assert klic == KEY
        return b"nahled-preview", "image/jpeg"

    def __call__(self, method, url, klic, body=None):
        self.calls.append((method, url))
        assert klic == KEY
        if self.fail and self.fail in url:
            raise immich.ImmichError(f"HTTP 403 {url}", status=403)
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        if method != "GET":
            self.writes.append((method, parts.path, body))
        if parts.path == "/api/server/version":
            return {"major": 3, "minor": 3, "patch": 0, "prerelease": 2}
        if parts.path == "/api/api-keys/me":
            return {"permissions": self.permissions}
        if parts.path == "/api/people" and method == "PUT":
            for item in body["people"]:
                for p in self.people:
                    if p["id"] == item["id"]:
                        if "name" in item:
                            p["name"] = item["name"]
                        if "isHidden" in item:
                            p["isHidden"] = item["isHidden"]
            return None
        if parts.path == "/api/people/merge":
            return None
        if parts.path == "/api/people":
            page, size = int(query["page"][0]), int(query["size"][0])
            chunk = self.people[(page - 1) * size:page * size]
            return {"people": chunk, "total": len(self.people),
                    "hasNextPage": page * size < len(self.people)}
        if parts.path == "/api/search/metadata":
            ids = [a for a in sorted(self.paths) if not body.get("personIds")
                   or any((f["person"] or {}).get("id") in body["personIds"]
                          for f in self.faces[a])]
            if body.get("albumIds"):
                members = {i for aid in body["albumIds"] for i in
                           self.albums.get(aid, {}).get("assetIds", [])}
                ids = [a for a in ids if a in members]
            if body.get("originalPath"):
                ids = [a for a in ids
                       if body["originalPath"] in self.paths[a]]
            page, size = body["page"], body["size"]
            chunk = ids[(page - 1) * size:page * size]
            more = page * size < len(ids)
            return {"assets": {
                "items": [{"id": a, "originalPath": self.paths[a],
                           "type": self.typy.get(a, "IMAGE"),
                           "resized": True,   # Immich 3.3: vždy true
                           "thumbhash": None if a in self.bez_nahledu
                           else "hash"} for a in chunk],
                "nextPage": str(page + 1) if more else None}}
        if parts.path == "/api/albums":
            if method == "POST":
                self.album_seq += 1
                album = {"id": f"alb{self.album_seq}",
                         "albumName": body["albumName"],
                         "assetIds": list(body.get("assetIds") or [])}
                self.albums[album["id"]] = album
                return self._album(album)
            return [self._album(a) for a in self.albums.values()]
        if parts.path.startswith("/api/albums/"):
            rest = parts.path.removeprefix("/api/albums/")
            if rest.endswith("/assets"):
                album = self.albums[rest[: -len("/assets")]]
                ids = body["ids"]
                if method == "PUT":
                    album["assetIds"] += [i for i in ids
                                          if i not in album["assetIds"]]
                else:
                    album["assetIds"] = [i for i in album["assetIds"]
                                         if i not in ids]
                return None
            if rest not in self.albums:
                raise immich.ImmichError(f"HTTP 404 {url}", status=404)
            return self._album(self.albums[rest])
        if parts.path == "/api/libraries":
            if self.no_admin:
                raise immich.ImmichError(f"HTTP 403 {url}", status=403)
            return [dict(lib) for lib in self.libraries]
        if (parts.path.startswith("/api/libraries/")
                and parts.path.endswith("/scan")):
            return None                    # prázdná odpověď (204)
        if parts.path.startswith("/api/queues/"):
            if self.no_admin:
                raise immich.ImmichError(f"HTTP 403 {url}", status=403)
            name = parts.path.removeprefix("/api/queues/")
            return {"name": name, "statistics": self.queues.get(
                name, {"active": 0, "waiting": 0, "completed": 0,
                       "failed": 0})}
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
    immich.Settings(ws.work).save(URL, KEY, "lib-1")
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
    assert r.json == {"ok": True, "verze": "3.3.0-rc2", "osob": 1,
                      "varovani": [], "chybi": []}
    assert any("/api/faces" in url for _, url in fake.calls)


def test_connection_all_key_has_no_permission_warning(setup):
    """Klíč s `all`: žádná varování (knihovna vybraná, admin)."""
    app, fake = setup
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    r = app.test_client().post("/api/immich/test")
    assert r.status_code == 200
    assert r.json["chybi"] == [] and r.json["varovani"] == []


def test_connection_read_only_key_warns_but_passes(setup):
    """Klíč jen pro čtení: test projde a vypíše chybějící oprávnění."""
    app, fake = setup
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.permissions = ["person.read", "asset.read", "face.read",
                        "asset.view"]
    r = app.test_client().post("/api/immich/test")
    assert r.status_code == 200 and r.json["ok"] is True
    assert "person.update" in r.json["chybi"]
    assert "album.create" in r.json["chybi"]
    assert "person.read" not in r.json["chybi"]
    assert len(r.json["varovani"]) == 1
    assert "Čtení osob a obličejů funguje" in r.json["varovani"][0]
    assert "pojmenování osob" in r.json["varovani"][0]
    assert "person.update" in r.json["varovani"][0]


def test_connection_without_admin_role_warns(setup):
    """Klíč s `all` ale bez role admin: 403 na knihovnách = varování."""
    app, fake = setup
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.no_admin = True
    r = app.test_client().post("/api/immich/test")
    assert r.status_code == 200 and r.json["ok"] is True
    assert r.json["chybi"] == []
    assert len(r.json["varovani"]) == 1
    assert "bez role admin" in r.json["varovani"][0]
    assert "sken knihovny a stav rozpoznávání" in r.json["varovani"][0]


def test_connection_without_library_warns(setup):
    app, fake = setup
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    ws = app.config["WORKSPACE"]
    immich.Settings(ws.work).save(URL, KEY)   # bez vybrané knihovny
    r = app.test_client().post("/api/immich/test")
    assert r.status_code == 200 and r.json["ok"] is True
    assert len(r.json["varovani"]) == 1
    assert "není vybraná knihovna" in r.json["varovani"][0]


def test_connection_without_face_permission(setup):
    app, fake = setup
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.fail = "/api/faces"
    r = app.test_client().post("/api/immich/test")
    assert r.status_code == 502
    assert r.json["ok"] is False and r.json["chyba"].startswith("obličeje")


# --- klient: zápis, alba, knihovny, zmenšeniny -----------------------------

def test_api_key_permissions(setup):
    _, fake = setup
    fake.permissions = ["asset.read", "face.read"]
    assert immich.Client(URL, KEY, fake).api_key_permissions() == \
        ["asset.read", "face.read"]


def test_update_people_request(setup):
    _, fake = setup
    fake.people = [{"id": "p-1", "name": ""}, {"id": "p-2", "name": "X"}]
    client = immich.Client(URL, KEY, fake)
    client.update_people([{"id": "p-1", "name": "Hlava, Miloš"},
                          {"id": "p-2", "isHidden": True}])
    assert fake.writes == [("PUT", "/api/people", {"people": [
        {"id": "p-1", "name": "Hlava, Miloš"},
        {"id": "p-2", "isHidden": True}]})]
    assert fake.people[0]["name"] == "Hlava, Miloš"
    assert fake.people[1]["isHidden"] is True


def test_merge_people_target_is_first_id(setup):
    _, fake = setup
    immich.Client(URL, KEY, fake).merge_people("p-cil",
                                               ["p-a", "p-cil", "p-b"])
    method, path, body = fake.writes[0]
    assert (method, path) == ("POST", "/api/people/merge")
    assert body == {"ids": ["p-cil", "p-a", "p-b"]}


def test_album_requests(setup):
    _, fake = setup
    client = immich.Client(URL, KEY, fake)
    album = client.create_album(EVENT, ["a1", "a2"])
    client.add_album_assets(album["id"], ["a3"])
    client.remove_album_assets(album["id"], ["a1"])
    albums = client.albums()
    assert [a["id"] for a in albums] == [album["id"]]
    assert albums[0]["albumName"] == EVENT
    assert fake.albums[album["id"]]["assetIds"] == ["a2", "a3"]
    with pytest.raises(immich.ImmichError) as e:
        client.album("neexistujici")
    assert e.value.status == 404
    assert fake.writes[:3] == [
        ("POST", "/api/albums",
         {"albumName": EVENT, "assetIds": ["a1", "a2"]}),
        ("PUT", f"/api/albums/{album['id']}/assets", {"ids": ["a3"]}),
        ("DELETE", f"/api/albums/{album['id']}/assets", {"ids": ["a1"]})]


def test_search_album_paging_and_body(setup):
    _, fake = setup
    for i in range(5):
        fake.add(f"a{i}", f"{ROOT}/{EVENT}/P9109996.JPG",
                 face(f"Osoba{i}, X"))
    client = immich.Client(URL, KEY, fake)
    album = client.create_album(EVENT, [f"a{i}" for i in range(5)])
    fake.writes.clear()
    items = client.search_album(album["id"], size=2)
    assert sorted(i["id"] for i in items) == [f"a{i}" for i in range(5)]
    assert len(fake.writes) == 3          # stránkování po 2
    for _, _, body in fake.writes:
        assert body["albumIds"] == [album["id"]]
        assert body["withPeople"] is True and body["withExif"] is True


def test_search_path_pages_and_filters(setup):
    _, fake = setup
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/2026-09-20 jina akce/x.jpg", face(None))
    client = immich.Client(URL, KEY, fake)
    found = client.search_path(EVENT, size=1)
    assert [i["id"] for i in found] == ["a1"]
    assert fake.writes[0][2]["originalPath"] == EVENT


def test_thumbnail_binary(setup):
    _, fake = setup
    client = immich.Client(URL, KEY, fake, fetch_bytes=fake.thumbnail)
    assert client.thumbnail("a1") == (b"nahled-preview", "image/jpeg")
    assert fake.calls[-1] == ("GET",
                              f"{URL}/api/assets/a1/thumbnail"
                              "?size=preview")


def test_libraries_scan_queue(setup):
    _, fake = setup
    client = immich.Client(URL, KEY, fake)
    assert client.libraries() == [{"id": "lib-1", "name": "Archiv"}]
    assert client.scan_library("lib-1") is None
    assert ("POST", "/api/libraries/lib-1/scan", None) in fake.writes
    assert client.queue("faceDetection")["statistics"]["active"] == 0
    fake.queues["faceDetection"] = {"active": 2, "waiting": 1}
    assert client.queue("faceDetection")["statistics"] == {
        "active": 2, "waiting": 1}


def test_immich_error_status():
    err = immich.ImmichError("HTTP 403", status=403)
    assert err.status == 403
    assert immich.ImmichError("x").status is None


# --- knihovna v nastavení ---------------------------------------------------

def test_settings_knihovna(tmp_path):
    s = immich.Settings(tmp_path / "work")
    s.save(URL, KEY, "lib-1")
    assert s.load() == {"adresa": URL, "klic": KEY, "knihovna": "lib-1"}
    assert json.loads(
        (tmp_path / "work" / "immich.json").read_text())["knihovna"] \
        == "lib-1"
    s.save(URL, KEY)                        # bez knihovny: id tam není
    assert s.load()["knihovna"] is None


def test_knihovna_save_via_api(tmp_path):
    app = create_app(tmp_path, tmp_path / "work", prihlaseni=False)
    c = app.test_client()
    c.put("/api/immich", json={"adresa": URL, "klic": KEY})
    assert c.get("/api/immich").json["knihovna"] is None
    r = c.put("/api/immich", json={"adresa": URL, "knihovna": "lib-1"})
    assert r.status_code == 200 and r.json["knihovna"] == "lib-1"
    assert KEY not in r.get_data(as_text=True)
    # Změna knihovny bez nového klíče: klíč se nemění.
    r = c.put("/api/immich", json={"adresa": URL, "knihovna": "lib-2"})
    assert r.json["knihovna"] == "lib-2"
    assert immich.Settings(tmp_path / "work").load()["klic"] == KEY
    # PUT bez pole knihovna: výběr zůstává.
    assert c.put("/api/immich",
                 json={"adresa": URL}).json["knihovna"] == "lib-2"
    # Změna adresy dál vyžaduje klíč.
    assert c.put("/api/immich", json={"adresa": "http://jine:2283",
                                      "knihovna": "lib-2"}
                 ).status_code == 400


def test_knihovny_endpoint(setup):
    app, fake = setup
    c = app.test_client()
    r = c.get("/api/immich/knihovny")
    assert r.status_code == 200
    assert r.json == {"knihovny": [{"id": "lib-1", "name": "Archiv"}]}
    assert KEY not in r.get_data(as_text=True)
    fake.no_admin = True
    assert c.get("/api/immich/knihovny").status_code == 502


def test_knihovny_endpoint_without_settings(tmp_path):
    app = create_app(tmp_path, tmp_path / "work", prihlaseni=False)
    assert app.test_client().get("/api/immich/knihovny").status_code == 409


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
                         ("post", "/api/immich/sync"),
                         ("get", "/api/immich/knihovny")]:
        r = getattr(c, method)(path, json={"adresa": URL, "klic": KEY})
        assert r.status_code == 403, path
    assert not (work / "immich.json").exists()


# --- stav akcí ve `.work/immich-alba.json` (2.2) ----------------------------

def test_stavy_round_trip(tmp_path):
    work = tmp_path / "work"
    stavy = albums.Stavy(work)
    assert stavy.polozka(EVENT) is None
    polo = stavy.nastav(EVENT, stav="nacitani")
    assert polo["stav"] == "nacitani" and polo["album"] is None
    assert polo["cas"]
    stavy.nastav(EVENT, album="alb1")
    polo = stavy.polozka(EVENT)
    assert polo["album"] == "alb1" and polo["stav"] == "nacitani"
    stavy.nastav(EVENT, stav="rozpoznano", chyba=None)
    polo = stavy.polozka(EVENT)
    assert polo["stav"] == "rozpoznano" and "chyba" not in polo
    stavy.nastav(EVENT, chyba="HTTP 403 /api/queues/faceDetection")
    polo = stavy.polozka(EVENT)
    assert "403" in polo["chyba"] and polo["stav"] == "rozpoznano"
    # nezměněný zápis soubor nepřepíše
    path = work / "immich-alba.json"
    mtime = path.stat().st_mtime_ns
    stavy.nastav(EVENT, chyba="HTTP 403 /api/queues/faceDetection")
    assert path.stat().st_mtime_ns == mtime
    stavy.nastav(EVENT, chyba=None)
    assert "chyba" not in stavy.polozka(EVENT)
    assert json.loads(path.read_text())[EVENT]["album"] == "alb1"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert not list(work.glob(".immich-alba-*"))      # žádný dočasný soubor


def test_stavy_poskozeny_nebo_chybejici_soubor(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    path = work / "immich-alba.json"
    path.write_text("{", encoding="utf-8")
    stavy = albums.Stavy(work)
    assert stavy.nacti() == {} and stavy.polozka(EVENT) is None
    path.write_text("[]", encoding="utf-8")          # ne_dict = prázdné
    assert stavy.nacti() == {}
    stavy.nastav(EVENT, stav="rozpoznavani")         # přepíše poškozené
    assert stavy.polozka(EVENT)["stav"] == "rozpoznavani"
    path.unlink()
    assert albums.Stavy(work).nacti() == {}


def test_stavy_zamek_pod_zatezi(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    stavy = albums.Stavy(tmp_path / "work")

    def zapsat(i):
        stavy.nastav(f"2026-01-01 Akce {i}", stav="rozpoznavani")
        stavy.nastav(f"2026-01-01 Akce {i}", album=f"alb{i}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(zapsat, range(12)))
    data = stavy.nacti()
    assert len(data) == 12
    for jmeno, entry in data.items():
        assert entry["stav"] == "rozpoznavani"
        assert entry["album"] == f"alb{jmeno.split()[-1]}"


def test_stavy_cteni_bez_immiche(setup):
    app, fake = setup
    stavy = albums.Stavy(app.config["WORKSPACE"].work)
    pred = len(fake.calls)
    stavy.nacti()
    stavy.polozka(EVENT)
    assert len(fake.calls) == pred


# --- údržba alb synchronizací (2.3) -----------------------------------------

def dokoncit(app, akce=EVENT):
    ws = app.config["WORKSPACE"]
    doc, version = ws.load(akce)
    doc["dokonceno"] = "2026-10-01"
    ws.save(akce, doc, version)


def stavy_of(app):
    return app.config["IMMICH"].alba


def test_sync_nedokoncena_akce_album_nedostane(setup):
    app, fake = setup
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    app.config["IMMICH"].run()
    assert fake.albums == {}
    assert stavy_of(app).polozka(EVENT) is None


def test_sync_vytvori_album_a_stav_rozpoznano(setup):
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    app.config["IMMICH"].run()
    album = list(fake.albums.values())
    assert len(album) == 1
    assert album[0]["albumName"] == EVENT
    assert sorted(album[0]["assetIds"]) == ["a1", "a2"]
    polo = stavy_of(app).polozka(EVENT)
    assert polo["album"] == album[0]["id"]
    assert polo["stav"] == "rozpoznano" and polo["cas"]
    assert "chyba" not in polo


def test_sync_immich_fotky_nezna(setup):
    app, fake = setup
    dokoncit(app)
    status = app.config["IMMICH"].run()
    assert status["posledni"]["ok"] is True
    assert fake.albums == {}
    assert stavy_of(app).polozka(EVENT) is None


def test_sync_doplni_chybejici_a_odebere_cizi(setup):
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    fake.add("a9", f"{ROOT}/2026-09-20 jina akce/x.jpg", face(None))
    fake.albums["albx"] = {"id": "albx", "albumName": EVENT,
                           "assetIds": ["a9"]}
    app.config["IMMICH"].run()
    assert fake.albums["albx"]["assetIds"] == ["a1", "a2"]
    assert stavy_of(app).polozka(EVENT)["album"] == "albx"
    # maže se jen odebrání assetů z alba, nikdy album nebo asset
    for method, path, _ in fake.writes:
        if method == "DELETE":
            assert path.startswith("/api/albums/") and \
                path.endswith("/assets"), path


def test_sync_album_smazane_v_immichi(setup):
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    sync = app.config["IMMICH"]
    sync.run()
    del fake.albums[stavy_of(app).polozka(EVENT)["album"]]
    sync.run()
    assert len(fake.albums) == 1
    polo = stavy_of(app).polozka(EVENT)
    assert polo["album"] in fake.albums
    assert sorted(next(iter(fake.albums.values()))["assetIds"]) == \
        ["a1", "a2"]


def test_sync_ztratena_vazba_dohleda_podle_nazvu(setup):
    """Po ztrátě `.work/immich-alba.json` nesmí vzniknout duplicitní
    album."""
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    app.config["IMMICH"].run()
    stavy_of(app).path.unlink()
    app.config["IMMICH"].run()
    assert len(fake.albums) == 1
    assert stavy_of(app).polozka(EVENT)["album"] in fake.albums


def test_sync_nova_instace_drovna_po_restartu(setup):
    """Nová instance Sync (restart serveru, paměť pryč) album dorovná."""
    app, fake = setup
    ws = app.config["WORKSPACE"]
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    fake.albums["albX"] = {"id": "albX", "albumName": EVENT,
                           "assetIds": ["a1"]}
    stavy_of(app).nastav(EVENT, album="albSmazany", stav="nacitani")
    druha = immich.Sync(ws, app.config["LOCKS"],
                        immich.Settings(ws.work), lambda: set(),
                        fetch=fake)
    druha.run()
    assert fake.albums["albX"]["assetIds"] == ["a1", "a2"]
    polo = stavy_of(app).polozka(EVENT)
    assert polo["album"] == "albX" and polo["stav"] == "rozpoznano"


def test_sync_cizi_akce_se_stejnym_podretezcem(setup):
    """`originalPath` filtr je podřetězec — `file_key` musí oddělit
    `… Konference` od `… Konference 2`."""
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("ax", f"{ROOT}/{EVENT} 2/cizak.jpg", face("Cizi, Osoba"))
    app.config["IMMICH"].run()
    album = next(iter(fake.albums.values()))
    assert album["assetIds"] == ["a1"]


def test_sync_vyradene_soubory_nejsou_v_albu(setup):
    app, fake = setup
    dokoncit(app)
    ws = app.config["WORKSPACE"]
    doc, version = ws.load(EVENT)
    doc["soubory"]["b.jpg"]["vyradit"] = True
    ws.save(EVENT, doc, version)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    app.config["IMMICH"].run()
    assert next(iter(fake.albums.values()))["assetIds"] == ["a1"]


def test_sync_klic_bez_prav_k_album_obliceje_projdou(setup):
    """Scénář Klíč bez oprávnění k albům: zápis obličejů proběhne,
    album ne, chyba se zapíše a stav nevznikne."""
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    fake.fail = "/api/albums"                  # 403 na alba
    status = app.config["IMMICH"].run()
    assert status["posledni"]["ok"] is True
    assert status["posledni"]["zmenene"] == [EVENT]
    assert faces_of(app, "P9109996.JPG") is not None
    assert fake.albums == {}
    polo = stavy_of(app).polozka(EVENT)
    assert polo["chyba"] and "403" in polo["chyba"]
    assert polo.get("stav") is None


def test_sync_fronta_neprazdna_rozpoznavani(setup):
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    fake.queues["facialRecognition"] = {"active": 0, "waiting": 3}
    app.config["IMMICH"].run()
    assert stavy_of(app).polozka(EVENT)["stav"] == "rozpoznavani"


def test_sync_asset_bez_zmenseniny_rozpoznavani(setup):
    """Fotka bez `thumbhash` = zmenšenina ještě není; `resized` je
    v Immichi 3.3 vždy true, a proto se nepoužívá."""
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    fake.bez_nahledu = {"a2"}
    app.config["IMMICH"].run()
    assert stavy_of(app).polozka(EVENT)["stav"] == "rozpoznavani"


def test_sync_video_bez_zmenseniny_neblokuje(setup):
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    fake.typy["a2"] = "VIDEO"
    fake.bez_nahledu = {"a2"}
    app.config["IMMICH"].run()
    assert stavy_of(app).polozka(EVENT)["stav"] == "rozpoznano"


def test_sync_rozpoznano_necha_pri_cizi_praci_ve_fronte(setup):
    """Fronty jsou společné: cizí úlohy už rozpoznanou akci nevrátí."""
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    sync = app.config["IMMICH"]
    sync.run()
    assert sync.alba.polozka(EVENT)["stav"] == "rozpoznano"
    fake.queues["faceDetection"] = {"active": 2, "waiting": 40}
    sync.run()
    assert sync.alba.polozka(EVENT)["stav"] == "rozpoznano"


def test_sync_odebere_cizi_asset_z_existujiciho_alba(setup):
    """Členy alba se čtou přes `albumIds` (odpověď alba je nemá)."""
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a9", f"{ROOT}/2026-09-20 jina akce/x.jpg", face(None))
    fake.albums["albY"] = {"id": "albY", "albumName": EVENT,
                           "assetIds": ["a1", "a9"]}
    app.config["IMMICH"].run()
    assert fake.albums["albY"]["assetIds"] == ["a1"]
    assert not [w for w in fake.writes
                if w[1] == "/api/albums/albY/assets" and w[0] == "PUT"]


def test_sync_fronta_403_stav_rozpoznavani_a_chyba(setup):
    """Klíč bez role admin: album je udrženo, rozpoznání nelze ověřit
    → `rozpoznavani` s chybou."""
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    fake.no_admin = True
    app.config["IMMICH"].run()
    assert len(fake.albums) == 1
    polo = stavy_of(app).polozka(EVENT)
    assert polo["stav"] == "rozpoznavani"
    assert "403" in polo["chyba"]


def test_sync_chyba_fronty_stav_nemini(setup):
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    sync = app.config["IMMICH"]
    sync.run()
    assert sync.alba.polozka(EVENT)["stav"] == "rozpoznano"
    fake.fail = "/api/queues"
    # nový asset alba vynutí nové ověření front
    fake.add("a3", f"{ROOT}/{EVENT}/c.jpg", face("Hlava, Miloš"))
    (app.config["WORKSPACE"].event_dir(EVENT) / "c.jpg").write_bytes(b"x")
    sync.run()
    polo = sync.alba.polozka(EVENT)
    assert polo["stav"] == "rozpoznano" and "403" in polo["chyba"]


def test_udrzet_album_chyba_hledani_stav_nemini(setup):
    """Chyba `search` v `udrzet_album`: stav ani vazba se nezmění,
    jen se zapíše chyba."""
    app, fake = setup
    dokoncit(app)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    sync = app.config["IMMICH"]
    sync.run()
    album_id = sync.alba.polozka(EVENT)["album"]
    fake.fail = "/api/search"
    assert albums.udrzet_album(sync.client(), app.config["WORKSPACE"],
                               sync.alba, EVENT) is None
    polo = sync.alba.polozka(EVENT)
    assert polo["stav"] == "rozpoznano" and polo["album"] == album_id
    assert polo["chyba"]


# --- hlídač po dokončení (2.4) ----------------------------------------------

def hlidaci_setup(tmp_path, monkeypatch, zapis=False, interval=0.05,
                  limit=1.0):
    """Aplikace se zkráceným hlídačem (zkratka konstant HLIDAC_*)."""
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    make_tree(archiv, {f"{EVENT}/": {"P9109996.JPG": "x", "b.jpg": "x"},
                       f"{OTHER}/": {"c.jpg": "x"}})
    monkeypatch.setattr("fotoarchiv.scan.run_exiftool", lambda d, n: {})
    fake = FakeImmich()
    app = create_app(archiv, tmp_path / "work", zapis, immich_fetch=fake,
                     prihlaseni=False, immich_hlidac_interval=interval,
                     immich_hlidac_limit=limit)
    ws = app.config["WORKSPACE"]
    ws.save(EVENT, {"schema": SCHEMA, "akce": {"nazev": "Konference"},
                    "skupiny": {}, "soubory": {"P9109996.JPG": {},
                                               "b.jpg": {}}}, None)
    immich.Settings(ws.work).save(URL, KEY, "lib-1")
    return app, fake


def otestuj_dokonceni(app):
    """Požádá server o dokončení akce; vrátí (odpověď, čas odpovědi)."""
    app.config["LOCKS"].acquire(EVENT, "r1", "Novák, Jan")
    _, version = app.config["WORKSPACE"].load(EVENT)
    start = time.monotonic()
    r = app.test_client().post(
        f"/api/akce/{EVENT}/dokoncit",
        json={"relace": "r1", "version": version})
    return r, time.monotonic() - start


def test_dokonceni_vytvori_album_a_spusti_sync(tmp_path, monkeypatch):
    """Scénář Dokončení akce (produkce): sken, album, rozpoznání,
    `Sync.trigger()` — vše na pozadí."""
    app, fake = hlidaci_setup(tmp_path, monkeypatch, zapis=True)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    volani = []
    monkeypatch.setattr(app.config["IMMICH"], "trigger",
                        lambda: volani.append(1))
    r, cas = otestuj_dokonceni(app)
    assert r.status_code == 200 and r.json["dokonceno"]
    assert cas < 2                        # na Immich se nečekalo
    hlidac = app.config["IMMICH_HLIDAC"]
    assert hlidac.cekat(5)
    album = next(iter(fake.albums.values()))
    assert album["albumName"] == EVENT
    assert sorted(album["assetIds"]) == ["a1", "a2"]
    assert app.config["IMMICH"].alba.polozka(EVENT)["stav"] == "rozpoznano"
    assert volani == [1]
    scan_i = next(i for i, w in enumerate(fake.writes)
                  if w[1] == "/api/libraries/lib-1/scan")
    album_i = next(i for i, w in enumerate(fake.writes)
                   if w[1] == "/api/albums" and w[0] == "POST")
    assert scan_i < album_i               # nejdřív sken, pak album


def test_dokonceni_neceka_na_immich(tmp_path, monkeypatch):
    """Nedostupný Immich: dokončení proběhne jako dosud a rychle,
    alba se chopí až pozdější synchronizace."""
    app, fake = hlidaci_setup(tmp_path, monkeypatch)
    fake.fail = "/api"
    r, cas = otestuj_dokonceni(app)
    assert r.status_code == 200 and r.json["dokonceno"]
    assert r.json["chyby"] == []
    assert cas < 2
    hlidac = app.config["IMMICH_HLIDAC"]
    assert hlidac.cekat(5)                # hlídač doběhl s chybami
    assert fake.albums == {}
    polo = app.config["IMMICH"].alba.polozka(EVENT)
    assert polo["chyba"] and "403" in polo["chyba"]
    assert polo.get("stav") is None       # nic jsme nezjistili


def test_dokonceni_vyvojovy_rezim(tmp_path, monkeypatch):
    """Scénář Vývojový režim: bez skenu, album vznikne, když Immich
    fotky zná."""
    app, fake = hlidaci_setup(tmp_path, monkeypatch)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    r, _ = otestuj_dokonceni(app)
    assert r.status_code == 200
    hlidac = app.config["IMMICH_HLIDAC"]
    assert hlidac.cekat(5)
    assert sorted(next(iter(fake.albums.values()))["assetIds"]) == \
        ["a1", "a2"]
    assert not any(w[1] == "/api/libraries/lib-1/scan"
                   for w in fake.writes)


def test_hlidac_immich_nenasel_nenalezeno(tmp_path, monkeypatch):
    """Scénář Immich fotky nenašel: po vypršení hlídání bez jediného
    assetu je stav `nenalezeno`."""
    app, fake = hlidaci_setup(tmp_path, monkeypatch)
    hlidac = app.config["IMMICH_HLIDAC"]
    assert hlidac.spust(EVENT) is True
    assert hlidac.cekat(5)
    assert fake.albums == {}
    assert app.config["IMMICH"].alba.polozka(EVENT)["stav"] == "nenalezeno"


def test_hlidac_druha_podminka_hotovo_podle_fronty(tmp_path, monkeypatch):
    """Immich nikdy nenaimportuje jeden soubor: fronta `library` stojí
    a počet nalezených se nezměnil → album i tak vznikne."""
    app, fake = hlidaci_setup(tmp_path, monkeypatch)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    hlidac = app.config["IMMICH_HLIDAC"]
    hlidac.spust(EVENT)
    assert hlidac.cekat(5)
    assert next(iter(fake.albums.values()))["assetIds"] == ["a1"]
    assert app.config["IMMICH"].alba.polozka(EVENT)["stav"] == "rozpoznano"


def test_hlidac_opakovany_start_pusti_znovu(tmp_path, monkeypatch):
    """Nejvýš jeden hlídač na akci; opakované spuštění nesmí zdvojit
    album."""
    app, fake = hlidaci_setup(tmp_path, monkeypatch)
    fake.add("a1", f"{ROOT}/{EVENT}/P9109996.JPG", face("Hlava, Miloš"))
    fake.add("a2", f"{ROOT}/{EVENT}/b.jpg", face("Hlava, Miloš"))
    hlidac = app.config["IMMICH_HLIDAC"]
    assert hlidac.spust(EVENT) and hlidac.spust(EVENT)
    assert hlidac.cekat(5)
    assert len(fake.albums) == 1
    assert sorted(next(iter(fake.albums.values()))["assetIds"]) == \
        ["a1", "a2"]


def test_hlidac_bez_nastaveneho_immiche(tmp_path):
    app = create_app(tmp_path, tmp_path / "work", prihlaseni=False)
    assert app.config["IMMICH_HLIDAC"].spust(EVENT) is False


def test_hlidac_vychozi_konstanty():
    """Výchozí konstanty `HLIDAC_INTERVAL`/`HLIDAC_LIMIT` (immich.py)."""
    hlidac = albums.Hlidac(sync=None)
    assert hlidac.interval == immich.HLIDAC_INTERVAL == 20
    assert hlidac.limit == immich.HLIDAC_LIMIT == 3600


# --- stav akce na kartě a ploše (2.5) ---------------------------------------

def test_api_stav_cte_jenze_soubor(setup):
    """`GET /api/akce/<nazev>/immich`: stav ze `.work/`, žádné volání
    Immiche; `chyba` a id alba se nevrací."""
    app, fake = setup
    sync = app.config["IMMICH"]
    sync.alba.nastav(EVENT, stav="rozpoznavani", album="alb-1",
                     chyba="HTTP 403 fronty")
    r = app.test_client().get(f"/api/akce/{EVENT}/immich")
    assert r.status_code == 200
    assert r.json["nastaveno"] is True and r.json["stav"] == "rozpoznavani"
    assert r.json["album"] is True and r.json["cas"]
    text = r.get_data(as_text=True)
    assert "chyba" not in text and "alb-1" not in text and KEY not in text
    assert fake.calls == []                  # Immiche se neptá


def test_api_stav_404_a_bez_nastaveni(setup):
    """Neexistující akce = 404; bez nastaveného Immiche se stav
    neuvádí ani ve výpisu."""
    app, _ = setup
    sync = app.config["IMMICH"]
    sync.alba.nastav(EVENT, stav="rozpoznavani")
    assert app.test_client().get("/api/akce/2099-01-01 Nic/immich") \
        .status_code == 404
    sync.settings.delete()
    r = app.test_client().get(f"/api/akce/{EVENT}/immich")
    assert r.json == {"nastaveno": False, "stav": None, "cas": None,
                      "album": False}
    events = {e["nazev"]: e
              for e in app.test_client().get("/api/akce").json}
    assert "immich" not in events[EVENT]


def test_vypis_akci_leze_stav_bez_dotazu(setup):
    """Výpis akcí dostane `immich` jen u akcí se záznamem; bez `chyby`,
    bez id alba, bez dotazu na Immich."""
    app, fake = setup
    alba = app.config["IMMICH"].alba
    alba.nastav(EVENT, stav="rozpoznano", album="alb-1",
                chyba="HTTP 403 front")
    r = app.test_client().get("/api/akce")
    events = {e["nazev"]: e for e in r.json}
    assert events[EVENT]["immich"] == {
        "stav": "rozpoznano", "cas": events[EVENT]["immich"]["cas"],
        "album": True}
    assert "immich" not in events[OTHER]
    text = r.get_data(as_text=True)
    assert "chyba" not in text and "alb-1" not in text
    assert fake.calls == []


def test_alba_chyby_jen_na_nastaveni(setup):
    """Chyby alba se vrácí jen v odpovědi `GET /api/immich` (admin)."""
    app, _ = setup
    alba = app.config["IMMICH"].alba
    alba.nastav(EVENT, chyba="HTTP 403 /api/queues")
    alba.nastav(OTHER, stav="nacitani")
    r = app.test_client().get("/api/immich")
    assert r.json["alba_chyby"] == [{"akce": EVENT,
                                     "chyba": "HTTP 403 /api/queues"}]


def prihlaseni_setup(tmp_path, monkeypatch):
    """Přihlášená aplikace: admin `spacil` a `kopacova` bez role;
    Immich nastavený, u akce stav `rozpoznavani`."""
    from fotoarchiv import auth
    work = tmp_path / "work"
    work.mkdir()
    (work / "uzivatele.json").write_text(json.dumps(
        {"spacil": {"jmeno": "Spáčil, David", "role": "admin"},
         "kopacova": {"jmeno": "Kopáčová, Jana"}}), encoding="utf-8")
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    make_tree(archiv, {f"{EVENT}/": {"P9109996.JPG": "x"}})
    monkeypatch.setattr("fotoarchiv.scan.run_exiftool", lambda d, n: {})
    fake = FakeImmich()
    app = create_app(archiv, work, immich_fetch=fake)
    app.testing = True
    for login in ("spacil", "kopacova"):
        auth.Passwords(work).set(login, "tajne-heslo-1")
    immich.Settings(work).save(URL, KEY, "lib-1")
    app.config["IMMICH"].alba.nastav(EVENT, stav="rozpoznavani",
                                     album="alb-1")
    return app


def prihlasen(app, login):
    c = app.test_client()
    r = c.post("/api/prihlaseni",
               json={"login": login, "heslo": "tajne-heslo-1"})
    assert r.status_code == 200, r.json
    return c


def test_bezny_uzivatel_vidi_stav(tmp_path, monkeypatch):
    """Scénář Běžný uživatel: stav vidí i bez role; nastavení zůstává
    jen pro admina."""
    app = prihlaseni_setup(tmp_path, monkeypatch)
    c = prihlasen(app, "kopacova")
    r = c.get(f"/api/akce/{EVENT}/immich")
    assert r.status_code == 200
    assert r.json["stav"] == "rozpoznavani" and r.json["album"] is True
    events = {e["nazev"]: e for e in c.get("/api/akce").json}
    assert events[EVENT]["immich"]["stav"] == "rozpoznavani"
    assert c.get("/api/immich").status_code == 403
    admin = prihlasen(app, "spacil")
    assert admin.get(f"/api/akce/{EVENT}/immich").status_code == 200
    assert "alba_chyby" in admin.get("/api/immich").json
