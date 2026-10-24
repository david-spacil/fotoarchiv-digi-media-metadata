"""Okno klienta bez displeje (offscreen) nad podvrženým stromem gvfs.
Běží jen tam, kde je PySide6 (`klient/.venv`)."""

import os
import time

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from klient.evidence import Evidence, Konfigurace  # noqa: E402
from klient.gvfs import Gvfs  # noqa: E402
from klient.ui import Okno  # noqa: E402

from .test_klient import ULOZISTE, jpeg, s_nahledem  # noqa: E402

HOST = "mtp:host=Google_Pixel_8a_ABCDEFGH12"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def cekat(app, podminka, limit=10):
    konec = time.monotonic() + limit
    while time.monotonic() < konec:
        app.processEvents()
        if podminka():
            return
        time.sleep(0.01)
    raise AssertionError("nesplněno")


@pytest.fixture
def okno(app, tmp_path):
    koren = tmp_path / "gvfs"
    cam = koren / HOST / ULOZISTE / "DCIM" / "Camera"
    canon = koren / HOST / ULOZISTE / "DCIM" / "canon"
    cam.mkdir(parents=True)
    canon.mkdir()
    soubory = [(cam / "PXL_20260101_120000000.MP.jpg", s_nahledem(jpeg()),
                1767268800),
               (cam / "PXL_20260102_090000000.jpg", jpeg(300, 200),
                1767344400),
               (cam / "PXL_20251231_080000000.mp4", b"\0" * 100,
                1767168000),
               (canon / "IMG_0001.JPG", jpeg(), 1767000000)]
    for cesta, obsah, cas in soubory:
        cesta.write_bytes(obsah)
        os.utime(cesta, (cas, cas))
    konf = Konfigurace(tmp_path / "konfig")
    ev = Evidence(tmp_path / "konfig")
    w = Okno(Gvfs(koren, gio=False), konf, ev)
    yield w, koren, konf, ev
    w.casovac.stop()
    w.model.pool.waitForDone()
    w.close()


def test_vypis_od_nejnovejsich_a_nahledy(app, okno):
    w, _, _, _ = okno
    assert w.volba_zar.currentText() == "Google Pixel 8a"
    cekat(app, lambda: w.vypis.isFinished() and len(w.model.polozky) == 3)
    assert w.slozka == f"{ULOZISTE}/DCIM/Camera"
    assert [p.nazev for p in w.model.polozky] == [
        "PXL_20260102_090000000.jpg", "PXL_20260101_120000000.MP.jpg",
        "PXL_20251231_080000000.mp4"]
    m = w.model
    for row in range(3):  # view by se ptal sám; offscreen bez vykreslení
        m.data(m.index(row), Qt.ItemDataRole.DecorationRole)

    def stav(nazev):
        p = next(p for p in m.polozky if p.nazev == nazev)
        return m._nahledy.get(tuple(p.klic))

    # EXIF náhled hned; fotka bez něj dopočítaná z celého souboru.
    cekat(app, lambda: isinstance(stav("PXL_20260101_120000000.MP.jpg"),
                                  QPixmap))
    cekat(app, lambda: isinstance(stav("PXL_20260102_090000000.jpg"),
                                  QPixmap))
    # Video bez ffmpeg-čitelného obsahu: zůstane zástupný náhled.
    cekat(app, lambda: stav("PXL_20251231_080000000.mp4") is False)


def test_vybrat_nove_a_jina_slozka(app, okno):
    w, koren, konf, ev = okno
    cekat(app, lambda: w.vypis.isFinished() and len(w.model.polozky) == 3)
    zar = w.zar
    ev.pridat(zar.id, [w.model.polozky[0]])
    w.model.obnovit_oznaceni()
    w._vybrat_nove()
    assert [p.nazev for p in w._vybrane()] == [
        "PXL_20260101_120000000.MP.jpg", "PXL_20251231_080000000.mp4"]
    assert w.souhrn.text().startswith("Vybráno 2")

    w.konf.nastavit_slozku(zar.id, f"{ULOZISTE}/DCIM/canon")
    w._otevrit(f"{ULOZISTE}/DCIM/canon")
    cekat(app, lambda: w.vypis.isFinished() and len(w.model.polozky) == 1)
    assert Konfigurace(konf.soubor.parent).slozka(zar.id) == \
        f"{ULOZISTE}/DCIM/canon"


def test_cekani_na_telefon(app, tmp_path):
    koren = tmp_path / "gvfs"
    koren.mkdir()
    w = Okno(Gvfs(koren, gio=False), Konfigurace(tmp_path / "k"),
             Evidence(tmp_path / "k"))
    try:
        assert w.stranky.currentWidget() is w.hlaska
        assert "Připojte telefon" in w.hlaska.text()
        (koren / HOST).mkdir()  # připojený, ale zamčený
        w._hlidat()
        assert "Odemkněte" in w.hlaska.text()
        cam = koren / HOST / ULOZISTE / "DCIM" / "Camera"
        cam.mkdir(parents=True)
        (cam / "PXL_1.jpg").write_bytes(jpeg())
        w._hlidat()
        assert w.stranky.currentWidget() is w.mrizka
        cekat(app, lambda: w.vypis.isFinished()
              and len(w.model.polozky) == 1)
    finally:
        w.casovac.stop()
        w.close()
