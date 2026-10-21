import io
import json
import zipfile
from urllib.parse import unquote

import pytest

from fotoarchiv import download, xmp
from fotoarchiv.app import create_app
from fotoarchiv.archive import SCHEMA
from .conftest import make_tree, snapshot
from .test_app import R1, login_app, logged_in  # noqa: F401

EVENT = "2026-04-28 kontrola Naučné stezky"


def doc(**files):
    return {"schema": SCHEMA, "akce": {}, "skupiny": {},
            "soubory": {name: dict({"skupina": "s"}, **record)
                        for name, record in files.items()}}


def make(tmp_path, monkeypatch, metadata=None, folder=EVENT, zapis=False):
    """(klient, archiv, work) s akcí `a.jpg`, `b.jpg`, `c.mp4`, RAWem
    v podsložce a jiným souborem v kořeni."""
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    make_tree(archiv, {f"{folder}/": {"a.jpg": "aaa", "b.jpg": "bbb",
                                      "c.mp4": "0123456789",
                                      "pozn.txt": "x",
                                      "RAW.ignored/": {"a.CR2": "raw"}},
                       "2026-04-29 jina/": {"x.jpg": "x"}})
    work = tmp_path / "work"
    if metadata is not None:
        target = archiv / folder if zapis else work / "metadata" / EVENT
        target.mkdir(parents=True, exist_ok=True)
        (target / "_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr("fotoarchiv.scan.run_exiftool", lambda d, n: {})
    app = create_app(archiv, work, zapis, prihlaseni=False)
    app.testing = True
    return app.test_client(), archiv, work


def unzip(r):
    assert r.status_code == 200, r.data[:200]
    assert r.mimetype == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(r.data))
    assert zf.testzip() is None
    return {i.filename: zf.read(i) for i in zf.infolist()}


def filename(r):
    """Název přílohy z `Content-Disposition` (UTF-8, jinak ASCII)."""
    value = r.headers["Content-Disposition"]
    assert value.startswith("attachment;")
    if "filename*=UTF-8''" in value:
        return unquote(value.split("filename*=UTF-8''")[1])
    return value.split("filename=")[1].strip('"')


# --- streamovaný ZIP -------------------------------------------------------

def test_stream_reads_files_and_bytes(tmp_path):
    big = bytes(range(256)) * 9000  # víc než jeden blok
    (tmp_path / "v.mp4").write_bytes(big)
    (tmp_path / "č.jpg").write_bytes(b"jpg")
    chunks = list(download.stream([("v.mp4", tmp_path / "v.mp4"),
                                   ("č.jpg", tmp_path / "č.jpg"),
                                   ("x.xmp", "<x/>".encode())]))
    assert len(chunks) > 2 and all(chunks)
    zf = zipfile.ZipFile(io.BytesIO(b"".join(chunks)))
    assert zf.namelist() == ["v.mp4", "č.jpg", "x.xmp"]
    assert zf.read("v.mp4") == big and zf.read("č.jpg") == b"jpg"
    assert all(i.compress_type == zipfile.ZIP_STORED for i in zf.infolist())


def test_stream_skips_vanished_file(tmp_path):
    for name in ("a.jpg", "b.jpg"):
        (tmp_path / name).write_bytes(name.encode())
    chunks = download.stream([("a.jpg", tmp_path / "a.jpg"),
                              ("b.jpg", tmp_path / "b.jpg")])
    first = next(chunks)
    (tmp_path / "b.jpg").unlink()  # souběžný úklid po startu
    zf = zipfile.ZipFile(io.BytesIO(first + b"".join(chunks)))
    assert zf.testzip() is None
    assert zf.namelist() == ["a.jpg"]


def test_stream_zip64(tmp_path, monkeypatch):
    # Hranice zip64 snížená, ať test nepotřebuje soubor nad 4 GiB.
    monkeypatch.setattr(zipfile, "ZIP64_LIMIT", 100)
    (tmp_path / "v.mp4").write_bytes(b"v" * 1000)
    data = b"".join(download.stream([("v.mp4", tmp_path / "v.mp4")]))
    monkeypatch.undo()
    assert b"PK\x06\x06" in data  # konec centrálního adresáře zip64
    zf = zipfile.ZipFile(io.BytesIO(data))
    assert zf.read("v.mp4") == b"v" * 1000
    assert zf.getinfo("v.mp4").external_attr >> 16 == 0o644


def test_selection_name():
    assert download.selection_name("A", 1) == "A (1 soubor).zip"
    assert download.selection_name("A", 3) == "A (3 soubory).zip"
    assert download.selection_name("A", 12) == "A (12 souborů).zip"


def test_attachment_keeps_diacritics():
    value = download.attachment("Akce (5 souborů).zip")
    assert value == ('attachment; filename="Akce (5 souboru).zip"; '
                     "filename*=UTF-8''Akce%20%285%20soubor%C5%AF%29.zip")
    assert download.attachment('a"b.zip') == 'attachment; filename="ab.zip"'


# --- originál ------------------------------------------------------------

def test_original_attachment(tmp_path, monkeypatch):
    c, archiv, _ = make(tmp_path, monkeypatch)
    (archiv / EVENT / "č.jpg").write_bytes(b"orig")
    url = f"/api/akce/{EVENT}/soubor"
    inline = c.get(f"{url}/a.jpg").headers["Content-Disposition"]
    assert inline.startswith("inline")  # lupa
    r = c.get(f"{url}/a.jpg?stahnout=1")
    assert filename(r) == "a.jpg" and r.data == b"aaa"
    r = c.get(f"{url}/č.jpg?stahnout=1")
    assert filename(r) == "č.jpg" and r.data == b"orig"
    for name in ("RAW.ignored%2Fa.CR2", "..%2F2026-04-29%20jina%2Fx.jpg",
                 "pozn.txt"):
        assert c.get(f"{url}/{name}?stahnout=1").status_code == 404


# --- ZIP akce --------------------------------------------------------------

def test_event_zip(tmp_path, monkeypatch):
    meta = doc(**{"a.jpg": {"popis": "Most přes Svratku"},
                  "b.jpg": {"vyradit": True}, "c.mp4": {}})
    c, archiv, work = make(tmp_path, monkeypatch, meta)
    before = snapshot(tmp_path)
    r = c.get(f"/api/akce/{EVENT}/zip")
    files = unzip(r)
    assert filename(r) == f"{EVENT}.zip"
    assert sorted(files) == ["_metadata.json", "a.jpg", "a.jpg.xmp",
                             "c.mp4", "c.mp4.xmp"]
    assert files["a.jpg"] == b"aaa" and files["c.mp4"] == b"0123456789"
    assert files["_metadata.json"] == (
        work / "metadata" / EVENT / "_metadata.json").read_bytes()
    assert "Most přes Svratku" in files["a.jpg.xmp"].decode()
    assert files["a.jpg.xmp"].decode() == xmp.sidecar(meta, EVENT, "a.jpg")
    assert not (work / "xmp").exists()  # sidecary nikdy exportovány
    assert snapshot(tmp_path) == before


def test_event_zip_after_export_change(tmp_path, monkeypatch):
    meta = doc(**{"a.jpg": {"popis": "Starý"}})
    c, archiv, work = make(tmp_path, monkeypatch, meta, zapis=True)
    (archiv / EVENT / "a.jpg.xmp").write_text("starý sidecar")
    path = archiv / EVENT / "_metadata.json"
    meta["soubory"]["a.jpg"]["popis"] = "Nový"
    path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    files = unzip(c.get(f"/api/akce/{EVENT}/zip"))
    assert "Nový" in files["a.jpg.xmp"].decode()
    assert "a.jpg.xmp.xmp" not in files
    assert (archiv / EVENT / "a.jpg.xmp").read_text() == "starý sidecar"


def test_event_zip_without_metadata(tmp_path, monkeypatch):
    c, _, _ = make(tmp_path, monkeypatch)
    files = unzip(c.get(f"/api/akce/{EVENT}/zip"))
    assert sorted(files) == ["a.jpg", "b.jpg", "c.mp4"]


def test_event_zip_nfd_names(tmp_path, monkeypatch):
    import unicodedata
    nfd = unicodedata.normalize("NFD", "č.jpg")
    meta = doc(**{"č.jpg": {"vyradit": True}, "a.jpg": {}})
    c, archiv, _ = make(tmp_path, monkeypatch, meta)
    (archiv / EVENT / nfd).write_bytes(b"x")
    files = unzip(c.get(f"/api/akce/{EVENT}/zip"))
    assert nfd not in files and "č.jpg" not in files


def test_hidden_event_zip(tmp_path, monkeypatch):
    meta = doc(**{"a.jpg": {}})
    c, _, _ = make(tmp_path, monkeypatch, meta, folder=f"{EVENT}.ignored",
                   zapis=True)
    r = c.get(f"/api/akce/{EVENT}/zip")
    assert "a.jpg.xmp" in unzip(r)
    assert filename(r) == f"{EVENT}.zip"
    assert c.get(f"/api/akce/{EVENT}.ignored/zip").status_code == 404


def test_zip_unauthenticated(login_app):  # noqa: F811
    app, archiv = login_app
    event = "2026-04-28 kontrola"
    c = app.test_client()
    assert c.get(f"/api/akce/{event}/zip").status_code == 401
    r = c.post(f"/api/akce/{event}/zip",
               data={"soubory": ["IMG-20260428-WA0001.jpg"]})
    assert r.status_code == 401
    r = logged_in(app, "modelova").get(f"/api/akce/{event}/zip")
    assert sorted(unzip(r)) == ["IMG-20260428-WA0001.jpg"]


# --- ZIP výběru ------------------------------------------------------------

def test_selection_zip(tmp_path, monkeypatch):
    meta = doc(**{"a.jpg": {}, "b.jpg": {"vyradit": True}, "c.mp4": {}})
    c, _, _ = make(tmp_path, monkeypatch, meta)
    before = snapshot(tmp_path)
    url = f"/api/akce/{EVENT}/zip"
    r = c.post(url, data={"soubory": ["a.jpg", "b.jpg", "a.jpg"]})
    files = unzip(r)
    assert sorted(files) == ["_metadata.json", "a.jpg", "a.jpg.xmp",
                             "b.jpg", "b.jpg.xmp"]
    assert filename(r) == f"{EVENT} (2 soubory).zip"
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("bad", ["../2026-04-29 jina/x.jpg",
                                 "RAW.ignored/a.CR2", "pozn.txt",
                                 "neni.jpg", "_metadata.json"])
def test_selection_invalid_name(tmp_path, monkeypatch, bad):
    c, _, _ = make(tmp_path, monkeypatch, doc(**{"a.jpg": {}}))
    r = c.post(f"/api/akce/{EVENT}/zip", data={"soubory": ["a.jpg", bad]})
    assert r.status_code == 404
    assert r.mimetype != "application/zip"


def test_selection_empty(tmp_path, monkeypatch):
    c, _, _ = make(tmp_path, monkeypatch)
    assert c.post(f"/api/akce/{EVENT}/zip", data={}).status_code == 400


def test_download_ignores_foreign_lock(tmp_path, monkeypatch):
    c, _, _ = make(tmp_path, monkeypatch, doc(**{"a.jpg": {}}))
    assert c.post(f"/api/akce/{EVENT}/zamek", json=R1).status_code == 200
    lock = c.get(f"/api/akce/{EVENT}/zamek").json
    unzip(c.get(f"/api/akce/{EVENT}/zip"))
    unzip(c.post(f"/api/akce/{EVENT}/zip", data={"soubory": ["a.jpg"]}))
    assert c.get(f"/api/akce/{EVENT}/soubor/a.jpg?stahnout=1").data == b"aaa"
    assert c.get(f"/api/akce/{EVENT}/zamek").json == lock
