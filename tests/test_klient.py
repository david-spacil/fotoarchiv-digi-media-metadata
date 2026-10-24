"""Klient pro import z telefonu: logika bez UI proti podvrženému zdroji
a proti skutečnému serveru aplikace na localhostu."""

import hashlib
import io
import json
import shutil
import struct
import subprocess
import threading

import pytest
from cheroot import wsgi
from PIL import Image

from fotoarchiv import auth
from fotoarchiv.app import create_app
from klient import exif, gvfs, nahrani, server as srv
from klient.evidence import Evidence, Konfigurace
from klient.zdroj import Polozka, Zarizeni, Zdroj

pytestmark = pytest.mark.filterwarnings(
    "ignore::pytest.PytestUnraisableExceptionWarning")

ULOZISTE = "Interní sdílené úložiště"
CAMERA = f"{ULOZISTE}/DCIM/Camera"


class PodvrzenyZdroj(Zdroj):
    """Telefon v paměti: {cesta složky: {název: (bajty, datum)}}."""

    def __init__(self, slozky, zar=None, chyba=()):
        self.data = slozky
        self.zar = zar or Zarizeni("tel", "Telefon", (ULOZISTE,))
        self.chyba = set(chyba)  # názvy, jejichž čtení selže (odpojení)

    def zarizeni(self):
        return [self.zar]

    def slozky(self, zar, cesta):
        pre = cesta + "/" if cesta else ""
        return sorted({k[len(pre):].split("/")[0] for k in self.data
                       if k.startswith(pre) and k != cesta})

    def polozky(self, zar, cesta):
        for nazev, (obsah, datum) in self.data.get(cesta, {}).items():
            yield Polozka(cesta, nazev, len(obsah), datum)

    def otevrit(self, zar, polozka):
        if polozka.nazev in self.chyba:
            raise OSError("zařízení odpojeno")
        return io.BytesIO(self.data[polozka.slozka][polozka.nazev][0])


# --- EXIF náhled ----------------------------------------------------------

def jpeg(w=40, h=30, barva="red"):
    out = io.BytesIO()
    Image.new("RGB", (w, h), barva).save(out, "JPEG")
    return out.getvalue()


def s_nahledem(nahled, orientace=6, order="<"):
    """JPEG s APP1 Exif: IFD0 s orientací, IFD1 s náhledem."""
    bo = b"II" if order == "<" else b"MM"
    ifd0 = 8
    ifd1 = ifd0 + 2 + 12 + 4
    data_off = ifd1 + 2 + 2 * 12 + 4
    tiff = bo + struct.pack(order + "HI", 42, ifd0)
    tiff += struct.pack(order + "H", 1)
    tiff += struct.pack(order + "HHIHH", 0x0112, 3, 1, orientace, 0)
    tiff += struct.pack(order + "I", ifd1)
    tiff += struct.pack(order + "H", 2)
    tiff += struct.pack(order + "HHII", 0x0201, 4, 1, data_off)
    tiff += struct.pack(order + "HHII", 0x0202, 4, 1, len(nahled))
    tiff += struct.pack(order + "I", 0)
    tiff += nahled
    app1 = b"Exif\0\0" + tiff
    hlavni = jpeg(400, 300, "blue")
    return (b"\xff\xd8\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1
            + hlavni[2:])


@pytest.mark.parametrize("order", ["<", ">"])
def test_exif_nahled(order):
    maly = jpeg()
    data = s_nahledem(maly, 6, order)
    assert exif.nahled(data[:65536]) == (maly, 6)


def test_exif_bez_nahledu_a_useknuty():
    assert exif.nahled(jpeg()) == (None, 1)
    assert exif.nahled(b"\x00\x00ftypmp42") == (None, 1)
    data = s_nahledem(jpeg(), 3)
    assert exif.nahled(data[:60]) == (None, 1)


@pytest.mark.skipif(not shutil.which("exiftool"), reason="bez exiftool")
def test_exif_nahled_z_exiftoolu(tmp_path):
    """Druhá cesta: náhled vložený exiftoolem, ne vlastním sestavením."""
    foto, maly = tmp_path / "f.jpg", tmp_path / "t.jpg"
    foto.write_bytes(jpeg(400, 300))
    maly.write_bytes(jpeg(80, 60, "green"))
    subprocess.run(["exiftool", "-q", "-overwrite_original",
                    f"-ThumbnailImage<={maly}", "-Orientation#=8", str(foto)],
                   check=True)
    assert exif.nahled(foto.read_bytes()[:65536]) == (maly.read_bytes(), 8)


# --- gvfs ------------------------------------------------------------------

GIO = """\
Drive(1): Generic- SD/MMC/MS PRO
Volume(2): Pixel 8a
  Type: GProxyVolume (GProxyVolumeMonitorMTP)
  activation_root=mtp://Google_Pixel_8a_ABCDEFGH12/
  can_mount=1
Mount(1): mtp -> mtp://Google_Pixel_8a_ABCDEFGH12/
"""


def test_gio_svazky():
    assert gvfs.gio_svazky(GIO) == [
        ("Pixel 8a", "mtp://Google_Pixel_8a_ABCDEFGH12/")]


@pytest.fixture
def telefon(tmp_path):
    koren = tmp_path / "gvfs"
    dev = koren / "mtp:host=Google_Pixel_8a_ABCDEFGH12"
    cam = dev / ULOZISTE / "DCIM" / "Camera"
    cam.mkdir(parents=True)
    (dev / ULOZISTE / "DCIM" / "canon").mkdir()
    (cam / "PXL_20260101_120000000.MP.jpg").write_bytes(b"a" * 10)
    (cam / "PXL_20251231_080000000.mp4").write_bytes(b"v" * 5)
    (cam / ".trashed-1.jpg").mkdir()  # složka s příponou fotky
    (cam / "poznamka.txt").write_text("x")
    (koren / "smb-share:server=x").mkdir()
    (tmp_path / "zamceny").mkdir()
    (tmp_path / "zamceny" / "mtp:host=Zamceny_ABCDEFGH12").mkdir()
    return gvfs.Gvfs(koren, gio=False)


def test_gvfs_zarizeni_a_vypis(telefon):
    [zar] = telefon.zarizeni()
    assert zar.nazev == "Google Pixel 8a" and zar.uloziste == (ULOZISTE,)
    assert telefon.vychozi_slozka(zar) == CAMERA
    assert telefon.slozky(zar, f"{ULOZISTE}/DCIM") == ["Camera", "canon"]
    polozky = {p.nazev: p for p in telefon.polozky(zar, CAMERA)}
    assert set(polozky) == {"PXL_20260101_120000000.MP.jpg",
                            "PXL_20251231_080000000.mp4"}
    assert polozky["PXL_20251231_080000000.mp4"].typ == "video"
    p = polozky["PXL_20260101_120000000.MP.jpg"]
    assert telefon.hlavicka(zar, p, 4) == b"aaaa"
    with pytest.raises(ValueError):
        telefon.slozky(zar, f"{ULOZISTE}/../..")


def test_gvfs_zamceny_telefon(telefon, tmp_path):
    zdroj = gvfs.Gvfs(tmp_path / "zamceny", gio=False)
    [zar] = zdroj.zarizeni()
    assert zar.uloziste == () and zdroj.vychozi_slozka(zar) is None
    assert gvfs.Gvfs(tmp_path / "neni", gio=False).zarizeni() == []


def test_kopie_bez_zmeny_a_bez_prepsani(telefon, tmp_path):
    [zar] = telefon.zarizeni()
    p = next(p for p in telefon.polozky(zar, CAMERA) if p.typ == "foto")
    cil = tmp_path / "cil"
    cil.mkdir()
    kopie = telefon.kopirovat(zar, p, cil)
    assert kopie == cil / p.nazev and kopie.read_bytes() == b"a" * 10
    with pytest.raises(FileExistsError):
        telefon.kopirovat(zar, p, cil)


# --- konfigurace a evidence -------------------------------------------------

def test_evidence_rozlisuje_slozky(tmp_path):
    a = Polozka(CAMERA, "IMG_0001.jpg", 10, 1000.5)
    b = Polozka(f"{ULOZISTE}/DCIM/canon", "IMG_0001.jpg", 10, 1000.5)
    ev = Evidence(tmp_path)
    ev.pridat("tel", [a])
    ev2 = Evidence(tmp_path)
    assert ev2.je_nahrana("tel", a) and not ev2.je_nahrana("tel", b)
    assert not ev2.je_nahrana("jiny", a)


def test_konfigurace_bez_hesla(tmp_path):
    k = Konfigurace(tmp_path)
    k.nastavit_prihlaseni("https://foto.example", "prikladny")
    k.nastavit_slozku("tel", f"{ULOZISTE}/DCIM/canon")
    k2 = Konfigurace(tmp_path)
    assert (k2.server, k2.login) == ("https://foto.example", "prikladny")
    assert k2.slozka("tel") == f"{ULOZISTE}/DCIM/canon"
    assert "heslo" not in (tmp_path / "klient.json").read_text()


@pytest.mark.parametrize("text,ok", [
    ("https://foto.example/", "https://foto.example"),
    ("foto.example", "https://foto.example"),
    ("http://127.0.0.1:5000", "http://127.0.0.1:5000"),
    ("http://localhost:5000", "http://localhost:5000"),
    ("http://foto.example", None),
    ("ftp://foto.example", None),
])
def test_adresa_jen_https(text, ok):
    if ok is None:
        with pytest.raises(srv.Chyba):
            srv.adresa(text)
    else:
        assert srv.adresa(text) == ok


# --- nahrání proti serveru aplikace -----------------------------------------

USERS = {"prikladny": {"jmeno": "Příkladný, Daniel", "role": "admin"},
         "modelova": {"jmeno": "Modelová, Eva", "role": "archivar"}}
HESLO = "tajne-heslo-1"


@pytest.fixture
def aplikace(tmp_path):
    """Skutečný server cheroot s přihlášením; vrátí (app, url, work)."""
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    (work / "uzivatele.json").write_text(json.dumps(USERS),
                                         encoding="utf-8")
    hesla = auth.Passwords(work)
    for login in USERS:
        hesla.set(login, HESLO)
    app = create_app(archiv, work, zapis=False, prihlaseni=True)
    server = wsgi.Server(("127.0.0.1", 0), app)
    server.prepare()
    vlakno = threading.Thread(target=server.serve, daemon=True)
    vlakno.start()
    host, port = server.bind_addr
    yield app, f"http://{host}:{port}", work
    server.stop()
    vlakno.join(timeout=2)


def test_spatne_heslo(aplikace):
    _, url, _ = aplikace
    with pytest.raises(srv.Chyba) as e:
        srv.Server(url).prihlasit("prikladny", "spatne")
    assert e.value.kod == "neplatne"


def test_nahrani_vyberu(aplikace, tmp_path):
    app, url, work = aplikace
    fotky = {"PXL_20260101_120000000.MP.jpg": (jpeg(), 1767268800.4),
             "PXL_20260102_090000000.jpg": (jpeg(barva="green"), 1767344400),
             "PXL_20260103_090000000.jpg": (jpeg(barva="blue"), 1767430800)}
    zdroj = PodvrzenyZdroj({CAMERA: fotky},
                           chyba={"PXL_20260103_090000000.jpg"})
    zar = zdroj.zarizeni()[0]
    s = srv.Server(url)
    s.prihlasit("modelova", HESLO)
    ev = Evidence(tmp_path / "konfig")
    prenos = []
    vysledek = nahrani.nahrat(zdroj, zar, list(zdroj.polozky(zar, CAMERA)),
                              s, ev, prubeh=prenos.append)
    assert {p.nazev for p in vysledek.nahrane} == {
        "PXL_20260101_120000000.MP.jpg", "PXL_20260102_090000000.jpg"}
    assert [p.nazev for p, _ in vysledek.chyby] == [
        "PXL_20260103_090000000.jpg"]
    assert sum(prenos) == sum(len(fotky[p.nazev][0])
                              for p in vysledek.nahrane)
    for p in vysledek.nahrane:
        assert ev.je_nahrana(zar.id, p)
    assert not any(ev.je_nahrana(zar.id, p) for p, _ in vysledek.chyby)

    # Import patří uživateli; soubory bajtově shodné, mtime z data položky.
    c = app.test_client()
    c.post("/api/prihlaseni", json={"login": "modelova", "heslo": HESLO})
    prehled = c.get(f"/api/import/{vysledek.id}").json
    assert sorted(f["nazev"] for f in prehled["soubory"]) == sorted(
        p.nazev for p in vysledek.nahrane)
    soubory = list((work / "import" / vysledek.id).rglob("PXL_*"))
    assert len(soubory) == 2
    for f in soubory:
        obsah = fotky[f.name][0]
        assert hashlib.sha256(f.read_bytes()).digest() == \
            hashlib.sha256(obsah).digest()
        assert int(f.stat().st_mtime) == int(fotky[f.name][1])
    assert s.adresa_importu(vysledek.id) == f"{url}/#/import/{vysledek.id}"

    jiny = app.test_client()
    jiny.post("/api/prihlaseni", json={"login": "prikladny",
                                       "heslo": HESLO})
    assert jiny.get(f"/api/import/{vysledek.id}").status_code == 404


def test_stejne_jmeno_z_ruznych_slozek(aplikace, tmp_path):
    _, url, _ = aplikace
    zdroj = PodvrzenyZdroj({CAMERA: {"IMG_1.jpg": (b"a", 1)},
                            f"{ULOZISTE}/DCIM/canon": {"IMG_1.jpg": (b"b", 1)}})
    zar = zdroj.zarizeni()[0]
    polozky = [*zdroj.polozky(zar, CAMERA),
               *zdroj.polozky(zar, f"{ULOZISTE}/DCIM/canon")]
    s = srv.Server(url)
    s.prihlasit("modelova", HESLO)
    with pytest.raises(srv.Chyba) as e:
        nahrani.nahrat(zdroj, zar, polozky, s, Evidence(tmp_path))
    assert e.value.kod == "stejne_jmeno"


@pytest.mark.skipif(not shutil.which("exiftool"), reason="bez exiftool")
def test_server_prijme_fotku_s_polohou(aplikace, tmp_path):
    """Import na serveru beze změny: přehled a plán, poloha neodebraná."""
    app, url, _ = aplikace
    foto = tmp_path / "f.jpg"
    foto.write_bytes(jpeg(400, 300))
    subprocess.run(["exiftool", "-q", "-overwrite_original",
                    "-GPSLatitude=10.5", "-GPSLatitudeRef=N",
                    "-GPSLongitude=20.25", "-GPSLongitudeRef=E",
                    "-DateTimeOriginal=2026:01:01 12:00:00", str(foto)],
                   check=True)
    zdroj = PodvrzenyZdroj({CAMERA: {"PXL_1.jpg": (foto.read_bytes(),
                                                   1767268800)}})
    zar = zdroj.zarizeni()[0]
    s = srv.Server(url)
    s.prihlasit("modelova", HESLO)
    v = nahrani.nahrat(zdroj, zar, list(zdroj.polozky(zar, CAMERA)), s,
                       Evidence(tmp_path / "k"))
    assert not v.chyby
    c = app.test_client()
    c.post("/api/prihlaseni", json={"login": "modelova", "heslo": HESLO})
    prehled = c.get(f"/api/import/{v.id}").json
    assert prehled["odebrana_poloha"] == []
    assert prehled["od"] == "2026-01-01"
    r = c.post(f"/api/import/{v.id}/plan",
               json={"nova": "2026-01-01 Test klienta"})
    udalosti = [json.loads(r) for r in r.data.decode().splitlines()]
    assert udalosti[-1]["typ"] == "plan", udalosti[-1]


def test_typy_jako_import_aplikace():
    from fotoarchiv import cleanup, scan
    from klient import zdroj
    assert {e[1:] for e in zdroj.FOTKY | zdroj.VIDEA} == scan.MEDIA_EXT
    assert {e[1:] for e in zdroj.VIDEA} == scan.VIDEO_EXT
    assert {e[1:] for e in zdroj.RAWY} == cleanup.RAW_EXT
    assert zdroj.typ_media("PXL_1.HEIC") is None
