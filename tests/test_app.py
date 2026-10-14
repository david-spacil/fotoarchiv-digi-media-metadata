import io
import os
import json

import pytest
from PIL import Image

from fotoarchiv.__main__ import main
from fotoarchiv.app import create_app
from fotoarchiv.lock import Locks
from .conftest import make_tree, snapshot

EVENT = "2026-04-28 kontrola"
R1 = {"relace": "r1", "jmeno": "Spáčil, David"}
R2 = {"relace": "r2", "jmeno": "Kopáčová, Jana"}


def make_client(tmp_path, monkeypatch, zapis=False, locks=None):
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    make_tree(archiv, {f"{EVENT}/": {"IMG-20260428-WA0001.jpg": "x",
                                     "v.mp4": "0123456789",
                                     "a.rw2": "raw",
                                     "pozn.txt": "x",
                                     "RAW/": {"a.rw2": ""}}})
    Image.new("RGB", (2000, 1000)).save(archiv / EVENT / "foto.jpg")
    monkeypatch.setattr("fotoarchiv.scan.run_exiftool",
                        lambda d, n: {})
    app = create_app(archiv, tmp_path / "work", zapis, locks,
                     prihlaseni=False)
    app.testing = True
    return app.test_client(), archiv


@pytest.fixture
def client(tmp_path, monkeypatch):
    return make_client(tmp_path, monkeypatch)


@pytest.fixture
def prod(tmp_path, monkeypatch):
    return make_client(tmp_path, monkeypatch, zapis=True)


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
    assert c.post(f"/api/akce/{EVENT}/zamek", json=R1).status_code == 200
    r = c.put(f"/api/akce/{EVENT}/metadata",
              json={"metadata": doc, "version": None, "relace": "r1"})
    assert r.status_code == 200
    assert c.get("/api/akce").json[0]["stav"] == "rozpracovano"
    r = c.put(f"/api/akce/{EVENT}/metadata",
              json={"metadata": doc, "version": None, "relace": "r1"})
    assert r.status_code == 409
    assert snapshot(archiv) == before


def test_save_drops_people_and_keeps_stored_faces(tmp_path, client):
    c, _ = client
    doc = c.get(f"/api/akce/{EVENT}").json["metadata"]
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    version = c.put(f"/api/akce/{EVENT}/metadata", json={
        "metadata": doc, "version": None, "relace": "r1"}).json["version"]
    # Obličeje zapsala synchronizace; klient je nemá a posílá starší osoby.
    face = {"jmeno": "Hlava, Miloš", "oblast": [0.5, 0.4, 0.08, 0.06]}
    path = tmp_path / "work" / "metadata" / EVENT / "_metadata.json"
    stored = json.loads(path.read_text())
    stored["soubory"]["foto.jpg"]["obliceje"] = [face]
    path.write_text(json.dumps(stored))
    version = c.get(f"/api/akce/{EVENT}").json["version"]
    doc["akce"]["osoby"] = ["A, B"]
    doc["soubory"]["foto.jpg"]["osoby"] = ["A, B"]
    doc["soubory"]["v.mp4"]["obliceje"] = [face]
    r = c.put(f"/api/akce/{EVENT}/metadata", json={
        "metadata": doc, "version": version, "relace": "r1"})
    assert r.status_code == 200
    saved = json.loads(path.read_text())
    assert "osoby" not in saved["akce"]
    assert saved["soubory"]["foto.jpg"] == dict(
        stored["soubory"]["foto.jpg"], obliceje=[face])
    assert "obliceje" not in saved["soubory"]["v.mp4"]


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


def test_thumb_sizes(client):
    c, archiv = client
    before = snapshot(archiv)
    url = f"/api/akce/{EVENT}/nahled/foto.jpg"
    for query, size in (("", 320), ("?velikost=1600", 1600)):
        r = c.get(url + query)
        assert r.status_code == 200
        assert Image.open(io.BytesIO(r.data)).size[0] == size
    for bad in ("800", "abc"):
        assert c.get(f"{url}?velikost={bad}").status_code == 400
    assert snapshot(archiv) == before


def test_cleanup_sample_thumb(client):
    c, archiv = client
    Image.new("RGB", (100, 50)).save(archiv / EVENT / "RAW" / "f.jpg")
    before = snapshot(archiv)
    plan = c.post(f"/api/akce/{EVENT}/uklid", json={}).json
    assert plan["podslozky"][0]["ukazky"] == ["f.jpg"]
    url = f"/api/akce/{EVENT}/uklid/nahled"
    assert c.get(f"{url}/RAW/f.jpg").status_code == 200
    assert c.get(f"{url}/RAW/f.jpg?velikost=1600").status_code == 200
    assert c.get(f"{url}/RAW/f.jpg?velikost=800").status_code == 400
    for path in ("RAW/a.rw2", "RAW/neni.jpg", "foto.jpg", "neni/f.jpg",
                 "..%2F..%2Fx/f.jpg", ".%2E/foto.jpg", "RAW/..%2Ffoto.jpg"):
        assert c.get(f"{url}/{path}").status_code == 404, path
    assert snapshot(archiv) == before


def test_original_range(client):
    c, archiv = client
    before = snapshot(archiv)
    url = f"/api/akce/{EVENT}/soubor/v.mp4"
    assert c.get(url).data == b"0123456789"
    r = c.get(url, headers={"Range": "bytes=3-5"})
    assert r.status_code == 206 and r.data == b"345"
    assert c.get(f"/api/akce/{EVENT}/soubor/foto.jpg").status_code == 200
    for name in ("RAW/a.rw2", "RAW%2Fa.rw2", "a.rw2", "pozn.txt", "neni.jpg",
                 "..%2F..%2Fx.jpg"):
        assert c.get(f"/api/akce/{EVENT}/soubor/{name}").status_code == 404
    assert snapshot(archiv) == before


def test_lock_api(client):
    c, _ = client
    url = f"/api/akce/{EVENT}/zamek"
    r = c.post(url, json=R1)
    assert r.status_code == 200 and r.json["zamek"]["jmeno"] == R1["jmeno"]
    r = c.post(url, json=R2)
    assert r.status_code == 409
    assert r.json["drzitel"]["jmeno"] == "Spáčil, David"
    assert c.get(f"/api/akce/{EVENT}").json["zamek"]["jmeno"] == R1["jmeno"]
    assert c.put(url, json={"relace": "r1"}).status_code == 200
    assert c.put(url, json={"relace": "r2"}).status_code == 409
    c.delete(url, json={"relace": "r2"})
    assert c.post(url, json=R2).status_code == 409
    c.delete(url, json={"relace": "r1"})
    assert c.post(url, json=R2).status_code == 200
    # Beacon posílá text/plain.
    r = c.post(url + "/uvolnit", data=json.dumps({"relace": "r2"}),
               content_type="text/plain")
    assert r.status_code == 200
    assert c.get(f"/api/akce/{EVENT}").json["zamek"] is None
    assert c.post(url, json={"relace": "r1"}).status_code == 400
    assert c.post("/api/akce/2026-01-01 neni/zamek", json=R1).status_code \
        == 404


def test_lost_lock(tmp_path, monkeypatch):
    clock = [0.0]
    c, _ = make_client(tmp_path, monkeypatch,
                       locks=Locks(clock=lambda: clock[0]))
    url = f"/api/akce/{EVENT}/zamek"
    c.post(url, json=R1)
    clock[0] += 301
    assert c.post(url, json=R2).status_code == 200
    r = c.put(url, json={"relace": "r1"})
    assert r.status_code == 409 and r.json["drzitel"]["jmeno"] == R2["jmeno"]


def test_save_requires_lock(client):
    c, archiv = client
    doc = c.get(f"/api/akce/{EVENT}").json["metadata"]
    url = f"/api/akce/{EVENT}/metadata"
    body = {"metadata": doc, "version": None}
    assert c.put(url, json=body).status_code == 423
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    r = c.put(url, json=dict(body, relace="r2"))
    assert r.status_code == 423
    assert r.json["drzitel"]["jmeno"] == R1["jmeno"]
    assert c.get("/api/akce").json[0]["stav"] == "nezpracovano"
    assert c.put(url, json=dict(body, relace="r1")).status_code == 200


def test_prod_saves_into_archive(prod):
    c, archiv = prod
    assert c.get("/api/info").json["zapis"] is True
    doc = c.get(f"/api/akce/{EVENT}").json["metadata"]
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    r = c.put(f"/api/akce/{EVENT}/metadata",
              json={"metadata": doc, "version": None, "relace": "r1"})
    assert r.status_code == 200
    stored = json.loads((archiv / EVENT / "_metadata.json").read_text())
    assert list(stored.pop("upravili")) == ["Spáčil, David"]
    assert stored == doc
    d = c.get(f"/api/akce/{EVENT}").json
    assert not d["novy"]
    # Fixture: RAW/, a.rw2 a pozn.txt; _metadata.json se nehlásí.
    assert d["kontrola"] == [
        {"druh": "nepodporovany", "nazev": "pozn.txt"},
        {"druh": "raw", "nazev": "a.rw2"},
        {"druh": "podslozka", "nazev": "RAW"}]


def test_detail_consistency(client):
    c, archiv = client
    (archiv / EVENT / "x.jpg.xmp").write_text("")
    d = c.get(f"/api/akce/{EVENT}").json
    # Nová akce: záznamy z návrhu se nepočítají jako chybějící.
    assert d["novy"]
    assert {"druh": "sirotek_xmp", "nazev": "x.jpg.xmp"} in d["kontrola"]
    assert not any(n["druh"] == "chybejici" for n in d["kontrola"])
    doc, _ = saved(c)
    (archiv / EVENT / "foto.jpg").unlink()
    d = c.get(f"/api/akce/{EVENT}").json
    assert {"druh": "chybejici", "nazev": "foto.jpg"} in d["kontrola"]


def test_cleanup_execute_dev_refused(client):
    c, archiv = client
    before = snapshot(archiv)
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    r = c.post(f"/api/akce/{EVENT}/uklid/provest",
               json={"relace": "r1", "volby": {"RAW": "ponechat"}})
    assert r.status_code == 403
    assert snapshot(archiv) == before


def test_cleanup_execute_prod(prod):
    c, archiv = prod
    url = f"/api/akce/{EVENT}/uklid/provest"
    body = {"volby": {"RAW": "ponechat"}, "raw_v_koreni": True}
    assert c.post(url, json=dict(body, relace="r1")).status_code == 423
    assert (archiv / EVENT / "RAW").is_dir()
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    r = c.post(url, json=dict(body, relace="r1"))
    assert r.status_code == 200
    assert [(o["z"], o["stav"]) for o in r.json["operace"]] == [
        ("RAW", "hotovo"), ("a.rw2", "blokovano"), ("pozn.txt", "hotovo")]
    assert (archiv / EVENT / "RAW.ignored" / "a.rw2").exists()
    assert (archiv / EVENT / "a.rw2").read_text() == "raw"
    assert (archiv / EVENT / "ostatni.ignored" / "pozn.txt").is_file()


def test_info_version_fixed_at_start(tmp_path, monkeypatch):
    versions = iter(["v0.2.0-1-g5609826", "v0.3.0"])
    monkeypatch.setattr("fotoarchiv.version.app_version",
                        lambda: next(versions))
    c, _ = make_client(tmp_path, monkeypatch)
    assert c.get("/api/info").json["verze"] == "v0.2.0-1-g5609826"
    assert c.get("/api/info").json["verze"] == "v0.2.0-1-g5609826"


def test_info_version_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr("fotoarchiv.version.app_version", lambda: None)
    c, _ = make_client(tmp_path, monkeypatch)
    assert c.get("/api/info").json["verze"] is None


def test_geocoding_disabled_without_contact(client):
    c, _ = client
    assert c.get("/api/info").json["geokodovani"] is False
    r = c.get("/api/geokodovani?q=Holštejn")
    assert r.status_code == 503
    assert r.json["chyba"] == "geokodovani_vypnuto"


def test_geocoding_endpoint(tmp_path, monkeypatch):
    from fotoarchiv import geocode
    calls = []

    def fetch(query, user_agent):
        calls.append((query, user_agent))
        if query == "nedostupne":
            raise geocode.GeocodeError("timeout")
        return [{"name": "Holštejn", "lat": "49.4063", "lon": "16.7777",
                 "display_name": "Holštejn, okres Blansko",
                 "osm_type": "relation", "osm_id": 1}]

    monkeypatch.setattr("fotoarchiv.geocode.fetch_nominatim", fetch)
    monkeypatch.setattr("fotoarchiv.geocode.INTERVAL", 0)
    monkeypatch.setattr("fotoarchiv.scan.run_exiftool", lambda d, n: {})
    (tmp_path / "archiv").mkdir()
    geocode.Contact(tmp_path / "work").save("test@example.org")
    app = create_app(tmp_path / "archiv", tmp_path / "work",
                     prihlaseni=False)
    c = app.test_client()
    assert c.get("/api/info").json["geokodovani"] is True
    assert c.get("/api/geokodovani?q=").status_code == 400
    r = c.get("/api/geokodovani?q=Holštejn")
    assert r.status_code == 200 and r.json["z_cache"] is False
    assert r.json["kandidati"][0]["gps"] == [49.4063, 16.7777]
    assert c.get("/api/geokodovani?q=holštejn").json["z_cache"] is True
    assert calls == [("holštejn",
                      "fotoarchiv-digi-media-metadata (test@example.org)")]
    r = c.get("/api/geokodovani?q=nedostupne")
    assert r.status_code == 502 and r.json["chyba"] == "sluzba_nedostupna"
    assert (tmp_path / "work" / "cache" / "geokodovani.json").exists()


def saved(c):
    """Uloží nový dokument akce pod zámkem r1; vrátí (dokument, verze)."""
    doc = c.get(f"/api/akce/{EVENT}").json["metadata"]
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    r = c.put(f"/api/akce/{EVENT}/metadata",
              json={"metadata": doc, "version": None, "relace": "r1"})
    return doc, r.json["version"]


def test_finish_dev_mode(client, tmp_path):
    """Dokončení ve vývojovém režimu píše jen do `.work`."""
    c, archiv = client
    before = snapshot(archiv)
    _, version = saved(c)
    d = c.get(f"/api/akce/{EVENT}").json["export"]
    assert d == {"kontrola": {"zapsano": 3, "nezmeneno": 0, "chyby": []},
                 "version": None}
    # Uložení ani kontrola nanečisto index negenerují.
    assert not (tmp_path / "work" / "index").exists()
    url = f"/api/akce/{EVENT}/dokoncit"
    assert c.post(url, json={"relace": "r2", "version": version}) \
        .status_code == 423
    r = c.post(url, json={"relace": "r1", "version": version})
    assert r.status_code == 200 and r.json["dokonceno"]
    assert r.json["zapsano"] == 3 and r.json["chyby"] == []
    assert r.json["export_version"] == r.json["version"]
    assert (tmp_path / "work" / "index" / "_INDEX.html").exists()
    assert (tmp_path / "work" / "xmp" / EVENT / "foto.jpg.xmp").exists()
    assert c.get(f"/api/akce/{EVENT}").json["export"]["kontrola"][
        "zapsano"] == 0
    assert c.get("/api/akce").json[0]["stav"] == "hotovo"
    assert snapshot(archiv) == before


def test_export_endpoint_removed(client):
    c, _ = client
    saved(c)
    r = c.post(f"/api/akce/{EVENT}/export", json={"relace": "r1"})
    assert r.status_code in (404, 405)


def finished_before(c, datum="2026-10-01"):
    """Uloží akci jako dokončenou k `datum` bez exportu; vrátí verzi."""
    doc, version = saved(c)
    doc["dokonceno"] = datum
    r = c.put(f"/api/akce/{EVENT}/metadata",
              json={"metadata": doc, "version": version, "relace": "r1"})
    return r.json["version"]


def test_refinish_keeps_date(prod):
    """Opakované dokončení nemění datum prvního dokončení (#20)."""
    c, archiv = prod
    version = finished_before(c)
    r = c.post(f"/api/akce/{EVENT}/dokoncit",
               json={"relace": "r1", "version": version})
    assert r.status_code == 200 and r.json["dokonceno"] == "2026-10-01"
    assert r.json["zapsano"] == 3
    assert json.loads((archiv / EVENT / "_metadata.json").read_text())[
        "dokonceno"] == "2026-10-01"


def test_refinish_export_error_keeps_done(prod, monkeypatch):
    """Selhání exportu u dokončené akce ji nevrátí do rozpracovaných."""
    c, archiv = prod
    version = finished_before(c)

    def failing(path, data, mode=None):
        raise OSError("zápis selhal")

    monkeypatch.setattr("fotoarchiv.xmp.write_atomic", failing)
    r = c.post(f"/api/akce/{EVENT}/dokoncit",
               json={"relace": "r1", "version": version})
    assert r.status_code == 200 and r.json["dokonceno"] == "2026-10-01"
    assert len(r.json["chyby"]) == 3
    assert json.loads((archiv / EVENT / "_metadata.json").read_text())[
        "dokonceno"] == "2026-10-01"
    assert c.get("/api/akce").json[0]["stav"] == "hotovo"


def test_finish(prod):
    c, archiv = prod
    doc, version = saved(c)
    url = f"/api/akce/{EVENT}/dokoncit"
    assert c.post(url, json={"relace": "r2", "version": version}) \
        .status_code == 423
    r = c.post(url, json={"relace": "r1", "version": "stará"})
    assert r.status_code == 409 and r.json["version"] == version
    r = c.post(url, json={"relace": "r1", "version": version})
    assert r.status_code == 200 and r.json["dokonceno"]
    assert r.json["zapsano"] == 3
    assert r.json["export_version"] == r.json["version"]
    assert (archiv / EVENT / "foto.jpg.xmp").exists()
    assert r.json["index"] == []
    assert "kontrola" in (archiv / "_INDEX.md").read_text()
    assert "hotovo" in (archiv / "_INDEX.html").read_text()
    event = c.get("/api/akce").json[0]
    assert event["stav"] == "hotovo" and not event["zmeneno_po_exportu"]
    # Sidecary nejsou nezpracované soubory ani se nepočítají.
    assert event["souboru"] == 5
    d = c.get(f"/api/akce/{EVENT}").json
    assert not any(n["nazev"].endswith(".xmp") for n in d["kontrola"])


def test_finish_export_error(prod, monkeypatch):
    c, archiv = prod
    _, version = saved(c)

    def failing(path, data, mode=None):
        raise OSError("zápis selhal")

    monkeypatch.setattr("fotoarchiv.xmp.write_atomic", failing)
    r = c.post(f"/api/akce/{EVENT}/dokoncit",
               json={"relace": "r1", "version": version})
    assert r.status_code == 200 and r.json["dokonceno"] is None
    assert len(r.json["chyby"]) == 3
    assert len(r.json["index"]) == 2
    assert json.loads((archiv / EVENT / "_metadata.json").read_text())[
        "dokonceno"] is None
    assert c.get("/api/akce").json[0]["stav"] == "rozpracovano"


HIDDEN = f"{EVENT}.ignored"


def finish(c, version):
    return c.post(f"/api/akce/{EVENT}/dokoncit",
                  json={"relace": "r1", "version": version})


def test_finish_publishes_hidden_event(prod):
    """Dokončení odebere příponu `.ignored` až po zápisu sidecarů."""
    c, archiv = prod
    (archiv / EVENT).rename(archiv / HIDDEN)
    assert c.get("/api/akce").json[0]["nazev"] == EVENT
    doc, version = saved(c)
    assert (archiv / HIDDEN / "_metadata.json").is_file()
    r = finish(c, version)
    assert r.status_code == 200 and r.json["dokonceno"]
    assert "zverejneni" not in r.json
    assert not (archiv / HIDDEN).exists()
    assert (archiv / EVENT / "foto.jpg.xmp").exists()
    assert 'href="./2026-04-28%20kontrola/"' in \
        (archiv / "_INDEX.html").read_text()
    # Akce jde dál otevřít a upravit pod týmž názvem a zámkem.
    d = c.get(f"/api/akce/{EVENT}").json
    doc = d["metadata"]
    doc["akce"]["popis"] = "nový popis"
    r = c.put(f"/api/akce/{EVENT}/metadata", json={
        "metadata": doc, "version": d["version"], "relace": "r1"})
    assert r.status_code == 200
    # Opakované dokončení příponu nevrátí.
    assert finish(c, r.json["version"]).json["dokonceno"]
    assert (archiv / EVENT).is_dir() and not (archiv / HIDDEN).exists()


def test_finish_rename_error(prod, monkeypatch):
    c, archiv = prod
    (archiv / EVENT).rename(archiv / HIDDEN)
    _, version = saved(c)

    def failing(src, dst):
        raise OSError("soubor je otevřený")

    monkeypatch.setattr("fotoarchiv.archive.os.rename", failing)
    r = finish(c, version)
    assert r.status_code == 200 and r.json["dokonceno"] is None
    assert r.json["zverejneni"] == "soubor je otevřený"
    assert r.json["chyby"] == []
    assert (archiv / HIDDEN / "foto.jpg.xmp").exists()
    assert json.loads((archiv / HIDDEN / "_metadata.json").read_text())[
        "dokonceno"] is None
    assert c.get("/api/akce").json[0]["stav"] == "rozpracovano"


def test_finish_dev_mode_keeps_suffix(tmp_path, monkeypatch):
    c, archiv = make_client(tmp_path, monkeypatch)
    (archiv / EVENT).rename(archiv / HIDDEN)
    _, version = saved(c)
    assert finish(c, version).json["dokonceno"]
    assert (archiv / HIDDEN).is_dir() and not (archiv / EVENT).exists()


def test_collision_refused(prod):
    c, archiv = prod
    (archiv / HIDDEN).mkdir()
    before = snapshot(archiv)
    assert c.get("/api/akce").json[0]["stav"] == "kolize"
    r = c.get(f"/api/akce/{EVENT}")
    assert r.status_code == 409 and r.json["chyba"] == "kolize_pripony"
    assert c.post(f"/api/akce/{EVENT}/dokoncit", json={
        "relace": "r1", "version": None}).status_code == 409
    assert c.get(f"/api/akce/{HIDDEN}").status_code == 404
    assert snapshot(archiv) == before


def test_scan_cache_survives_publish(prod, tmp_path):
    c, archiv = prod
    (archiv / EVENT).rename(archiv / HIDDEN)
    _, version = saved(c)
    cache = tmp_path / "work" / "cache" / "scan" / f"{EVENT}.json"
    assert cache.is_file()
    finish(c, version)
    assert cache.is_file()
    assert not (cache.parent / f"{HIDDEN}.json").exists()


def test_cli_export(tmp_path, monkeypatch, capsys):
    c, archiv = make_client(tmp_path, monkeypatch)
    saved(c)
    (archiv / "2020-01-01 bez metadat").mkdir()
    before = snapshot(archiv)
    work = str(tmp_path / "work")
    main(["exportovat", "--archiv", str(archiv), "--work", work])
    out = capsys.readouterr().out
    assert f"{EVENT}: zapsáno 3, nezměněno 0, selhalo 0" in out
    assert "přeskočeno: 2020-01-01 bez metadat" in out
    assert f"index: {tmp_path / 'work' / 'index'}" in out
    assert "bez metadat" in (tmp_path / "work" / "index" / "_INDEX.md") \
        .read_text()
    assert snapshot(archiv) == before
    main(["exportovat", EVENT, "--archiv", str(archiv), "--work", work])
    assert "zapsáno 0, nezměněno 3" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["exportovat", "2020-01-02 neni", "--archiv", str(archiv)])


def marked(c, names, popis=None):
    """Uloží dokument s označenými soubory; vrátí verzi."""
    doc, version = saved(c)
    for name in names:
        doc["soubory"][name]["vyradit"] = True
    if popis:
        doc["soubory"][names[0]]["popis"] = popis
    r = c.put(f"/api/akce/{EVENT}/metadata",
              json={"metadata": doc, "version": version, "relace": "r1"})
    return r.json["version"]


DISCARD = {"z_plochy": True, "relace": "r1"}


def test_discard_plan_from_saved(client):
    c, archiv = client
    before = snapshot(archiv)
    marked(c, ["foto.jpg"])
    plan = c.post(f"/api/akce/{EVENT}/uklid", json=DISCARD).json
    # Podsložka RAW bez volby se z plochy nemění, RAW a ostatní z kořene ano.
    assert [(o["z"], o["do"]) for o in plan["operace"]] == [
        ("foto.jpg", "k_odstraneni.ignored/foto.jpg"),
        ("a.rw2", "RAW.ignored/a.rw2"),
        ("pozn.txt", "ostatni.ignored/pozn.txt")]
    assert plan["podslozky"][0]["volba"] is None
    # Dřívější název příznaku.
    old = c.post(f"/api/akce/{EVENT}/uklid",
                 json={"jen_vyradit": True}).json
    assert old["operace"] == plan["operace"]
    r = c.post(f"/api/akce/{EVENT}/uklid/provest", json=DISCARD)
    assert r.status_code == 403
    assert snapshot(archiv) == before


def test_discard_execute(prod):
    c, archiv = prod
    marked(c, ["foto.jpg", "v.mp4"], popis="Nepovedená")
    (archiv / EVENT / "foto.jpg.xmp").write_text("starý")
    (archiv / EVENT / "k_odstraneni.ignored").mkdir()
    (archiv / EVENT / "k_odstraneni.ignored" / "v.mp4").write_text("jiné")
    r = c.post(f"/api/akce/{EVENT}/uklid/provest", json=DISCARD)
    assert r.status_code == 200
    assert [(o["z"], o["stav"]) for o in r.json["operace"]] == [
        ("foto.jpg", "hotovo"), ("v.mp4", "blokovano"), ("a.rw2", "hotovo"),
        ("pozn.txt", "hotovo")]
    target = archiv / EVENT / "k_odstraneni.ignored"
    assert (target / "foto.jpg").is_file()
    xmp = (target / "foto.jpg.xmp").read_text()
    assert "Nepovedená" in xmp and "vyrad" not in xmp
    assert not (archiv / EVENT / "foto.jpg.xmp").exists()
    # Podsložka RAW bez volby zůstane, RAW a ostatní z kořene se přesunou.
    assert (archiv / EVENT / "RAW").is_dir()
    assert (archiv / EVENT / "RAW.ignored" / "a.rw2").read_text() == "raw"
    assert (archiv / EVENT / "ostatni.ignored" / "pozn.txt").is_file()
    d = c.get(f"/api/akce/{EVENT}").json
    assert d["version"] == r.json["version"]
    assert "foto.jpg" not in d["metadata"]["soubory"]
    assert d["metadata"]["soubory"]["v.mp4"]["vyradit"] is True
    assert d["chybejici"] == []


def test_workspace_cleanup_subfolder_choice(prod):
    c, archiv = prod
    saved(c)
    r = c.post(f"/api/akce/{EVENT}/uklid/provest",
               json=dict(DISCARD, volby={"RAW": "presunout"}))
    assert r.status_code == 200
    # RAW/a.rw2 do kořene koliduje s a.rw2 v kořeni, ten jde do RAW.ignored.
    assert [(o["z"], o["stav"]) for o in r.json["operace"]] == [
        ("RAW/a.rw2", "blokovano"), ("RAW", "blokovano"),
        ("a.rw2", "hotovo"), ("pozn.txt", "hotovo")]


def test_discard_execute_requires_lock(prod):
    c, archiv = prod
    marked(c, ["foto.jpg"])
    r = c.post(f"/api/akce/{EVENT}/uklid/provest",
               json=dict(DISCARD, relace="r2"))
    assert r.status_code == 423
    assert (archiv / EVENT / "foto.jpg").exists()


# --- přihlášení ------------------------------------------------------------

USERS = {"spacil": {"jmeno": "Spáčil, David", "role": "admin",
                    "email": "spacil@example.cz"},
         "kopacova": {"jmeno": "Kopáčová, Jana"},
         "novak": {"jmeno": "Novák, Petr", "role": "archivar"}}
HESLO = "tajne-heslo-1"


@pytest.fixture
def login_app(tmp_path, monkeypatch):
    """(app, archiv) s přihlášením v produkčním režimu; admin `spacil`,
    běžná `kopacova`, archivář `novak`, všichni s heslem HESLO."""
    from fotoarchiv import auth
    work = tmp_path / "work"
    work.mkdir()
    (work / "uzivatele.json").write_text(json.dumps(USERS),
                                         encoding="utf-8")
    passwords = auth.Passwords(work)
    for login in USERS:
        passwords.set(login, HESLO)
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    make_tree(archiv, {f"{EVENT}/": {"IMG-20260428-WA0001.jpg": "x"}})
    monkeypatch.setattr("fotoarchiv.scan.run_exiftool", lambda d, n: {})
    app = create_app(archiv, work, zapis=True)
    app.testing = True
    return app, archiv


def logged_in(app, login, heslo=HESLO):
    c = app.test_client()
    r = c.post("/api/prihlaseni", json={"login": login, "heslo": heslo})
    assert r.status_code == 200, r.json
    return c


def test_unauthenticated_rejected(login_app):
    app, archiv = login_app
    before = snapshot(archiv)
    c = app.test_client()
    doc = {"schema": 1}
    r = c.put(f"/api/akce/{EVENT}/metadata",
              json={"metadata": doc, "version": None, "relace": "r1"})
    assert r.status_code == 401 and r.json["chyba"] == "neprihlasen"
    assert c.get("/api/akce").status_code == 401
    r = c.get("/")
    assert r.status_code == 302 and r.location.endswith("/prihlaseni")
    assert c.get("/prihlaseni").status_code == 200
    assert c.get("/static/app.js").status_code == 200
    assert snapshot(archiv) == before


def test_login_cookie_and_me(login_app):
    app, _ = login_app
    c = app.test_client()
    r = c.post("/api/prihlaseni", json={"login": "Spacil", "heslo": HESLO})
    cookie = r.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert "Secure" not in cookie
    assert HESLO not in r.get_data(as_text=True)
    assert c.get("/api/ja").json == {
        "prihlaseni": True, "login": "spacil", "jmeno": "Spáčil, David",
        "role": "admin", "admin": True, "archivar": True,
        "zmenit_heslo": False}
    assert c.get("/api/akce").status_code == 200
    assert c.get("/").status_code == 200
    c.post("/api/odhlaseni")
    assert c.get("/api/akce").status_code == 401


def test_me_roles(login_app):
    app, _ = login_app
    for login, role, admin, archivar in (("spacil", "admin", True, True),
                                         ("novak", "archivar", False, True),
                                         ("kopacova", None, False, False)):
        me = logged_in(app, login).get("/api/ja").json
        assert (me["role"], me["admin"], me["archivar"]) == \
            (role, admin, archivar)


def test_https_cookie_secure(tmp_path):
    app = create_app(tmp_path, tmp_path / "work", https=True)
    assert app.config["SESSION_COOKIE_SECURE"] is True


def test_wrong_and_unknown_login_same(login_app):
    app, _ = login_app
    c = app.test_client()
    wrong = c.post("/api/prihlaseni", json={"login": "spacil", "heslo": "x"})
    unknown = c.post("/api/prihlaseni", json={"login": "nikdo", "heslo": "x"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json == unknown.json == {"chyba": "neplatne"}


def test_login_throttled(login_app):
    app, _ = login_app
    c = app.test_client()
    for _ in range(5):
        c.post("/api/prihlaseni", json={"login": "spacil", "heslo": "x"})
    r = c.post("/api/prihlaseni", json={"login": "spacil", "heslo": HESLO})
    assert r.status_code == 429 and r.json["za_s"] >= 1


def test_one_time_password_only_change(login_app):
    app, _ = login_app
    heslo = app.config["AUTH"].issue("kopacova")
    c = logged_in(app, "kopacova", heslo)
    assert c.get("/api/ja").json["zmenit_heslo"] is True
    r = c.get("/api/akce")
    assert r.status_code == 403 and r.json["chyba"] == "zmenit_heslo"
    assert c.get("/").location.endswith("/heslo")
    assert c.get("/heslo").status_code == 200
    r = c.post("/api/heslo", json={"stavajici": heslo, "nove": "kratke"})
    assert r.status_code == 400 and r.json["chyba"] == "kratke_heslo"
    r = c.post("/api/heslo", json={"stavajici": heslo,
                                   "nove": "vlastni-heslo"})
    assert r.status_code == 200 and r.json["zmenit_heslo"] is False
    assert c.get("/api/akce").status_code == 200


def test_password_change_ends_other_sessions(login_app):
    app, _ = login_app
    a = logged_in(app, "kopacova")
    b = logged_in(app, "kopacova")
    r = a.post("/api/heslo", json={"stavajici": "spatne",
                                   "nove": "nove-heslo-22"})
    assert r.status_code == 400 and r.json["chyba"] == "spatne_heslo"
    assert a.post("/api/heslo", json={"stavajici": HESLO,
                                      "nove": "nove-heslo-22"}).status_code == 200
    assert a.get("/api/akce").status_code == 200
    assert b.get("/api/akce").status_code == 401
    r = app.test_client().post("/api/prihlaseni",
                               json={"login": "kopacova", "heslo": HESLO})
    assert r.status_code == 401


def test_new_one_time_password_ends_sessions(login_app):
    app, _ = login_app
    c = logged_in(app, "kopacova")
    app.config["AUTH"].issue("kopacova")
    assert c.get("/api/akce").status_code == 401


def test_removed_user_401(login_app, tmp_path):
    app, _ = login_app
    c = logged_in(app, "kopacova")
    path = tmp_path / "work" / "uzivatele.json"
    path.write_text(json.dumps({"spacil": USERS["spacil"]}))
    import os
    os.utime(path, ns=(1, 1))
    assert c.get("/api/akce").status_code == 401


def own(app, jmeno, nazev=EVENT):
    """Akce s `_metadata.json`, v jehož `upravili` je `jmeno`."""
    from fotoarchiv.archive import SCHEMA
    ws = app.config["WORKSPACE"]
    _, version = ws.load(nazev)
    ws.save(nazev, {"schema": SCHEMA, "akce": {}, "skupiny": {},
                    "soubory": {}, "upravili": {jmeno: "2026-10-14T10:15:02"}},
            version)


def set_users(tmp_path, users):
    path = tmp_path / "work" / "uzivatele.json"
    path.write_text(json.dumps(users), encoding="utf-8")
    os.utime(path, ns=(1, 1))  # jiný mtime i při rychlém přepisu


def test_lock_name_from_login_and_logout_releases(login_app):
    app, _ = login_app
    own(app, "Kopáčová, Jana")
    c = logged_in(app, "kopacova")
    r = c.post(f"/api/akce/{EVENT}/zamek",
               json={"relace": "r1", "jmeno": "Podvržené, Jméno"})
    assert r.json["zamek"]["jmeno"] == "Kopáčová, Jana"
    other = logged_in(app, "spacil")
    r = other.post(f"/api/akce/{EVENT}/zamek", json={"relace": "r2"})
    assert r.status_code == 409
    assert r.json["drzitel"]["jmeno"] == "Kopáčová, Jana"
    c.post("/api/odhlaseni")
    assert other.post(f"/api/akce/{EVENT}/zamek",
                      json={"relace": "r2"}).status_code == 200


def test_force_release_admin_and_archivist(login_app):
    app, _ = login_app
    own(app, "Kopáčová, Jana")
    user = logged_in(app, "kopacova")
    doc = user.get(f"/api/akce/{EVENT}").json["metadata"]
    user.post(f"/api/akce/{EVENT}/zamek", json={"relace": "r1"})
    r = user.post(f"/api/akce/{EVENT}/zamek/vynutit")
    assert r.status_code == 403
    archivar = logged_in(app, "novak")
    r = archivar.post(f"/api/akce/{EVENT}/zamek/vynutit")
    assert r.json["uvolneno"]["jmeno"] == "Kopáčová, Jana"
    assert archivar.post(f"/api/akce/{EVENT}/zamek",
                         json={"relace": "r2"}).status_code == 200
    r = user.put(f"/api/akce/{EVENT}/zamek", json={"relace": "r1"})
    assert r.status_code == 409 and r.json["uvolnil"] == "Novák, Petr"
    r = user.put(f"/api/akce/{EVENT}/metadata",
                 json={"metadata": doc, "version": None, "relace": "r1"})
    assert r.status_code == 423
    admin = logged_in(app, "spacil")
    r = admin.post(f"/api/akce/{EVENT}/zamek/vynutit")
    assert r.json["uvolneno"]["jmeno"] == "Novák, Petr"


def test_edit_permission(login_app):
    app, _ = login_app
    user = logged_in(app, "kopacova")
    archivar = logged_in(app, "novak")
    # Akce bez _metadata.json: jen admin a archivář.
    assert user.get("/api/akce").json[0]["upravit"] is False
    assert archivar.get("/api/akce").json[0]["upravit"] is True
    r = user.post(f"/api/akce/{EVENT}/zamek", json={"relace": "r1"})
    assert r.status_code == 403 and r.json["chyba"] == "jen_cteni"
    assert app.config["LOCKS"].holder(EVENT) is None
    # Prohlížet smí.
    assert user.get(f"/api/akce/{EVENT}").status_code == 200
    # Cizí akce (jiné jméno v upravili).
    own(app, "Spáčil, David")
    assert user.get("/api/akce").json[0]["upravit"] is False
    assert user.post(f"/api/akce/{EVENT}/zamek",
                     json={"relace": "r1"}).status_code == 403
    # Archivář u cizí akce zámek dostane a smí uložit i dokončit.
    assert archivar.post(f"/api/akce/{EVENT}/zamek",
                         json={"relace": "r2"}).status_code == 200
    doc, version = app.config["WORKSPACE"].load(EVENT)
    r = archivar.put(f"/api/akce/{EVENT}/metadata",
                     json={"metadata": doc, "version": version,
                           "relace": "r2"})
    assert r.status_code == 200
    archivar.delete(f"/api/akce/{EVENT}/zamek", json={"relace": "r2"})
    # Vlastní akce (jméno bez diakritiky v upravili).
    own(app, "Kopacova, Jana")
    assert user.get("/api/akce").json[0]["upravit"] is True
    assert user.post(f"/api/akce/{EVENT}/zamek",
                     json={"relace": "r1"}).status_code == 200


def test_role_removed_while_holding_lock(login_app, tmp_path):
    app, _ = login_app
    archivar = logged_in(app, "novak")
    assert archivar.post(f"/api/akce/{EVENT}/zamek",
                         json={"relace": "r1"}).status_code == 200
    doc = archivar.get(f"/api/akce/{EVENT}").json["metadata"]
    set_users(tmp_path, dict(USERS, novak={"jmeno": "Novák, Petr"}))
    r = archivar.put(f"/api/akce/{EVENT}/metadata",
                     json={"metadata": doc, "version": None, "relace": "r1"})
    assert r.status_code == 403 and r.json["chyba"] == "jen_cteni"
    assert not (app.config["WORKSPACE"].metadata_path(EVENT)).exists()


def test_unsorted_admin_and_archivist(login_app):
    app, archiv = login_app
    unsorted_tree(archiv)
    user = logged_in(app, "kopacova")
    r = user.get("/api/pretridit")
    assert r.status_code == 403 and r.json["chyba"] == "jen_archivar"
    r = user.post("/api/import", json={"zdroj": "DOD 2019"})
    assert r.status_code == 403
    assert user.get("/api/import").json["importy"] == []
    assert not (app.config["IMPORTS"].root).exists() or \
        not any(app.config["IMPORTS"].root.iterdir())
    archivar = logged_in(app, "novak")
    assert ndjson(archivar.get("/api/pretridit?exif=0"))[0]["slozky"]
    assert archivar.post("/api/import",
                         json={"zdroj": "DOD 2019"}).status_code == 200
    assert archivar.put("/api/nominatim",
                        json={"kontakt": "x@example.cz"}).status_code == 403
    admin = logged_in(app, "spacil")
    assert admin.get("/api/pretridit?exif=0").status_code == 200


def test_unsorted_execute_without_role(login_app, tmp_path):
    app, archiv = login_app
    unsorted_tree(archiv)
    archivar = logged_in(app, "novak")
    id = archivar.post("/api/import", json={"zdroj": "DOD 2019"}).json["id"]
    nova = "2019-05-01 DOD 2019"
    ndjson(archivar.post(f"/api/import/{id}/plan", json={"nova": nova}))
    set_users(tmp_path, dict(USERS, novak={"jmeno": "Novák, Petr"}))
    r = archivar.post(f"/api/import/{id}/provest",
                      json={"relace": "r1", "nova": nova})
    assert r.status_code == 403 and r.json["chyba"] == "jen_archivar"
    assert not (archiv / (nova + ".ignored")).exists()


def test_import_owner_from_login(login_app):
    app, _ = login_app
    admin = logged_in(app, "spacil")
    id = admin.post("/api/import", json={"jmeno": "Podvržené, Jméno"}) \
        .json["id"]
    admin.post(f"/api/import/{id}/soubor", data=b"a",
               query_string={"cesta": "a.jpg", "mtime": 1})
    [item] = admin.get("/api/import").json["importy"]
    assert item["id"] == id
    user = logged_in(app, "kopacova")
    cizi = {"jmeno": "Spáčil, David"}
    assert user.get("/api/import", query_string=cizi).json["importy"] == []
    assert user.get(f"/api/import/{id}",
                    query_string=cizi).status_code == 404
    assert user.post(f"/api/import/{id}/plan", json=dict(
        cizi, nova="2026-04-28 nová")).status_code == 404
    assert user.post(f"/api/import/{id}/provest", json=dict(
        cizi, relace="r1", nova="2026-04-28 nová")).status_code == 404
    assert user.delete(f"/api/import/{id}", json=cizi).status_code == 404
    assert admin.get(f"/api/import/{id}").json["pocty"] == {"foto": 1}


def test_import_new_event_writes_editors(login_app):
    app, archiv = login_app
    user = logged_in(app, "kopacova")
    id = user.post("/api/import", json={}).json["id"]
    data = io.BytesIO()
    Image.new("RGB", (10, 10)).save(data, "JPEG")
    user.post(f"/api/import/{id}/soubor", data=data.getvalue(),
              query_string={"cesta": "a.jpg", "mtime": 1})
    nova = "2026-04-29 workshop"
    ndjson(user.post(f"/api/import/{id}/plan", json={"nova": nova}))
    events = ndjson(user.post(f"/api/import/{id}/provest",
                              json={"relace": "r1", "nova": nova}))
    assert events[-1]["typ"] == "vysledek"
    assert events[-1]["skupiny"]["zapsano"] is True
    doc, _ = app.config["WORKSPACE"].load(nova)
    assert list(doc["upravili"]) == ["Kopáčová, Jana"]
    [event] = [e for e in user.get("/api/akce").json if e["nazev"] == nova]
    assert event["upravit"] is True
    user.delete(f"/api/akce/{nova}/zamek", json={"relace": "r1"})
    assert user.post(f"/api/akce/{nova}/zamek",
                     json={"relace": "r2"}).status_code == 200


def test_import_into_foreign_event_refused(login_app):
    app, archiv = login_app
    own(app, "Spáčil, David")
    user = logged_in(app, "kopacova")
    id = user.post("/api/import", json={}).json["id"]
    user.post(f"/api/import/{id}/soubor", data=b"n",
              query_string={"cesta": "n.jpg", "mtime": 1})
    ndjson(user.post(f"/api/import/{id}/plan", json={"cil": EVENT}))
    # Zámek cizí akce nedostane, bez něj provedení neprojde.
    r = user.post(f"/api/akce/{EVENT}/zamek", json={"relace": "r1"})
    assert r.status_code == 403
    r = user.post(f"/api/import/{id}/provest",
                  json={"relace": "r1", "cil": EVENT})
    assert r.status_code == 423
    assert not (archiv / EVENT / "n.jpg").exists()


def test_nominatim_contact_admin_only(login_app, tmp_path):
    app, _ = login_app
    user = logged_in(app, "kopacova")
    assert user.put("/api/nominatim",
                    json={"kontakt": "x@example.cz"}).status_code == 403
    assert app.test_client().get("/api/info").status_code == 401
    admin = logged_in(app, "spacil")
    assert admin.get("/api/info").json["geokodovani"] is False
    assert admin.get("/api/nominatim").json == {
        "kontakt": None, "navrh": "spacil@example.cz"}
    assert admin.put("/api/nominatim", json={"kontakt": " "}).status_code \
        == 400
    r = admin.put("/api/nominatim", json={"kontakt": "archiv@example.cz"})
    assert r.json["kontakt"] == "archiv@example.cz"
    assert user.get("/api/info").json["geokodovani"] is True
    path = tmp_path / "work" / "nominatim.json"
    assert path.stat().st_mode & 0o777 == 0o600
    assert admin.delete("/api/nominatim").json["kontakt"] is None
    assert user.get("/api/info").json["geokodovani"] is False


def test_without_login_everyone_admin(client):
    c, _ = client
    assert c.get("/api/ja").json == {
        "prihlaseni": False, "login": None, "jmeno": None, "role": "admin",
        "admin": True, "archivar": True, "zmenit_heslo": False}
    assert c.get("/prihlaseni").status_code == 302
    r = c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    assert r.json["zamek"]["jmeno"] == "Spáčil, David"
    assert c.post(f"/api/akce/{EVENT}/zamek/vynutit").status_code == 200


def test_production_without_login_refused(tmp_path, capsys):
    (tmp_path / "archiv").mkdir()
    with pytest.raises(SystemExit) as e:
        main(["--archiv", str(tmp_path / "archiv"), "--work",
              str(tmp_path / "work"), "--zapis-do-archivu",
              "--bez-prihlaseni"])
    assert "bez přihlášení" in str(e.value)


def test_password_command(tmp_path, capsys):
    from fotoarchiv import auth
    work = tmp_path / "work"
    work.mkdir()
    (work / "uzivatele.json").write_text(json.dumps(USERS))
    with pytest.raises(SystemExit) as e:
        main(["heslo", "nikdo", "--work", str(work)])
    assert "nikdo" in str(e.value)
    main(["heslo", "kopacova", "--work", str(work)])
    heslo = capsys.readouterr().out.strip().rsplit(" ", 1)[1]
    a = auth.Auth(work)
    assert a.passwords.must_change("kopacova")
    assert a.login("kopacova", heslo)[1] is None
    assert heslo not in (work / "hesla.json").read_text()


OLD_USERS = {"spacil": {"jmeno": "Spáčil, David", "admin": True}}


def test_old_users_file_refused(tmp_path, monkeypatch):
    monkeypatch.setattr("fotoarchiv.__main__.serve", lambda *a, **k: None)
    work = tmp_path / "work"
    work.mkdir()
    (work / "uzivatele.json").write_text(json.dumps(OLD_USERS))
    (tmp_path / "archiv").mkdir()
    for argv in (["heslo", "spacil", "--work", str(work)],
                 ["--archiv", str(tmp_path / "archiv"), "--work",
                  str(work)]):
        with pytest.raises(SystemExit) as e:
            main(argv)
        assert e.value.code not in (0, None)
        assert "spacil" in str(e.value)
        assert '"role": "admin"' in str(e.value)
    assert not (work / "hesla.json").exists()
    # Bez přihlášení se soubor nečte.
    main(["--archiv", str(tmp_path / "archiv"), "--work", str(work),
          "--bez-prihlaseni"])


def test_contact_option_migrated(tmp_path, monkeypatch, capsys):
    from fotoarchiv import geocode
    monkeypatch.setattr("fotoarchiv.__main__.serve", lambda *a, **k: None)
    (tmp_path / "archiv").mkdir()
    args = ["--archiv", str(tmp_path / "archiv"), "--work",
            str(tmp_path / "work"), "--bez-prihlaseni"]
    main(args + ["--kontakt", "archiv@example.cz"])
    assert "zastaralý" in capsys.readouterr().out
    contact = geocode.Contact(tmp_path / "work")
    assert contact.load() == "archiv@example.cz"
    main(args + ["--kontakt", "jiny@example.cz"])  # už nastaveno: ignoruje
    assert "ignoruje" in capsys.readouterr().out
    assert contact.load() == "archiv@example.cz"


# --- přetřídit -------------------------------------------------------------

def ndjson(r):
    assert r.status_code == 200, r.get_data(as_text=True)
    return [json.loads(line) for line in r.get_data(as_text=True).splitlines()]


def unsorted_tree(archiv):
    make_tree(archiv, {"přetřídit/": {
        "DOD 2019/": {"a.jpg": "a", "b.jpg": "bb", "NEF/": {"a.nef": "r"}},
        "_duplicity.ignored/": {"a.jpg": "a"}, "pozn.txt": "x"}})


def test_api_pretridit(client):
    c, archiv = client
    assert ndjson(c.get("/api/pretridit")) == [{"typ": "vypis",
                                                "slozky": []}]
    unsorted_tree(archiv)
    events = ndjson(c.get("/api/pretridit"))
    [item] = events[0]["slozky"]
    assert item["nazev"] == "DOD 2019"
    assert item["pocty"] == {"foto": 2, "raw": 1}
    assert item["podslozky"] == ["NEF"]
    assert events[1]["typ"] == "slozka" and events[1]["navrh"]["akce"] is None
    assert ndjson(c.get("/api/pretridit?exif=0")) == events[:1]


def test_api_source_dev_mode(client):
    c, archiv = client
    unsorted_tree(archiv)
    before = snapshot(archiv)
    for bad in ("../x", "_duplicity.ignored", "pozn.txt"):
        r = c.post("/api/import", json=dict(R1, zdroj=bad))
        assert r.status_code == 400 and r.json["chyba"] == "neplatny_zdroj"
    body = dict(R1, zdroj="DOD 2019", cil="2019-05-01 DOD 2019", nova=True)
    id = c.post("/api/import", json=body).json["id"]
    assert c.post("/api/import", json=body).json["id"] == id
    o = c.get(f"/api/import/{id}", query_string={"jmeno": R1["jmeno"]}).json
    assert o["zdroj"] == "DOD 2019" and o["pocty"] == {"foto": 2, "raw": 1}
    assert o["cil"] == "2019-05-01 DOD 2019" and o["nova"]
    plan = ndjson(c.post(f"/api/import/{id}/plan", json={
        "jmeno": R1["jmeno"], "nova": "2019-05-01 DOD 2019"}))[-1]
    assert [(o["z"], o["stav"]) for o in plan["operace"]] == [
        ("DOD 2019/NEF/a.nef", "ok"), ("DOD 2019/a.jpg", "ok"),
        ("DOD 2019/b.jpg", "ok")]
    r = c.post(f"/api/import/{id}/provest",
               json=dict(R1, nova="2019-05-01 DOD 2019"))
    assert r.status_code == 403 and r.json["chyba"] == "vyvojovy_rezim"
    assert c.delete(f"/api/import/{id}", json=R1).status_code == 200
    assert snapshot(archiv) == before


def test_api_source_lock(prod):
    c, archiv = prod
    unsorted_tree(archiv)
    jana = c.post("/api/import", json=dict(R2, zdroj="DOD 2019")).json["id"]
    david = c.post("/api/import", json=dict(R1, zdroj="DOD 2019")).json["id"]
    r = c.post(f"/api/import/{david}/provest",
               json=dict(R1, nova="2019-05-01 DOD David"))
    assert r.status_code == 409 and r.json["chyba"] == "bez_planu"
    assert c.application.config["LOCKS"].holder("přetřídit/DOD 2019") is None
    for id, who, name in ((jana, R2, "Jana"), (david, R1, "David")):
        ndjson(c.post(f"/api/import/{id}/plan", json={
            "jmeno": who["jmeno"], "nova": f"2019-05-01 DOD {name}"}))
    r = c.post(f"/api/import/{jana}/provest",
               json=dict(R2, nova="2019-05-01 DOD Jana"), buffered=False)
    chunks = iter(r.response)
    assert b'"kontrola"' in next(chunks)  # provedení běží, zámek drží
    refused = c.post(f"/api/import/{david}/provest",
                     json=dict(R1, nova="2019-05-01 DOD David"))
    assert refused.status_code == 409
    assert refused.json["chyba"] == "zdroj_obsazen"
    assert refused.json["drzitel"]["jmeno"] == R2["jmeno"]
    assert not (archiv / "2019-05-01 DOD David").exists()
    r.close()  # přerušení uvolní zámek zdroje
    r = c.post(f"/api/import/{david}/provest",
               json=dict(R1, nova="2019-05-01 DOD David"))
    result = ndjson(r)[-1]
    r.close()
    assert result["typ"] == "vysledek" and result["zahozeno"]
    moved = sorted(os.listdir(archiv / "2019-05-01 DOD David.ignored"))
    assert "RAW.ignored" in moved
    assert c.application.config["LOCKS"].holder("přetřídit/DOD 2019") is None


# --- integrita v aplikaci (issue #10, varianta C) ---------------------------

def test_thumb_plni_cache_integrity(client, tmp_path):
    c, archiv = client
    from PIL import Image
    import io as _io
    img = _io.BytesIO()
    Image.new("RGB", (100, 80)).save(img, "JPEG")
    data = bytearray(img.getvalue())
    data[:65536] = b"\x00" * 65536
    (archiv / EVENT / "shora.jpg").write_bytes(bytes(data))
    # Náhled takového souboru nevyjde (404 -> zástupná ikona), ale
    # kontrola musí proběhnout a zapsat se bez ohledu na výsledek.
    c.get(f"/api/akce/{EVENT}/nahled/shora.jpg")
    cache = tmp_path / "work" / "cache" / "kontrola" / f"{EVENT}.json"
    assert json.loads(cache.read_text())["shora.jpg"]["vysledek"]["stav"] \
        == "necitelny"
    d = c.get(f"/api/akce/{EVENT}").json
    assert d["poskozene"]["shora.jpg"]["stav"] == "necitelny"
    assert c.get("/api/akce").json[0]["poskozene"] == 1


def test_overeno_roundtrip_a_odznak(client):
    c, archiv = client
    import io as _io
    from PIL import Image
    img = _io.BytesIO()
    Image.new("RGB", (100, 80)).save(img, "JPEG")
    data = bytearray(img.getvalue())
    data[:65536] = b"\x00" * 65536
    (archiv / EVENT / "shora.jpg").write_bytes(bytes(data))
    c.get(f"/api/akce/{EVENT}/nahled/shora.jpg")  # at je ve vysledcich
    assert c.get("/api/akce").json[0]["poskozene"] == 1
    doc, version = saved(c)
    doc["soubory"]["shora.jpg"] = {"overeno": True}
    c.put(f"/api/akce/{EVENT}/metadata",
          json={"metadata": doc, "version": version, "relace": "r1"})
    d = c.get(f"/api/akce/{EVENT}").json
    assert d["metadata"]["soubory"]["shora.jpg"]["overeno"] is True
    # Souhrn detailu obsahuje i potvrzený (se značkou), odznak ne.
    assert d["poskozene"]["shora.jpg"] == {
        "stav": "necitelny", "duvody": d["poskozene"]["shora.jpg"]["duvody"],
        "overeno": True}
    assert c.get("/api/akce").json[0]["poskozene"] == 0
    # Zruseni potvrzeni: pole se pri ulozeni odstrani spolu s hodnotou.
    doc, version = d["metadata"], d["version"]
    del doc["soubory"]["shora.jpg"]["overeno"]
    c.put(f"/api/akce/{EVENT}/metadata",
          json={"metadata": doc, "version": version, "relace": "r1"})
    assert "overeno" not in c.get(
        f"/api/akce/{EVENT}").json["metadata"]["soubory"]["shora.jpg"]
    assert c.get("/api/akce").json[0]["poskozene"] == 1


def test_overeno_se_nededi_a_neexportuje(prod):
    c, archiv = prod
    doc, version = saved(c)
    doc["soubory"]["foto.jpg"]["overeno"] = True
    r = c.put(f"/api/akce/{EVENT}/metadata",
              json={"metadata": doc, "version": version, "relace": "r1"})
    doc = c.get(f"/api/akce/{EVENT}").json["metadata"]
    assert doc["akce"].get("overeno") is None
    out = c.post(f"/api/akce/{EVENT}/dokoncit",
                 json={"relace": "r1", "version": r.json["version"]}).json
    assert out["chyby"] == [] and out["zapsano"] >= 1
    sidecar = (archiv / EVENT / "foto.jpg.xmp").read_text()
    assert "overeno" not in sidecar


# --- seznam akcí jako fronta práce (fronta-akci) ----------------------------

def test_list_holder_and_yours(client):
    c, _ = client
    assert c.get("/api/akce").json[0]["drzitel"] is None
    c.post(f"/api/akce/{EVENT}/zamek", json=R1)
    r = c.get("/api/akce?relace=r1")
    assert r.json[0]["drzitel"] == {"jmeno": "Spáčil, David", "vase": True}
    r = c.get("/api/akce?relace=r2")
    assert r.json[0]["drzitel"] == {"jmeno": "Spáčil, David", "vase": False}
    assert c.get("/api/akce").json[0]["drzitel"]["vase"] is False
    assert b"r1" not in c.get("/api/akce?relace=r1").data


def test_save_writes_editors_ignores_client(client):
    c, _ = client
    doc, version = saved(c)
    stored = c.get(f"/api/akce/{EVENT}").json["metadata"]
    assert list(stored["upravili"]) == ["Spáčil, David"]
    first = stored["upravili"]["Spáčil, David"]
    assert len(first) == 19 and first[10] == "T"
    # Podvržená hodnota od klienta se zahodí.
    doc["upravili"] = {"Podvržený, Pán": "2030-01-01T00:00:00"}
    r = c.put(f"/api/akce/{EVENT}/metadata",
              json={"metadata": doc, "version": version, "relace": "r1"})
    assert r.status_code == 200
    stored = c.get(f"/api/akce/{EVENT}").json["metadata"]
    assert list(stored["upravili"]) == ["Spáčil, David"]
    # Druhý uživatel přibude vedle prvního.
    c.delete(f"/api/akce/{EVENT}/zamek", json={"relace": "r1"})
    c.post(f"/api/akce/{EVENT}/zamek", json=R2)
    r = c.put(f"/api/akce/{EVENT}/metadata",
              json={"metadata": doc, "version": r.json["version"],
                    "relace": "r2"})
    stored = c.get(f"/api/akce/{EVENT}").json["metadata"]
    assert set(stored["upravili"]) == {"Spáčil, David", "Kopáčová, Jana"}
    assert c.get("/api/akce").json[0]["upravili"] == stored["upravili"]


def test_finish_writes_editors(client):
    c, _ = client
    _, version = saved(c)
    r = c.post(f"/api/akce/{EVENT}/dokoncit",
               json={"relace": "r1", "version": version})
    assert r.status_code == 200
    stored = c.get(f"/api/akce/{EVENT}").json["metadata"]
    assert list(stored["upravili"]) == ["Spáčil, David"]
