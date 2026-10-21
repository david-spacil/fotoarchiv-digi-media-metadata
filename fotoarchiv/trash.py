"""Koš smazaných akcí v archivu (`_kos.ignored`).

Smazání akce nic nemaže: celá složka akce se přesune do
`<archiv>/_kos.ignored/<ID>/` a vedle obsahu vznikne záznam
`_smazano.json` (název akce a složky, kdo, kdy, důvod a stav akce
vyjmutý z pracovního adresáře). Název koše nesplňuje vzor akce a má
příponu `.ignored`, takže ho seznam akcí, index i Immich přeskočí.

Obnovení vrátí složku pod původní název a stav do pracovního adresáře.
Vysypání trvale smaže akce, jejichž záznam je starší než `LHUTA`;
o stáří rozhoduje jen čas v záznamu, složka bez platného záznamu se
nikdy nesmaže. Jediné trvalé mazání v aplikaci.
"""

import json
import logging
import math
import os
import secrets
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from . import thumbs, xmp
from .albums import KosAlba
from .archive import IGNORED, Collision, is_metadata, is_skipped
from .importer import PROPOSALS
from .integrity import event_cache_path

log = logging.getLogger(__name__)

TRASH = "_kos.ignored"
RECORD = "_smazano.json"
SCHEMA = "fotoarchiv-kos/1"
LHUTA = timedelta(days=7)


class Refused(Exception):
    """Operaci koše nejde provést; `code` jde do odpovědi API."""

    def __init__(self, code, **info):
        super().__init__(code)
        self.code = code
        self.info = info


class Stav:
    """Stav akcí v pracovním adresáři, který se při smazání přenáší do
    záznamu: instance sdílené se serverem (vlastní zámky souborů)."""

    def __init__(self, ws, alba, osoby, odlozene):
        self.ws = ws
        self.alba = alba
        self.osoby = osoby
        self.odlozene = odlozene

    def _export(self, nazev):
        try:
            return json.loads(self.ws.export_record_path(nazev).read_bytes())
        except (FileNotFoundError, ValueError):
            return None

    def nahled(self, nazev):
        """Stav akce bez změny pracovního adresáře."""
        odlozene = {login: uzivatel[nazev] for login, uzivatel
                    in self.odlozene.nacti().items()
                    if isinstance(uzivatel, dict) and nazev in uzivatel}
        return _bez_prazdnych({"album": self.alba.polozka(nazev),
                               "osoby": self.osoby.polozka(nazev),
                               "odlozene": odlozene,
                               "export": self._export(nazev)})

    def vyjmout(self, nazev):
        """Odebere stav akce z pracovního adresáře a vrátí ho; cache
        kontroly a návrh skupin z importu zahodí."""
        stav = {"album": self.alba.vyjmout(nazev),
                "osoby": self.osoby.vyjmout(nazev),
                "odlozene": self.odlozene.vyjmout_akci(nazev),
                "export": self._export(nazev)}
        self.ws.export_record_path(nazev).unlink(missing_ok=True)
        event_cache_path(self.ws.work, nazev).unlink(missing_ok=True)
        (self.ws.work / PROPOSALS / f"{nazev}.json").unlink(missing_ok=True)
        return _bez_prazdnych(stav)

    def vlozit(self, nazev, stav):
        """Vrátí stav ze záznamu do pracovního adresáře."""
        stav = stav or {}
        self.alba.vlozit(nazev, stav.get("album"))
        self.osoby.vlozit(nazev, stav.get("osoby"))
        self.odlozene.vlozit_akci(nazev, stav.get("odlozene"))
        if stav.get("export") is not None:
            xmp.write_atomic(self.ws.export_record_path(nazev),
                             json.dumps(stav["export"]).encode("utf-8"))


def _bez_prazdnych(stav):
    return {k: v for k, v in stav.items() if v}


def root(ws):
    return ws.archiv / TRASH


def _now():
    return datetime.now().replace(microsecond=0)


def _new_dir(ws, now):
    while True:
        path = root(ws) / (now.strftime("%Y%m%dT%H%M%S") + "-"
                           + secrets.token_hex(2))
        if not os.path.lexists(path):
            return path


def _write_record(path, record):
    xmp.write_atomic(path / RECORD, (json.dumps(
        record, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        mode=0o644)


def purge_date(record):
    return datetime.fromisoformat(record["smazano"]) + LHUTA


def delete(ws, nazev, jmeno, duvod, stav, now=None):
    """Přesune akci do koše; vrátí {id, vysypat}.

    Ve vývojovém režimu jen plán ({id: None, cesta, vysypat}) bez
    zápisu. Neexistující akce vyhodí KeyError, kolize přípony Collision,
    selhání přesunu OSError (akce i pracovní adresář pak beze změny).
    Zámek akce drží volající.
    """
    now = now or _now()
    path = ws.event_dir(nazev)
    vysypat = (now + LHUTA).isoformat()
    if not ws.zapis:
        return {"id": None, "slozka": path.name,
                "cil": str(root(ws) / "<ID>"), "vysypat": vysypat}
    # Stav se z pracovního adresáře vyjme až po přesunu; do záznamu
    # před přesunem jde jeho kopie.
    record = {"schema": SCHEMA, "nazev": nazev, "slozka": path.name,
              "smazal": jmeno, "smazano": now.isoformat(), "duvod": duvod,
              "stav": stav.nahled(nazev)}
    root(ws).mkdir(exist_ok=True)
    dst = _new_dir(ws, now)
    _write_record(path, record)
    try:
        if os.path.lexists(dst):        # os.rename přepíše prázdnou složku
            raise FileExistsError(dst)
        os.rename(path, dst)
    except BaseException:
        (path / RECORD).unlink(missing_ok=True)
        raise
    # Až po přesunu: nepovedený přesun nechá pracovní adresář být.
    record["stav"] = stav.vyjmout(nazev)
    try:
        _write_record(dst, record)
    except OSError:
        # Zůstává záznam s kopií stavu zapsaný před přesunem.
        log.exception("koš: přepis záznamu %s selhal", dst.name)
    log.info("koš: %s smazal akci %s (%s) do %s, důvod: %s", jmeno, nazev,
             path.name, dst.name, duvod)
    return {"id": dst.name, "vysypat": vysypat}


def read_record(path):
    """Platný záznam o smazání ve složce koše, nebo None."""
    try:
        record = json.loads((path / RECORD).read_text(encoding="utf-8"))
        nazev, slozka = record["nazev"], record["slozka"]
        datetime.fromisoformat(record["smazano"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if record.get("schema") != SCHEMA or not isinstance(nazev, str) \
            or slozka not in (nazev, nazev + IGNORED) \
            or "/" in nazev or "\\" in nazev:
        return None
    return record


def _folders(ws):
    try:
        with os.scandir(root(ws)) as it:
            return sorted((e for e in it
                           if e.is_dir(follow_symlinks=False)),
                          key=lambda e: e.name, reverse=True)
    except FileNotFoundError:
        return []


def _count(path):
    """Počet souborů v kořeni jako v seznamu akcí."""
    with os.scandir(path) as it:
        return sum(1 for e in it if e.is_file() and e.name != RECORD
                   and not is_skipped(e.name) and not is_metadata(e.name))


def entries(ws, now=None):
    """Akce v koši, nejnověji smazané první.

    Položka: {id, nazev, smazal, smazano, duvod, souboru, vysypat,
    zbyva_dni}, složka bez platného záznamu {id, neznama: True}.
    """
    now = now or _now()
    result = []
    for entry in _folders(ws):
        path = Path(entry.path)
        record = read_record(path)
        if record is None:
            result.append({"id": entry.name, "neznama": True})
            continue
        vysypat = purge_date(record)
        result.append({
            "id": entry.name, "nazev": record["nazev"],
            "smazal": record.get("smazal"),
            "smazano": record["smazano"], "duvod": record.get("duvod"),
            "souboru": _count(path), "vysypat": vysypat.isoformat(),
            "zbyva_dni": max(0, math.ceil(
                (vysypat - now).total_seconds() / 86400))})
    result.sort(key=lambda e: (e.get("smazano") or "", e["id"]),
                reverse=True)
    return result


def _trashed(ws, id):
    if not isinstance(id, str) or "/" in id or "\\" in id \
            or id.startswith(".") or id in ("", ".."):
        raise KeyError(id)
    path = root(ws) / id
    if path.is_symlink() or not path.is_dir():
        raise KeyError(id)
    return path


def restore(ws, id, stav):
    """Vrátí akci z koše pod původní složku; vrátí název akce.

    Neznámé id vyhodí KeyError, složka bez záznamu Refused("neznama"),
    obsazený název Refused("obsazeno"). Zámek drží volající.
    """
    path = _trashed(ws, id)
    record = read_record(path)
    if record is None:
        raise Refused("neznama")
    nazev = record["nazev"]
    try:
        ws.event_dir(nazev)
    except Collision:
        raise Refused("obsazeno", nazev=nazev) from None
    except KeyError:
        pass
    else:
        raise Refused("obsazeno", nazev=nazev)
    dst = ws.archiv / record["slozka"]
    if os.path.lexists(dst) or os.path.lexists(ws.archiv / nazev) \
            or os.path.lexists(ws.archiv / (nazev + IGNORED)):
        raise Refused("obsazeno", nazev=nazev)
    os.rename(path, dst)
    stav.vlozit(nazev, record.get("stav"))
    (dst / RECORD).unlink(missing_ok=True)
    log.info("koš: obnovena akce %s z %s", nazev, id)
    return nazev


def _drop_thumbs(ws, path, slozka):
    """Smaže z cache náhledy souborů kořene (klíč z původní cesty,
    velikosti a mtime; přesun mtime nemění)."""
    cache = ws.work / "cache" / "thumbs"
    with os.scandir(path) as it:
        for entry in it:
            if not entry.is_file(follow_symlinks=False):
                continue
            key = thumbs.cache_key(ws.archiv / slozka / entry.name,
                                   entry.stat())
            for size in thumbs.SIZES:
                for suffix in (".jpg", ".failed"):
                    (cache / f"{key}-{size}{suffix}").unlink(missing_ok=True)


def due(ws, now=None):
    """Akce v koši, kterým uplynula lhůta: [(id, záznam)]."""
    now = now or _now()
    result = []
    for entry in _folders(ws):
        record = read_record(Path(entry.path))
        if record is not None and purge_date(record) <= now:
            result.append((entry.name, record))
    return result


def purge(ws, now=None, client=None):
    """Trvale smaže akce, kterým uplynula lhůta; vrátí jejich názvy.

    Ve vývojovém režimu nic nemaže. Album akce jde do fronty
    `KosAlba` před smazáním složky; s klientem Immiche (`client`) se
    pak fronta zpracuje. Selhání u jedné akce nezastaví ostatní.
    """
    if not ws.zapis:
        return []
    fronta = KosAlba(ws.work)
    smazane = []
    for id, record in due(ws, now):
        path = root(ws) / id
        try:
            album = ((record.get("stav") or {}).get("album") or {}) \
                .get("album")
            if album:
                fronta.pridat(album, record["nazev"])
            _drop_thumbs(ws, path, record["slozka"])
            # Záznam jako poslední: přerušené mazání dokončí další běh.
            with os.scandir(path) as it:
                for entry in it:
                    if entry.name == RECORD:
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        shutil.rmtree(entry.path)
                    else:
                        os.unlink(entry.path)
            (path / RECORD).unlink()
            path.rmdir()
        except OSError:
            log.exception("koš: vysypání %s (%s) selhalo", id,
                          record["nazev"])
            continue
        log.info("koš: trvale smazána akce %s (%s, smazal %s %s)",
                 record["nazev"], id, record.get("smazal"),
                 record["smazano"])
        smazane.append(record["nazev"])
    if client is not None and fronta.nacti():
        from .albums import smazat_alba
        smazat_alba(client, fronta)
    return smazane
