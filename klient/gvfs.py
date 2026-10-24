"""Linux: telefon připojený přes gvfs jako složka
`/run/user/<uid>/gvfs/mtp:host=…/<úložiště>/…` (ověřeno na GNOME)."""

import os
import re
import subprocess
from pathlib import Path

from .zdroj import Polozka, Zarizeni, Zdroj, typ_media

PREFIX = "mtp:host="


def gio_svazky(text):
    """MTP svazky z výpisu `gio mount -li`: [(název, uri)]."""
    svazky, nazev = [], None
    for radek in text.splitlines():
        m = re.match(r"^Volume\(\d+\): (.*)$", radek)
        if m:
            nazev = m.group(1)
            continue
        m = re.match(r"^\s+activation_root=(mtp://\S+)$", radek)
        if m and nazev is not None:
            svazky.append((nazev, m.group(1)))
            nazev = None
    return svazky


def _host(uri):
    return uri[len("mtp://"):].strip("/")


def _citelny(host):
    """`Google_Pixel_8a_ABCDEFGH12` → `Google Pixel 8a`."""
    return re.sub(r"_[0-9A-Z]{8,}$", "", host).replace("_", " ")


class Gvfs(Zdroj):
    def __init__(self, koren=None, gio=True):
        self.koren = Path(koren or f"/run/user/{os.getuid()}/gvfs")
        self.gio = gio
        self._nazvy = {}

    def _svazky(self):
        if not self.gio:
            return []
        try:
            out = subprocess.run(["gio", "mount", "-li"], capture_output=True,
                                 text=True, timeout=10).stdout
        except (OSError, subprocess.SubprocessError):
            return []
        return gio_svazky(out)

    def pripojit(self):
        """Připojí MTP svazky, které gvfs zná, ale nejsou připojené
        (bez automatického připojení). Vrátí, jestli se o něco pokusil."""
        pokus = False
        for nazev, uri in self._svazky():
            self._nazvy[_host(uri)] = nazev
            if not (self.koren / (PREFIX + _host(uri))).exists():
                pokus = True
                try:
                    subprocess.run(["gio", "mount", uri], capture_output=True,
                                   timeout=30)
                except (OSError, subprocess.SubprocessError):
                    pass
        return pokus

    def zarizeni(self):
        try:
            slozky = sorted(p for p in self.koren.iterdir()
                            if p.name.startswith(PREFIX))
        except OSError:
            return []
        hosty = [p.name[len(PREFIX):] for p in slozky]
        if any(h not in self._nazvy for h in hosty):
            self._nazvy.update((_host(uri), n) for n, uri in self._svazky())
            for h in hosty:
                self._nazvy.setdefault(h, _citelny(h))
        vysledek = []
        for p, host in zip(slozky, hosty):
            try:
                uloziste = tuple(sorted(d.name for d in p.iterdir()
                                        if d.is_dir()))
            except OSError:
                uloziste = ()
            vysledek.append(Zarizeni(p.name, self._nazvy[host], uloziste))
        return vysledek

    def _cesta(self, zar, cesta):
        casti = [c for c in cesta.split("/") if c]
        if any(c in (".", "..") for c in casti):
            raise ValueError(cesta)
        return self.koren.joinpath(zar.id, *casti)

    def slozky(self, zar, cesta):
        with os.scandir(self._cesta(zar, cesta)) as it:
            return sorted((e.name for e in it if e.is_dir()),
                          key=str.casefold)

    def polozky(self, zar, cesta):
        slozka = "/".join(c for c in cesta.split("/") if c)
        with os.scandir(self._cesta(zar, cesta)) as it:
            for e in it:
                typ = typ_media(e.name)
                if typ is None or not e.is_file():
                    continue
                st = e.stat()
                yield Polozka(slozka, e.name, st.st_size, st.st_mtime, typ)

    def mistni_cesta(self, zar, polozka):
        return self._cesta(zar, polozka.cesta)

    def otevrit(self, zar, polozka):
        return open(self._cesta(zar, polozka.cesta), "rb")
