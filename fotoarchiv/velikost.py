"""Velikost akcí a položek koše „k datu“ (`.work/velikosti.json`).

Velikost je součet `st_size` všech souborů celé složky rekurzivně
(podsložky `*.ignored`, `_metadata.json`, sidecary, `Thumbs.db`);
symlinky se nesledují ani nepočítají. Akce v kolizi přípony se sečte
z obou složek.

Výpis akcí čte jen cache v paměti. Přepočet jde přes frontu, kterou
zpracovává jedno vlákno: po změně aplikací (`zmena`), u položek bez
údaje a jednou denně celý archiv i koš. Archiv se jen čte.

Cache: {"akce": {název: {bajtu, cas}}, "kos": {ID: {bajtu, cas}}};
akce podle názvu bez přípony, položky koše podle ID složky
v `_kos.ignored`.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime

from .albums import _zapsat
from .archive import IGNORED
from .trash import TRASH

log = logging.getLogger(__name__)

NAME = "velikosti.json"


def bajtu(paths):
    """Součet `st_size` souborů ve složkách `paths` rekurzivně.

    Symlinky se nesledují ani nepočítají. Nečitelná podsložka se
    zaloguje a přeskočí (výsledek je pak spodní odhad).
    """
    total = 0
    stack = list(paths)
    while stack:
        path = stack.pop()
        try:
            with os.scandir(path) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(
                                follow_symlinks=False).st_size
                    except OSError as e:
                        log.warning("velikost: %s: %s", entry.path, e)
        except OSError as e:
            log.warning("velikost: %s: %s", path, e)
    return total


def _now():
    return datetime.now().isoformat(timespec="seconds")


class Velikosti:
    def __init__(self, ws):
        self.ws = ws
        self.path = ws.work / NAME
        self._lock = threading.Lock()
        self._data = self._nacti()
        # Fronta přepočtů bez duplicit: [("akce"|"kos", klíč)].
        self._fronta = []
        self._udalost = threading.Event()

    def _nacti(self):
        """Obsah souboru; poškozený nebo chybějící = prázdná cache."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        if not isinstance(data, dict):
            data = {}
        return {druh: {k: v for k, v in (data.get(druh) or {}).items()
                       if isinstance(v, dict)
                       and isinstance(v.get("bajtu"), int)}
                if isinstance(data.get(druh), dict) else {}
                for druh in ("akce", "kos")}

    def _zapsat(self):
        """Zápis cache; volá se pod zámkem."""
        try:
            _zapsat(self.path, self._data, prefix=".velikosti-")
        except OSError:
            log.exception("velikost: zápis %s selhal", self.path)

    # --- čtení --------------------------------------------------------------

    def akce(self):
        with self._lock:
            return dict(self._data["akce"])

    def kos(self):
        with self._lock:
            return dict(self._data["kos"])

    # --- složky v archivu ---------------------------------------------------

    def _slozky_akce(self, nazev):
        archiv = self.ws.archiv
        return [p for p in (archiv / nazev, archiv / (nazev + IGNORED))
                if p.is_dir() and not p.is_symlink()]

    def _slozka_kose(self, id):
        path = self.ws.archiv / TRASH / id
        return [path] if path.is_dir() and not path.is_symlink() else []

    def _slozky(self, druh, klic):
        return (self._slozky_akce if druh == "akce"
                else self._slozka_kose)(klic)

    def _kos_ids(self):
        try:
            with os.scandir(self.ws.archiv / TRASH) as it:
                return {e.name for e in it if e.is_dir(follow_symlinks=False)}
        except FileNotFoundError:
            return set()

    # --- fronta -------------------------------------------------------------

    def _zaradit(self, druh, klic):
        with self._lock:
            if (druh, klic) not in self._fronta:
                self._fronta.append((druh, klic))
        self._udalost.set()

    def zmena(self, nazev):
        """Zařadí přepočet akce (po změně aplikací, akce bez údaje)."""
        self._zaradit("akce", nazev)

    def zmena_kos(self, id):
        self._zaradit("kos", id)

    def fronta(self):
        with self._lock:
            return list(self._fronta)

    def krok(self):
        """Přepočítá jednu položku fronty; False = fronta je prázdná.

        Výsledek složky, která mezitím zmizela (přesun do koše,
        vysypání), se zahodí.
        """
        with self._lock:
            if not self._fronta:
                return False
            druh, klic = self._fronta.pop(0)
        slozky = self._slozky(druh, klic)
        if not slozky:
            return True
        hodnota = bajtu(slozky)
        with self._lock:
            if not self._slozky(druh, klic):
                return True
            self._data[druh][klic] = {"bajtu": hodnota, "cas": _now()}
            self._zapsat()
        return True

    def doplnit(self):
        """Zařadí akce a položky koše bez údaje (start serveru)."""
        akce, kos = self.akce(), self.kos()
        for nazev in self.ws.event_names():
            if nazev not in akce:
                self.zmena(nazev)
        for id in sorted(self._kos_ids()):
            if id not in kos:
                self.zmena_kos(id)

    def denni(self):
        """Zařadí celý archiv i koš a odebere z cache zmizelé položky."""
        nazvy = self.ws.event_names()
        ids = sorted(self._kos_ids())
        with self._lock:
            pred = (len(self._data["akce"]), len(self._data["kos"]))
            self._data["akce"] = {k: v for k, v in self._data["akce"].items()
                                  if k in nazvy}
            self._data["kos"] = {k: v for k, v in self._data["kos"].items()
                                 if k in ids}
            if pred != (len(self._data["akce"]), len(self._data["kos"])):
                self._zapsat()
        for nazev in nazvy:
            self.zmena(nazev)
        for id in ids:
            self.zmena_kos(id)

    # --- přesuny bez průchodu -----------------------------------------------

    def presun_do_kose(self, nazev, id):
        """Smazání akce: údaj přejde k položce koše (bez údaje se
        položka dopočítá)."""
        with self._lock:
            entry = self._data["akce"].pop(nazev, None)
            if entry is not None:
                self._data["kos"][id] = entry
                self._zapsat()
        if entry is None:
            self.zmena_kos(id)

    def vratit_z_kose(self, id, nazev):
        """Obnovení akce: údaj se vrátí akci a akce se přepočítá."""
        with self._lock:
            entry = self._data["kos"].pop(id, None)
            if entry is not None:
                self._data["akce"][nazev] = entry
                self._zapsat()
        self.zmena(nazev)

    def odebrat_z_kose(self, ids):
        """Vysypání: odebere položky koše."""
        with self._lock:
            gone = [id for id in ids if id in self._data["kos"]]
            for id in gone:
                del self._data["kos"][id]
            if gone:
                self._zapsat()

    # --- vlákno -------------------------------------------------------------

    def spustit(self, interval):
        """Vlákno `velikosti`: při startu doplní chybějící, pak
        zpracovává frontu a po `interval` (s) zařadí celý archiv."""
        def smycka():
            try:
                self.doplnit()
            except Exception:  # noqa: BLE001 — vlákno nesmí umřít
                log.exception("velikost: doplnění při startu selhalo")
            dalsi = time.monotonic() + interval
            while True:
                try:
                    if self.krok():
                        continue
                    if time.monotonic() >= dalsi:
                        dalsi = time.monotonic() + interval
                        self.denni()
                        continue
                except Exception:  # noqa: BLE001
                    log.exception("velikost: neočekávaná chyba přepočtu")
                self._udalost.wait(max(0, dalsi - time.monotonic()))
                self._udalost.clear()
        threading.Thread(target=smycka, daemon=True,
                         name="velikosti").start()
