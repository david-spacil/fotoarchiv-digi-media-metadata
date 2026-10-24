"""Registrace klienta v systému bez instalátoru.

Linux: `.desktop` v `~/.local/share/applications/` pro menu aplikací.
Nabídka po připojení telefonu na Linuxu není (MTP svazek nehlásí
`x-content/*`), klient na telefon čeká sám. Windows (AutoPlay) zatím ne.
"""

import os
import shlex
import sys
from pathlib import Path

NAZEV = "fotoarchiv-klient.desktop"


def soubor_desktop():
    zaklad = Path(os.environ.get("XDG_DATA_HOME")
                  or Path.home() / ".local" / "share")
    return zaklad / "applications" / NAZEV


def prikaz():
    """(příkaz, pracovní adresář) ke spuštění klienta."""
    if getattr(sys, "frozen", False):  # PyInstaller
        return shlex.quote(sys.executable), None
    koren = Path(__file__).resolve().parent.parent
    return f"{shlex.quote(sys.executable)} -m klient", koren


def obsah_desktop():
    exe, adresar = prikaz()
    radky = ["[Desktop Entry]", "Type=Application",
             "Name=Fotoarchiv – import z telefonu",
             "Comment=Nahraje fotky z telefonu připojeného kabelem "
             "do Fotoarchivu",
             f"Exec={exe}", "Icon=camera-photo", "Terminal=false",
             "Categories=Graphics;Photography;"]
    if adresar:
        radky.append(f"Path={adresar}")
    return "\n".join(radky) + "\n"


def registrovat():
    if sys.platform == "win32":
        raise SystemExit("Registrace AutoPlay ve Windows zatím není.")
    cil = soubor_desktop()
    cil.parent.mkdir(parents=True, exist_ok=True)
    cil.write_text(obsah_desktop(), encoding="utf-8")
    return cil


def odregistrovat():
    if sys.platform == "win32":
        raise SystemExit("Registrace AutoPlay ve Windows zatím není.")
    cil = soubor_desktop()
    cil.unlink(missing_ok=True)
    return cil
