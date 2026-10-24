"""Okno klienta (PySide6): výběr telefonu a složky, mřížka náhledů
od nejnovějších, výběr, nahrání do importu aplikace."""

import bisect
import itertools
import shutil
import subprocess
import threading
import webbrowser
from datetime import datetime

from PySide6.QtCore import (QAbstractListModel, QBuffer, QByteArray,
                            QModelIndex, QObject, QRunnable, QSize, Qt,
                            QThread, QThreadPool, QTimer, Signal)
from PySide6.QtGui import (QColor, QFont, QImage, QImageReader, QPainter,
                           QPixmap, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog,
                               QDialogButtonBox, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListView, QMainWindow,
                               QMessageBox, QProgressDialog, QPushButton,
                               QStackedWidget, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget)

from . import exif, nahrani
from .server import Chyba, Server

NAHLED = 160
INTERVAL_ZARIZENI = 2000  # ms, hlídání připojení telefonu
PRIPOJIT_KAZDY = 5  # pokus o `gio mount` každé N-té hlídání

BEZ_TELEFONU = ("Připojte telefon kabelem, odemkněte ho a v oznámení "
                "„Nabíjení přes USB“ zvolte Přenos souborů.\n\n"
                "Klient na telefon čeká.")
ZAMCENY = ("Telefon je připojený, ale nezpřístupnil úložiště.\n\n"
           "Odemkněte ho a povolte přístup k datům (Přenos souborů).")


def velikost(n):
    for jednotka in ("B", "kB", "MB", "GB"):
        if n < 1000 or jednotka == "GB":
            return (f"{n:.0f} {jednotka}" if jednotka == "B"
                    else f"{n:.1f} {jednotka}".replace(".", ","))
        n /= 1000


def otocit(img, orientace):
    """Otočí náhled podle EXIF orientace 1–8."""
    if orientace in (2, 4, 5, 7):
        img = img.flipped(Qt.Orientation.Horizontal) \
            if hasattr(img, "flipped") else img.mirrored(True, False)
    uhel = {3: 180, 4: 180, 5: 270, 6: 90, 7: 90, 8: 270}.get(orientace)
    return img.transformed(QTransform().rotate(uhel)) if uhel else img


def zastupny(typ, nahrano=False):
    """Zástupný náhled, než se načte skutečný (nebo když není)."""
    pix = QPixmap(NAHLED, NAHLED * 3 // 4)
    pix.fill(QColor("#d8d8d8"))
    p = QPainter(pix)
    p.setPen(QColor("#666"))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter,
               {"video": "▶ video", "raw": "RAW"}.get(typ, "foto"))
    p.end()
    return s_oznacenim(pix) if nahrano else pix


def s_oznacenim(pix):
    """Náhled se štítkem „nahráno“."""
    pix = QPixmap(pix)
    p = QPainter(pix)
    p.fillRect(0, pix.height() - 22, pix.width(), 22, QColor(0, 110, 0, 200))
    p.setPen(QColor("white"))
    f = QFont()
    f.setBold(True)
    p.setFont(f)
    p.drawText(0, pix.height() - 22, pix.width(), 22,
               Qt.AlignmentFlag.AlignCenter, "✓ nahráno")
    p.end()
    return pix


# --- náhledy ---------------------------------------------------------------

class _Posel(QObject):
    hotovo = Signal(object, QImage, bool)  # klíč, obrázek, konečný


class NacteniNahledu(QRunnable):
    """Náhled z EXIF hlavičky; když v ní není (nebo `cely`), z celého
    souboru: fotka zmenšením, video prvním snímkem přes ffmpeg."""

    def __init__(self, zdroj, zar, polozka, posel, cely=False):
        super().__init__()
        self.zdroj, self.zar, self.p = zdroj, zar, polozka
        self.posel, self.cely = posel, cely

    def run(self):
        try:
            img = self._z_celeho() if self.cely else self._z_hlavicky()
        except Exception:  # odpojený telefon, poškozený soubor
            img = None
        if img is None and not self.cely:
            self.posel.hotovo.emit(tuple(self.p.klic), QImage(), False)
            return
        if img is not None and not img.isNull():
            img = img.scaled(NAHLED, NAHLED,
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        self.posel.hotovo.emit(tuple(self.p.klic), img or QImage(), True)

    def _z_hlavicky(self):
        if self.p.typ != "foto":
            return None
        jpeg, orientace = exif.nahled(self.zdroj.hlavicka(self.zar, self.p))
        if jpeg is None:
            return None
        img = QImage.fromData(jpeg)
        return None if img.isNull() else otocit(img, orientace)

    def _z_celeho(self):
        if self.p.typ == "video":
            cesta = self.zdroj.mistni_cesta(self.zar, self.p)
            if cesta is None or not shutil.which("ffmpeg"):
                return None
            out = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", str(cesta), "-frames:v", "1",
                 "-vf", f"scale={NAHLED * 2}:-2", "-f", "image2pipe",
                 "-vcodec", "mjpeg", "-"],
                capture_output=True, timeout=120).stdout
            return QImage.fromData(out) if out else None
        with self.zdroj.otevrit(self.zar, self.p) as f:
            data = QByteArray(f.read())  # QBuffer data nevlastní
        buf = QBuffer(data)
        reader = QImageReader(buf)
        reader.setAutoTransform(True)
        rozmer = reader.size()
        if rozmer.isValid():
            reader.setScaledSize(rozmer.scaled(
                NAHLED * 2, NAHLED * 2, Qt.AspectRatioMode.KeepAspectRatio))
        return reader.read()


# --- model -----------------------------------------------------------------

class Model(QAbstractListModel):
    """Položky jedné složky od nejnovějších; náhledy líně, jen pro
    položky, na které se view ptá (viditelné)."""

    def __init__(self, zdroj, evidence):
        super().__init__()
        self.zdroj, self.evidence = zdroj, evidence
        self.zar = None
        self.polozky, self._razeni = [], []
        # klíč → QPixmap, None (hlavička), "cely" (celý soubor), False
        self._nahledy = {}
        self._poradi = itertools.count()
        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(2)  # MTP stejně čte postupně
        self.posel = _Posel()
        self.posel.hotovo.connect(self._nahled_hotov)

    def vycistit(self, zar=None):
        self.pool.clear()
        self.beginResetModel()
        self.zar = zar
        self.polozky, self._razeni, self._nahledy = [], [], {}
        self.endResetModel()

    def pridat(self, polozky):
        for p in polozky:
            k = (-p.datum, p.nazev)
            i = bisect.bisect(self._razeni, k)
            self.beginInsertRows(QModelIndex(), i, i)
            self._razeni.insert(i, k)
            self.polozky.insert(i, p)
            self.endInsertRows()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.polozky)

    def je_nahrana(self, p):
        return self.evidence.je_nahrana(self.zar.id, p)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        p = self.polozky[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            d = datetime.fromtimestamp(p.datum)
            return f"{d.day}. {d.month}. {d.year} {d:%H:%M}"
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{p.nazev}\n{velikost(p.velikost)}"
        if role == Qt.ItemDataRole.DecorationRole:
            return self._nahled(p)
        return None

    def _nahled(self, p):
        k = tuple(p.klic)
        stav = self._nahledy.get(k)
        nahrano = self.je_nahrana(p)
        if isinstance(stav, QPixmap):
            return s_oznacenim(stav) if nahrano else stav
        if k not in self._nahledy:
            self._nahledy[k] = None  # načítá se z hlavičky
            self.pool.start(NacteniNahledu(self.zdroj, self.zar, p,
                                           self.posel),
                            next(self._poradi))
        return zastupny(p.typ, nahrano)

    def _nahled_hotov(self, k, img, konecny):
        if k not in self._nahledy:
            return  # mezitím jiná složka
        if not img.isNull():
            self._nahledy[k] = QPixmap.fromImage(img)
        elif konecny:
            self._nahledy[k] = False
        else:
            # Bez EXIF náhledu: zástupný hned, celý soubor na pozadí
            # (s nízkou prioritou, jen pro položky, které už byly vidět).
            self._nahledy[k] = "cely"
            p = next((p for p in self.polozky if tuple(p.klic) == k), None)
            if p is not None:
                self.pool.start(NacteniNahledu(self.zdroj, self.zar, p,
                                               self.posel, cely=True),
                                -next(self._poradi))
        for row, p in enumerate(self.polozky):
            if tuple(p.klic) == k:
                i = self.index(row)
                self.dataChanged.emit(i, i,
                                      [Qt.ItemDataRole.DecorationRole])
                break

    def obnovit_oznaceni(self):
        if self.polozky:
            self.dataChanged.emit(self.index(0),
                                  self.index(len(self.polozky) - 1))


class Vypis(QThread):
    """Výpis složky na pozadí (první výpis přes gvfs trvá desítky s)."""
    davka = Signal(list)
    chyba = Signal(str)

    def __init__(self, zdroj, zar, cesta):
        super().__init__()
        self.zdroj, self.zar, self.cesta = zdroj, zar, cesta
        self.zruseno = False

    def run(self):
        davka = []
        try:
            for p in self.zdroj.polozky(self.zar, self.cesta):
                if self.zruseno:
                    return
                davka.append(p)
                if len(davka) >= 50:
                    self.davka.emit(davka)
                    davka = []
            self.davka.emit(davka)
        except OSError as e:
            self.chyba.emit(str(e))


class Nahravani(QThread):
    prubeh = Signal(int)
    soubor = Signal(str, str)  # název, chyba ("" = nahráno)
    konec = Signal(object, str)  # Vysledek | None, chyba

    def __init__(self, zdroj, zar, polozky, server, evidence):
        super().__init__()
        self.args = (zdroj, zar, polozky, server, evidence)
        self.zruseno = threading.Event()

    def run(self):
        try:
            v = nahrani.nahrat(
                *self.args, prubeh=self.prubeh.emit,
                hotovo=lambda p, e: self.soubor.emit(p.nazev, e or ""),
                zruseno=self.zruseno.is_set)
        except Chyba as e:
            self.konec.emit(None, str(e))
            return
        self.konec.emit(v, "")


# --- dialogy ---------------------------------------------------------------

class VolbaSlozky(QDialog):
    """Strom složek telefonu, podsložky se načítají při rozbalení."""

    def __init__(self, zdroj, zar, aktualni, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Složka v telefonu")
        self.resize(420, 480)
        self.zdroj, self.zar = zdroj, zar
        self.strom = QTreeWidget()
        self.strom.setHeaderHidden(True)
        self.strom.itemExpanded.connect(self._rozbalit)
        self.strom.itemDoubleClicked.connect(lambda *_: self.accept())
        tlacitka = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                    | QDialogButtonBox.StandardButton.Cancel)
        tlacitka.accepted.connect(self.accept)
        tlacitka.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(self.strom)
        lay.addWidget(tlacitka)
        for ul in zar.uloziste:
            self.strom.addTopLevelItem(self._uzel(ul, ul))
        self._najit(aktualni or "")

    def _uzel(self, nazev, cesta):
        it = QTreeWidgetItem([nazev])
        it.setData(0, Qt.ItemDataRole.UserRole, cesta)
        it.setChildIndicatorPolicy(
            QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        return it

    def _rozbalit(self, it):
        if it.childCount() or it.data(0, Qt.ItemDataRole.UserRole + 1):
            return
        it.setData(0, Qt.ItemDataRole.UserRole + 1, True)
        cesta = it.data(0, Qt.ItemDataRole.UserRole)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            jmena = self.zdroj.slozky(self.zar, cesta)
        except OSError:
            jmena = []
        finally:
            QApplication.restoreOverrideCursor()
        for j in jmena:
            if not j.startswith("."):
                it.addChild(self._uzel(j, f"{cesta}/{j}"))
        if not it.childCount():
            it.setChildIndicatorPolicy(
                QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator)

    def _najit(self, cesta):
        """Rozbalí strom k aktuální složce a označí ji."""
        casti = cesta.split("/")
        uroven = [self.strom.topLevelItem(i)
                  for i in range(self.strom.topLevelItemCount())]
        it = None
        for n, c in enumerate(casti):
            it = next((u for u in uroven if u.text(0) == c), None)
            if it is None:
                return
            if n < len(casti) - 1:
                it.setExpanded(True)
                uroven = [it.child(i) for i in range(it.childCount())]
        if it is not None:
            self.strom.setCurrentItem(it)

    def cesta(self):
        it = self.strom.currentItem()
        return it.data(0, Qt.ItemDataRole.UserRole) if it else None


class Prihlaseni(QDialog):
    def __init__(self, server, login, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Přihlášení do Fotoarchivu")
        self.server = QLineEdit(server)
        self.server.setPlaceholderText("https://…")
        self.login = QLineEdit(login)
        self.heslo = QLineEdit()
        self.heslo.setEchoMode(QLineEdit.EchoMode.Password)
        self.chyba = QLabel()
        self.chyba.setStyleSheet("color: #b00")
        self.chyba.setWordWrap(True)
        form = QFormLayout(self)
        form.addRow("Server", self.server)
        form.addRow("Login", self.login)
        form.addRow("Heslo", self.heslo)
        form.addRow(self.chyba)
        tlacitka = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                    | QDialogButtonBox.StandardButton.Cancel)
        tlacitka.accepted.connect(self.accept)
        tlacitka.rejected.connect(self.reject)
        form.addRow(tlacitka)
        (self.heslo if server and login else self.server).setFocus()


# --- hlavní okno -----------------------------------------------------------

class Okno(QMainWindow):
    def __init__(self, zdroj, konfigurace, evidence):
        super().__init__()
        self.setWindowTitle("Fotoarchiv – import z telefonu")
        self.resize(1000, 720)
        self.zdroj, self.konf, self.evidence = zdroj, konfigurace, evidence
        self.zar, self.slozka, self.vypis = None, None, None
        self._bezici = set()  # vlákna výpisu, dokud neskončí
        self.server = None
        self._hlidani = 0

        self.volba_zar = QComboBox()
        self.volba_zar.currentIndexChanged.connect(self._zvolit_zarizeni)
        self.tl_slozka = QPushButton("Jiná složka…")
        self.tl_slozka.clicked.connect(self._jina_slozka)
        self.popis_slozky = QLabel()
        horni = QHBoxLayout()
        horni.addWidget(QLabel("Telefon:"))
        horni.addWidget(self.volba_zar)
        horni.addSpacing(16)
        horni.addWidget(self.popis_slozky, 1)
        horni.addWidget(self.tl_slozka)

        self.model = Model(zdroj, evidence)
        self.mrizka = QListView()
        self.mrizka.setViewMode(QListView.ViewMode.IconMode)
        self.mrizka.setResizeMode(QListView.ResizeMode.Adjust)
        self.mrizka.setMovement(QListView.Movement.Static)
        self.mrizka.setUniformItemSizes(True)
        self.mrizka.setIconSize(QSize(NAHLED, NAHLED))
        self.mrizka.setGridSize(QSize(NAHLED + 16, NAHLED + 36))
        self.mrizka.setSelectionMode(
            QListView.SelectionMode.ExtendedSelection)
        self.mrizka.setModel(self.model)
        self.mrizka.selectionModel().selectionChanged.connect(
            self._vyber_zmenen)

        self.hlaska = QLabel(BEZ_TELEFONU)
        self.hlaska.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hlaska.setWordWrap(True)
        self.stranky = QStackedWidget()
        self.stranky.addWidget(self.hlaska)
        self.stranky.addWidget(self.mrizka)

        self.tl_nove = QPushButton("Vybrat nové")
        self.tl_nove.clicked.connect(self._vybrat_nove)
        self.tl_zrusit = QPushButton("Zrušit výběr")
        self.tl_zrusit.clicked.connect(self.mrizka.clearSelection)
        self.souhrn = QLabel()
        self.tl_nahrat = QPushButton("Nahrát do Fotoarchivu…")
        self.tl_nahrat.clicked.connect(self._nahrat)
        dolni = QHBoxLayout()
        dolni.addWidget(self.tl_nove)
        dolni.addWidget(self.tl_zrusit)
        dolni.addWidget(self.souhrn, 1)
        dolni.addWidget(self.tl_nahrat)

        stred = QWidget()
        lay = QVBoxLayout(stred)
        lay.addLayout(horni)
        lay.addWidget(self.stranky, 1)
        lay.addLayout(dolni)
        self.setCentralWidget(stred)

        self.casovac = QTimer(self)
        self.casovac.timeout.connect(self._hlidat)
        self.casovac.start(INTERVAL_ZARIZENI)
        self._hlidat()
        self._vyber_zmenen()

    # zařízení a složky

    def _hlidat(self):
        """Hlídá připojení telefonu; bez něj zkusí `gio mount`."""
        zarizeni = self.zdroj.zarizeni()
        self._hlidani += 1
        if not zarizeni and self._hlidani % PRIPOJIT_KAZDY == 1 \
                and hasattr(self.zdroj, "pripojit"):
            if self.zdroj.pripojit():
                zarizeni = self.zdroj.zarizeni()
        stavajici = [self.volba_zar.itemData(i)
                     for i in range(self.volba_zar.count())]
        if zarizeni == stavajici:
            return
        zvolene = self.zar.id if self.zar else None
        self.volba_zar.blockSignals(True)
        self.volba_zar.clear()
        for z in zarizeni:
            self.volba_zar.addItem(z.nazev, z)
        i = next((i for i, z in enumerate(zarizeni) if z.id == zvolene), 0)
        self.volba_zar.setCurrentIndex(i if zarizeni else -1)
        self.volba_zar.blockSignals(False)
        self._zvolit_zarizeni()

    def _zvolit_zarizeni(self, *_):
        zar = self.volba_zar.currentData()
        if zar == self.zar:
            return
        stejne = zar is not None and self.zar is not None \
            and zar.id == self.zar.id
        self.zar = zar
        if zar is None:
            self._zastavit_vypis()
            self.model.vycistit()
            self._ukazat(BEZ_TELEFONU)
        elif not zar.uloziste:
            self._zastavit_vypis()
            self.model.vycistit()
            self._ukazat(ZAMCENY)
        elif not stejne or not self.model.polozky:
            slozka = self.konf.slozka(zar.id)
            if not slozka or slozka.split("/")[0] not in zar.uloziste:
                slozka = self.zdroj.vychozi_slozka(zar)
            self._otevrit(slozka)

    def _ukazat(self, text):
        self.hlaska.setText(text)
        self.stranky.setCurrentWidget(self.hlaska)
        self.popis_slozky.setText("")
        self.tl_slozka.setEnabled(False)
        self._vyber_zmenen()

    def _zastavit_vypis(self):
        if self.vypis is not None:
            self.vypis.zruseno = True
            self.vypis.davka.disconnect()
            self.vypis.chyba.disconnect()
            self.vypis = None

    def _otevrit(self, slozka):
        self._zastavit_vypis()
        self.slozka = slozka
        self.model.vycistit(self.zar)
        self.stranky.setCurrentWidget(self.mrizka)
        self.tl_slozka.setEnabled(True)
        self.popis_slozky.setText(f"Načítám {slozka}…")
        self.vypis = Vypis(self.zdroj, self.zar, slozka)
        self.vypis.davka.connect(self._davka)
        self.vypis.chyba.connect(self._chyba_vypisu)
        self.vypis.finished.connect(self._vypis_hotov)
        self._bezici.add(self.vypis)
        self.vypis.start()

    def _davka(self, polozky):
        self.model.pridat(polozky)
        self.popis_slozky.setText(
            f"Načítám {self.slozka}… {len(self.model.polozky)}")

    def _vypis_hotov(self):
        self._bezici.discard(self.sender())
        if self.sender() is not self.vypis:
            return
        n = len(self.model.polozky)
        self.popis_slozky.setText(f"{self.slozka} · {n} fotek a videí")
        self._vyber_zmenen()

    def _chyba_vypisu(self, zprava):
        self.popis_slozky.setText(f"{self.slozka}: nejde přečíst")
        QMessageBox.warning(self, "Výpis složky",
                            f"Složku {self.slozka} nejde přečíst. "
                            f"Je telefon připojený a odemčený?\n\n{zprava}")

    def _jina_slozka(self):
        d = VolbaSlozky(self.zdroj, self.zar, self.slozka, self)
        if d.exec() and d.cesta() and d.cesta() != self.slozka:
            self.konf.nastavit_slozku(self.zar.id, d.cesta())
            self._otevrit(d.cesta())

    # výběr

    def _vybrane(self):
        return [self.model.polozky[i.row()]
                for i in sorted(self.mrizka.selectionModel().selectedIndexes(),
                                key=lambda i: i.row())]

    def _vyber_zmenen(self, *_):
        vybrane = self._vybrane()
        nove = sum(1 for p in self.model.polozky
                   if not self.model.je_nahrana(p)) if self.zar else 0
        self.souhrn.setText(
            f"Vybráno {len(vybrane)} ({velikost(sum(p.velikost for p in vybrane))})"
            f" · nových {nove}")
        self.tl_nahrat.setEnabled(bool(vybrane))
        self.tl_nove.setEnabled(bool(nove))
        self.tl_zrusit.setEnabled(bool(vybrane))

    def _vybrat_nove(self):
        sel = self.mrizka.selectionModel()
        sel.clearSelection()
        for row, p in enumerate(self.model.polozky):
            if not self.model.je_nahrana(p):
                sel.select(self.model.index(row),
                           sel.SelectionFlag.Select)

    # nahrání

    def _prihlasit(self):
        """Přihlásí se (heslo jen pro tuto relaci); vrátí Server."""
        if self.server is not None:
            return self.server
        d = Prihlaseni(self.konf.server, self.konf.login, self)
        while d.exec():
            try:
                server = Server(d.server.text())
                server.prihlasit(d.login.text().strip(), d.heslo.text())
            except Chyba as e:
                d.chyba.setText(str(e))
                continue
            self.konf.nastavit_prihlaseni(server.url, d.login.text().strip())
            self.server = server
            return server
        return None

    def _nahrat(self):
        vybrane = self._vybrane()
        server = self._prihlasit()
        if not vybrane or server is None:
            return
        celkem = sum(p.velikost for p in vybrane)
        self.prubeh = QProgressDialog(
            f"Nahrávám {len(vybrane)} souborů ({velikost(celkem)})…",
            "Přerušit", 0, 1000, self)
        self.prubeh.setWindowTitle("Nahrávání")
        self.prubeh.setWindowModality(Qt.WindowModality.WindowModal)
        self.prubeh.setMinimumDuration(0)
        self._preneseno = 0
        uloha = Nahravani(self.zdroj, self.zar, vybrane, server,
                          self.evidence)

        def pribylo(n):
            self._preneseno += n
            self.prubeh.setValue(min(999, self._preneseno * 1000
                                     // max(1, celkem)))
        uloha.prubeh.connect(pribylo)
        uloha.soubor.connect(lambda *_: self.model.obnovit_oznaceni())
        uloha.konec.connect(self._nahrano)
        self.prubeh.canceled.connect(uloha.zruseno.set)
        self.uloha = uloha
        uloha.start()

    def _nahrano(self, vysledek, chyba):
        self.prubeh.reset()
        self.model.obnovit_oznaceni()
        self._vyber_zmenen()
        if "vypršelo" in chyba or vysledek is not None and any(
                "vypršelo" in e for _, e in vysledek.chyby):
            self.server = None  # příště znovu přihlásit
        if vysledek is None:
            QMessageBox.warning(self, "Nahrávání", chyba)
            return
        if vysledek.chyby:
            seznam = "\n".join(f"{p.nazev}: {e}"
                               for p, e in vysledek.chyby[:20])
            QMessageBox.warning(
                self, "Nahrávání",
                f"Nahráno {len(vysledek.nahrane)}, "
                f"nenahráno {len(vysledek.chyby)}:\n\n{seznam}")
        if vysledek.nahrane:
            self.mrizka.clearSelection()
            webbrowser.open(self.uloha.args[3].adresa_importu(vysledek.id))
