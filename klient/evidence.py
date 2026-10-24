"""Konfigurace klienta a evidence nahraných médií. Obojí jen
na počítači uživatele, nikdy v archivu ani na serveru."""

import json
import os
import sys
import threading
from pathlib import Path


def adresar_konfigurace():
    """`%APPDATA%\\fotoarchiv-klient`, jinak
    `$XDG_CONFIG_HOME/fotoarchiv-klient` (`~/.config/…`)."""
    if sys.platform == "win32":
        zaklad = Path(os.environ.get("APPDATA") or Path.home())
    else:
        zaklad = Path(os.environ.get("XDG_CONFIG_HOME")
                      or Path.home() / ".config")
    return zaklad / "fotoarchiv-klient"


def _nacist(soubor):
    try:
        data = json.loads(Path(soubor).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _ulozit(soubor, data):
    """Atomický zápis: dočasný soubor a přejmenování."""
    soubor = Path(soubor)
    soubor.parent.mkdir(parents=True, exist_ok=True)
    tmp = soubor.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    os.replace(tmp, soubor)


class Konfigurace:
    """Adresa serveru, login a naposledy otevřená složka po zařízení.
    Heslo se neukládá."""

    def __init__(self, adresar=None):
        self.soubor = Path(adresar or adresar_konfigurace()) / "klient.json"
        self.data = _nacist(self.soubor)

    @property
    def server(self):
        return self.data.get("server") or ""

    @property
    def login(self):
        return self.data.get("login") or ""

    def nastavit_prihlaseni(self, server, login):
        self.data["server"], self.data["login"] = server, login
        _ulozit(self.soubor, self.data)

    def slozka(self, zarizeni_id):
        return (self.data.get("slozky") or {}).get(zarizeni_id)

    def nastavit_slozku(self, zarizeni_id, cesta):
        self.data.setdefault("slozky", {})[zarizeni_id] = cesta
        _ulozit(self.soubor, self.data)


class Evidence:
    """Média úspěšně nahraná z každého zařízení (klíč `Polozka.klic`)."""

    def __init__(self, adresar=None):
        self.soubor = Path(adresar or adresar_konfigurace()) / "nahrane.json"
        self._zamek = threading.Lock()
        data = _nacist(self.soubor)
        self._sady = {z: {tuple(k) for k in v if isinstance(k, list)}
                      for z, v in data.items() if isinstance(v, list)}

    def je_nahrana(self, zarizeni_id, polozka):
        return tuple(polozka.klic) in self._sady.get(zarizeni_id, ())

    def pridat(self, zarizeni_id, polozky):
        with self._zamek:
            sada = self._sady.setdefault(zarizeni_id, set())
            sada.update(tuple(p.klic) for p in polozky)
            _ulozit(self.soubor, {z: sorted(list(k) for k in s)
                                  for z, s in self._sady.items()})
