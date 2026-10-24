"""Zdroj médií: rozhraní, které platformní adaptéry (gvfs, Windows)
implementují. UI, evidence a nahrávání pracují jen s ním."""

import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

# Jen to, co přijme import aplikace (`scan.MEDIA_EXT`, RAWy podle
# `cleanup.RAW_EXT`); klient je nezávislý na balíčku serveru.
FOTKY = {".jpg", ".jpeg", ".png"}
VIDEA = {".mp4", ".mov"}
RAWY = {".rw2", ".cr2", ".cr3", ".nef", ".arw", ".dng", ".orf", ".raf"}

# Výchozí složka fotoaparátu, relativně k úložišti telefonu.
FOTOAPARAT = "DCIM/Camera"


def typ_media(nazev):
    """"foto", "video", "raw", nebo None (import ho nepřijme)."""
    ext = PurePosixPath(nazev).suffix.lower()
    if ext in FOTKY:
        return "foto"
    if ext in VIDEA:
        return "video"
    if ext in RAWY:
        return "raw"
    return None


@dataclass(frozen=True)
class Zarizeni:
    """Připojený telefon. `id` je stálé mezi připojeními (evidence),
    `uloziste` jsou kořeny úložišť; prázdné = zamčený telefon."""
    id: str
    nazev: str
    uloziste: tuple = ()


@dataclass(frozen=True)
class Polozka:
    """Médium v telefonu. `slozka` je cesta s úložištěm na začátku
    (`Interní sdílené úložiště/DCIM/Camera`), `datum` v sekundách."""
    slozka: str
    nazev: str
    velikost: int
    datum: float
    typ: str = field(default="foto")

    @property
    def cesta(self):
        return f"{self.slozka}/{self.nazev}"

    @property
    def klic(self):
        """Klíč v evidenci nahraných: složka + název + velikost + datum."""
        return [self.slozka, self.nazev, self.velikost, int(self.datum)]


class Zdroj:
    """Rozhraní zdroje médií. Cesty jsou relativní k zařízení, oddělené
    `/`, první část je úložiště."""

    def zarizeni(self):
        """Seznam připojených zařízení (`Zarizeni`)."""
        raise NotImplementedError

    def slozky(self, zar, cesta):
        """Názvy podsložek složky `cesta` (prázdná = úložiště)."""
        raise NotImplementedError

    def polozky(self, zar, cesta):
        """Fotky a videa přímo ve složce `cesta`, postupně (generátor)."""
        raise NotImplementedError

    def otevrit(self, zar, polozka):
        """Binární soubor položky pro čtení."""
        raise NotImplementedError

    def mistni_cesta(self, zar, polozka):
        """Cesta v souborovém systému (ffmpeg), nebo None."""
        return None

    def hlavicka(self, zar, polozka, n=65536):
        """Prvních `n` bajtů položky (EXIF náhled bez čtení celé fotky)."""
        with self.otevrit(zar, polozka) as f:
            return f.read(n)

    def kopirovat(self, zar, polozka, cil):
        """Zkopíruje položku do složky `cil` beze změny bajtů; vrátí
        cestu kopie. Podsložku s datem nezakládá."""
        soubor = Path(cil) / polozka.nazev
        with self.otevrit(zar, polozka) as src, open(soubor, "xb") as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
        return soubor

    def vychozi_slozka(self, zar):
        """Složka fotoaparátu na prvním úložišti, které ji má; jinak
        kořen prvního úložiště, bez úložiště None."""
        for ul in zar.uloziste:
            cesta = f"{ul}/{FOTOAPARAT}"
            try:
                rodic, jmeno = cesta.rsplit("/", 1)
                if jmeno in self.slozky(zar, rodic):
                    return cesta
            except OSError:
                continue
        return zar.uloziste[0] if zar.uloziste else None
