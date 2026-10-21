"""Alba dokončených akcí v Immichi a stav akcí ve pracovním adresáři.

Album akce vymezují assety spárované se soubory kořene akce kromě
označených k vyřazení (stejně jako hotovost). Album zakládá dokončení
akce (hlídač na pozadí) a pravidelná synchronizace ho udržuje:
chybějící assety doplní, cizí z alba odebere. Asset se nikdy
nemaže a album jen u akce trvale smazané z koše (`smazat_alba`) —
`file_key` navíc dofiltruje cizí akci se stejným
podřetězcem cesty.

Stav akce (`nacitani` | `rozpoznavani` | `rozpoznano` | `nenalezeno`)
je v `<work>/immich-alba.json` jako {akce: {album, stav, cas, chyba?}}
— atomický zápis pod zámkem v paměti, čtení funguje i bez Immiche.
Chyba spojení nebo 403 stav nemění, jen se zapíše do `chyba`.

Počty osob akce (pojm. | celkem) zjišťuje synchronizace a ukládá do
`<work>/immich-osoby.json` jako {akce: {pojmenovane, celkem, cas}};
skryté osoby se nepočítají.
"""

import json
import logging
import os
import tempfile
import threading
import time
import unicodedata
from datetime import datetime
from pathlib import Path

from . import immich
from .archive import is_metadata, is_skipped
from .immich import FRONTY_ML, HLIDAC_INTERVAL, HLIDAC_LIMIT, \
    ImmichError, file_key

log = logging.getLogger(__name__)

STAVY = ("nacitani", "rozpoznavani", "rozpoznano", "nenalezeno")
# Stavy, ve kterých album ještě nevzniklo; při chybě rozpoznání po
# jeho vzniku se naproti tomu stav ponechává.
PRED_ALBEM = ("nacitani", "nenalezeno")

NEMENIT = object()   # sentinel: položka záznamu se nechá tak, jak je


def _nfc(text):
    return unicodedata.normalize("NFC", text)


def _now():
    return datetime.now().isoformat(timespec="seconds")


# --- stav akcí -------------------------------------------------------------

class Stavy:
    """`<work>/immich-alba.json`; čtení a zápis fungují i bez Immiche."""

    def __init__(self, work):
        self.path = Path(work) / "immich-alba.json"
        self._lock = threading.Lock()

    def nacti(self):
        """Obsah souboru; poškozený nebo chybějící soubor = prázdný
        stav."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def polozka(self, akce):
        """Záznam akce {album, stav, cas, chyba?}, nebo None."""
        return self.nacti().get(akce)

    def nastav(self, akce, stav=None, album=NEMENIT, chyba=NEMENIT):
        """Read-modify-write pod zámkem; `chyba=None` položku smaže.

        `cas` se obnoví jen při změně záznamu; nezměněný zápis soubor
        nepřepíše. Vrací aktuální záznam akce.
        """
        with self._lock:
            data = self.nacti()
            entry = dict(data.get(akce) or {})
            if album is not NEMENIT:
                entry["album"] = album
            if chyba is None:
                entry.pop("chyba", None)
            elif chyba is not NEMENIT:
                entry["chyba"] = str(chyba)
            if stav is not None:
                entry["stav"] = stav
            old = data.get(akce)
            if old is not None and _bez_casu(old) == _bez_casu(entry):
                return dict(old, cas=old.get("cas"))
            entry.setdefault("album", None)
            entry["cas"] = _now()
            data[akce] = entry
            _zapsat(self.path, data)
            return entry

    def vyjmout(self, akce):
        """Odebere záznam akce a vrátí ho (None, když není); smazání
        akce do koše ho přenese do záznamu o smazání."""
        return _vyjmout(self, akce)

    def vlozit(self, akce, entry):
        """Vrátí záznam akce (obnovení z koše); None nic nedělá."""
        _vlozit(self, akce, entry)


def _bez_casu(entry):
    return {key: value for key, value in entry.items() if key != "cas"}


def _zapsat(path, data, prefix=".immich-alba-"):
    """Atomický zápis JSON (dočasný soubor + `os.replace`, jako
    `Settings.save`)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=prefix,
                               suffix=".tmp")
    try:
        os.chmod(tmp, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# --- počty osob ------------------------------------------------------------

class Osoby:
    """`<work>/immich-osoby.json` = {akce: {pojmenovane, celkem, cas}}.

    Počty zjišťuje synchronizace (`Sync.udrzet_alba`); čtení pro výpis
    akcí funguje i bez Immiche (stejně jako `Stavy`).
    """

    def __init__(self, work):
        self.path = Path(work) / "immich-osoby.json"
        self._lock = threading.Lock()

    def nacti(self):
        """Obsah souboru; poškozený nebo chybějící soubor = prázdný
        stav."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def polozka(self, akce):
        """Záznam akce {pojmenovane, celkem, cas}, nebo None."""
        return self.nacti().get(akce)

    def nastav(self, akce, pojmenovane, celkem):
        """Read-modify-write pod zámkem; vrátí zapsaný záznam."""
        with self._lock:
            data = self.nacti()
            entry = {"pojmenovane": pojmenovane, "celkem": celkem,
                     "cas": _now()}
            data[akce] = entry
            _zapsat(self.path, data, prefix=".immich-osoby-")
            return entry

    def vyjmout(self, akce):
        """Jako `Stavy.vyjmout`."""
        return _vyjmout(self, akce, prefix=".immich-osoby-")

    def vlozit(self, akce, entry):
        """Jako `Stavy.vlozit`."""
        _vlozit(self, akce, entry, prefix=".immich-osoby-")


def _vyjmout(store, akce, prefix=".immich-alba-"):
    """Read-modify-write pod zámkem `store`: odebere a vrátí záznam."""
    with store._lock:
        data = store.nacti()
        entry = data.pop(akce, None)
        if entry is not None:
            _zapsat(store.path, data, prefix=prefix)
        return entry


def _vlozit(store, akce, entry, prefix=".immich-alba-"):
    if entry is None:
        return
    with store._lock:
        data = store.nacti()
        data[akce] = entry
        _zapsat(store.path, data, prefix=prefix)


def pocty_osob(assets):
    """{pojmenovane, celkem} osob s obličejem v albu.

    `assets` je odpověď `search_album` (`withPeople`): každá osoba má
    `id`, `name`, `isHidden`. Skryté osoby se nepočítají, pojmenovaná
    = neprázdné `name`; stejná osoba na více assetech jednou. Čistá
    funkce bez I/O — používá ji synchronizace i nástroj pojmenování.
    """
    jmen = {}
    for asset in assets:
        for person in asset.get("people") or []:
            if not person.get("id") or person.get("isHidden"):
                continue
            jmen[person["id"]] = bool((person.get("name") or "").strip())
    return {"pojmenovane": sum(jmen.values()), "celkem": len(jmen)}


# --- alba akcí vysypaných z koše -------------------------------------------

class KosAlba:
    """`<work>/kos-alba.json` = {id alba: název akce}.

    Fronta alb akcí trvale smazaných z koše. Album se do ní zapíše před
    smazáním složky (vazba je jen v záznamu o smazání) a odebere se po
    smazání v Immichi; jinak počká na další vysypání.
    """

    def __init__(self, work):
        self.path = Path(work) / "kos-alba.json"
        self._lock = threading.Lock()

    def nacti(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def pridat(self, album_id, akce):
        with self._lock:
            data = self.nacti()
            data[album_id] = akce
            _zapsat(self.path, data, prefix=".kos-alba-")

    def odebrat(self, album_id):
        with self._lock:
            data = self.nacti()
            if data.pop(album_id, None) is not None:
                _zapsat(self.path, data, prefix=".kos-alba-")


def smazat_alba(client, fronta):
    """Smaže v Immichi alba z fronty `KosAlba`; vrací smazaná id.

    Jediné místo, kde aplikace maže album (akce vysypaná z koše);
    assety nemaže. Album, které už neexistuje (404), se z fronty
    odebere; jiná chyba ho tam nechá do dalšího vysypání.
    """
    smazana = []
    for album_id, akce in sorted(fronta.nacti().items()):
        try:
            client.delete_album(album_id)
        except ImmichError as e:
            if e.status != 404:
                log.warning("koš: smazání alba %s (%s) selhalo: %s",
                            album_id, akce, e)
                continue
        log.info("koš: smazáno album %s akce %s", album_id, akce)
        fronta.odebrat(album_id)
        smazana.append(album_id)
    return smazana


# --- obsah alba ------------------------------------------------------------

def soubory_k_albu(ws, akce):
    """Názvy souborů kořene akce, které patří do alba.

    Stejný výběr jako hotovost (`model.completeness`): soubory, které
    se počítají (ne sidecary, ne `Thumbs.db`), kromě označených
    k vyřazení. Kolize přípony `.ignored` = prázdný výběr.
    """
    try:
        path = ws.event_dir(akce)
        doc, _ = ws.load(akce)
    except KeyError:
        return set()
    soubory = (doc or {}).get("soubory") or {}
    jmen = set()
    with os.scandir(path) as it:
        for entry in it:
            if (entry.is_file() and not is_skipped(entry.name)
                    and not is_metadata(entry.name)
                    and not (soubory.get(entry.name) or {}).get("vyradit")):
                jmen.add(_nfc(entry.name))
    return jmen


def assety_akce(client, ws, akce):
    """(assety {soubor: asset}, názvy souborů patřících k albu).

    Filtr `originalPath` je podřetězec, proto se výsledek dofiltruje
    přes `file_key` — cizí akce se stejným podřetězcem cesty
    (např. `… Konference` vs `… Konference 2`) do alba nedostane.
    """
    cil = soubory_k_albu(ws, akce)
    found = {}
    if not cil:
        return found, cil
    slozka = _nfc(akce)
    for asset in client.search_path(akce):
        key = file_key(asset.get("originalPath") or "")
        if key and key[0] == slozka and key[1] in cil:
            found[key[1]] = asset
    return found, cil


def _dohledat_album(client, stavy, akce):
    """Album podle vazby ze stavů, pak podle názvu; None když není.

    Vazba ukazuje na smazané album (404) → hledá se podle názvu, aby
    nevzniklo duplicitní.
    """
    vazba = (stavy.polozka(akce) or {}).get("album")
    if vazba:
        try:
            return client.album(vazba)
        except ImmichError as e:
            if e.status != 404:
                raise
    for album in client.albums():
        if album.get("albumName") == akce:
            return album
    return None


def _rozpoznano(client, assets):
    """True, když mají všechny fotky zmenšeninu a fronty ML stojí.

    Immich nemá příznak „obličeje zpracovány“; detekce se zařazuje až
    po zmenšenině. Zmenšeninu pozná `thumbhash`: `resized` je od
    v1.113 deprecated a Immich 3.3 ho vrací `true` i u assetu bez
    zmenšeniny. Videa se nepočítají — bez zmenšeniny (selhaný ffmpeg)
    by stav nikdy nedoběhl a obličeje se v nich stejně nehledají.
    """
    if not all(asset.get("thumbhash") for asset in assets
               if asset.get("type") != "VIDEO"):
        return False
    for fronta in FRONTY_ML:
        statistics = (client.queue(fronta) or {}).get("statistics") or {}
        if statistics.get("active") or statistics.get("waiting"):
            return False
    return True


def udrzet_album(client, ws, stavy, akce):
    """Udrží album dokončené akce, zjistí rozpoznání a zapíše stav.

    Společné pro hlídače i pravidelnou synchronizaci. Immich-li fotky
    akce nezná, album se nezakládá a funkce vrátí None. Chyba Immiche
    stav nemění — jen se zapíše do `chyba`. Chybí-li oprávnění číst
    fronty (klíč bez role admin), album je udrženo a stav zůstane
    `rozpoznavani` s chybou. Vrací id alba, nebo None.
    """
    try:
        assets, _ = assety_akce(client, ws, akce)
    except ImmichError as e:
        stavy.nastav(akce, chyba=str(e))
        return None
    if not assets:
        return None                    # Immich fotky akce ještě nezná
    ids = sorted(asset["id"] for asset in assets.values())
    chybejici = ids
    try:
        album = _dohledat_album(client, stavy, akce)
        if album is None:
            album = client.create_album(akce, ids)
        else:
            clenove = set(client.album_asset_ids(album["id"]))
            chybejici = [i for i in ids if i not in clenove]
            cizi = [i for i in sorted(clenove) if i not in ids]
            if chybejici:
                client.add_album_assets(album["id"], chybejici)
            if cizi:
                # Cizi = v albu, ale ne mezi assety akce; maže se jen
                # odebrání z alba, nikdy asset nebo album jako celek.
                client.remove_album_assets(album["id"], cizi)
    except ImmichError as e:
        stavy.nastav(akce, chyba=str(e))
        return None
    pred = (stavy.polozka(akce) or {}).get("stav")
    try:
        # Fronty jsou společné celému Immichi: jednou zjištěné
        # rozpoznání nevrací cizí práce zpět, jen nové assety alba.
        if pred == "rozpoznano" and not chybejici:
            stav = "rozpoznano"
        else:
            stav = "rozpoznano" if _rozpoznano(client, assets.values()) \
                else "rozpoznavani"
        chyba = None
    except ImmichError as e:
        # 403 na frontu: rozpoznání nelze ověřit. Stav zůstane, leda
        # by šlo o období před albem (nacitani/nenalezeno).
        stav = pred if pred and pred not in PRED_ALBEM else "rozpoznavani"
        chyba = str(e)
    stavy.nastav(akce, stav=stav, album=album["id"], chyba=chyba)
    return album["id"]


# --- hlídač po dokončení ---------------------------------------------------

class Hlidac:
    """Hlídání dokončené akce: sken knihovny, album, rozpoznávání.

    Spouští ho `akce_finish` po úspěšném zveřejnění složky (a obnovení
    dokončené akce z koše) na pozadí (daemon); dokončení na Immich nečeká a chyba Immiche výsledek
    dokončení nezmění. Nejvýš jeden hlídač na akci — opakované
    dokončení ho pustí znovu a běžící se u dalšího kroku sám ukončí.
    Ve vývojovém režimu se sken nespouští (`.ignored` se tam
    neodebírá); kroky pro album a rozpoznání běží, když Immich fotky
    zná. Po `limit` bez jediného assetu zapíše `nenalezeno`, jinak
    nechá poslední stav a práci převezme pravidelná synchronizace.
    """

    def __init__(self, sync, interval=HLIDAC_INTERVAL, limit=HLIDAC_LIMIT):
        self.sync = sync
        self.interval = interval
        self.limit = limit
        self._lock = threading.Lock()
        self._generace = {}     # akce → číslo aktuálního hlídače
        self._nitka = set()

    def spust(self, akce):
        """Start na pozadí; bez nastaveného Immiche se nespouští."""
        if self.sync.settings.load() is None:
            return False
        with self._lock:
            self._generace[akce] = self._generace.get(akce, 0) + 1
            generace = self._generace[akce]
        nitka = threading.Thread(target=self._bez, args=(akce, generace),
                                 daemon=True, name="immich-hlidac")
        self._nitka.add(nitka)
        nitka.start()
        return True

    def zastavit(self, akce):
        """Běžící hlídač akce se u dalšího kroku ukončí (akce smazaná
        do koše; stav už ve `.work` není a nesmí se tam vrátit)."""
        with self._lock:
            if akce in self._generace:
                self._generace[akce] += 1

    def skenovat(self):
        """Jen sken knihovny na pozadí (dokončená akce smazaná do koše:
        Immich její assety hned označí offline). Ve vývojovém režimu
        a bez vybrané knihovny se nespouští."""
        nastaveni = self.sync.settings.load()
        if not self.sync.ws.zapis or not nastaveni \
                or not nastaveni.get("knihovna"):
            return False
        nitka = threading.Thread(target=self._sken,
                                 args=(nastaveni["knihovna"],),
                                 daemon=True, name="immich-sken")
        self._nitka.add(nitka)
        nitka.start()
        return True

    def _sken(self, knihovna):
        try:
            client = self.sync.client()
            if client is not None:
                client.scan_library(knihovna)
        except Exception:  # noqa: BLE001 — chyba Immiche nesmí měnit
            # výsledek smazání
            log.exception("immich: sken knihovny po smazání selhal")
        finally:
            self._nitka.discard(threading.current_thread())

    def cekat(self, timeout=10):
        """Počká na doběhnutí všech hlídačů; True, když doběhli."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not any(t.is_alive() for t in list(self._nitka)):
                return True
            time.sleep(min(0.02, max(0.001, deadline - time.monotonic())))
        return not any(t.is_alive() for t in list(self._nitka))

    def _bez(self, akce, generace):
        try:
            self._beh(akce, generace)
        except Exception:  # noqa: BLE001 — chyba Immiche nesmí měnit
            # výsledek ani odpověď dokončení akce
            log.exception("immich: hlídání %s selhalo", akce)
        finally:
            self._nitka.discard(threading.current_thread())

    def _beh(self, akce, generace):
        client = self.sync.client()
        if client is None:
            return
        ws, stavy = self.sync.ws, self.sync.alba
        do = time.monotonic() + self.limit
        nastaveni = self.sync.settings.load()
        if ws.zapis and nastaveni and nastaveni.get("knihovna"):
            try:
                client.scan_library(nastaveni["knihovna"])
                stavy.nastav(akce, stav="nacitani")
            except ImmichError as e:
                stavy.nastav(akce, chyba=str(e))
        minuly = None
        zname = 0
        videno = False     # aspoň jeden dotaz na assety proběhl bez chyby
        hotovo = False
        while True:
            assets, cil = None, set()
            try:
                assets, cil = assety_akce(client, ws, akce)
            except ImmichError as e:
                stavy.nastav(akce, chyba=str(e))
                assets = None
            if assets is not None:
                videno = True
                zname = max(zname, len(assets))
                if (cil and len(assets) >= len(cil)) or self._fronta_stoji(
                        client, len(assets), minuly):
                    hotovo = True
                    break
                minuly = len(assets)
            krok = self._pockat(akce, generace, do)
            if krok == "nahrazen":
                return
            if krok == "konec":
                break
        if not hotovo and not zname:
            # `nenalezeno` je pozitivní zjištění: Immich sice odpovídá,
            # ale žádný soubor akce nezná. Při chybách nic netvrdíme.
            if videno and self._zije(akce, generace):
                stavy.nastav(akce, stav="nenalezeno")
            return
        while self._zije(akce, generace) and time.monotonic() <= do:
            udrzet_album(client, ws, stavy, akce)
            if (stavy.polozka(akce) or {}).get("stav") == "rozpoznano":
                self.sync.trigger()
                return
            if self._pockat(akce, generace, do) != "pokracuj":
                return

    def _fronta_stoji(self, client, nalezeno, minuly):
        """Druhá podmínka hotovo: fronta `library` nemá aktivní ani
        čekající úlohu a počet nalezených se mezi dotazy nezměnil."""
        if not nalezeno or minuly is None or nalezeno != minuly:
            return False
        try:
            statistics = (client.queue("library") or {}).get(
                "statistics") or {}
        except ImmichError:
            return False
        return not statistics.get("active") and not statistics.get("waiting")

    def _zije(self, akce, generace):
        with self._lock:
            return self._generace.get(akce) == generace

    def _pockat(self, akce, generace, do):
        """Rozhodne po intervalu čekání: `pokracuj` | `konec` (limit)
        | `nahrazen` (nový hlídač)."""
        if not self._zije(akce, generace):
            return "nahrazen"
        zbyva = do - time.monotonic()
        if zbyva <= 0:
            return "konec"
        time.sleep(min(self.interval, zbyva))
        return "pokracuj"
