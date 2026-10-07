"""Přehled složky `přetřídit`: kandidáti na import ze zdroje v archivu.

Složky první úrovně (bez `.ignored`) s počty souborů podle typu,
podsložkami, datem z názvu a z EXIF a navrženou akcí `YYYY-MM-DD název`.
EXIF se čte po složkách přes `importer.scan_source` se stejnou cache jako
přehled importu ze zdroje.
"""

import os
import re
from collections import Counter
from datetime import date
from pathlib import Path

from . import importer
from .cleanup import IGNORED

# (regex, pořadí skupin rok, měsíc, den); oddělené od okolních číslic.
NAME_DATES = [
    (re.compile(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)"), (3, 2, 1)),
    (re.compile(r"(?<!\d)(\d{4})_(\d{1,2})_(\d{1,2})(?!\d)"), (1, 2, 3)),
    (re.compile(r"(?<!\d)(\d{1,2})_(\d{1,2})_(\d{4})(?!\d)"), (3, 2, 1)),
]
YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")


def name_date(name):
    """(datum ISO, nebo None; rok, nebo None) z názvu složky. Samotný rok
    celé datum nedá."""
    for regex, (y, m, d) in NAME_DATES:
        for match in regex.finditer(name):
            try:
                day = date(int(match.group(y)), int(match.group(m)),
                           int(match.group(d)))
            except ValueError:
                continue
            return day.isoformat(), day.year
    match = YEAR_RE.search(name)
    return None, int(match.group(1)) if match else None


def folders(root):
    """Názvy složek první úrovně `root` bez `.ignored`, seřazené;
    chybějící `root` = prázdný seznam."""
    try:
        with os.scandir(root) as it:
            names = [e.name for e in it if e.is_dir()
                     and not e.name.endswith(IGNORED)
                     and not e.name.startswith(".")]
    except FileNotFoundError:
        return []
    return sorted(names)


def listing(root, name):
    """Údaje složky bez EXIF: počty podle typu (`importer.kind`, včetně
    podsložek, bez `Thumbs.db`), podsložky a datum z názvu."""
    folder = Path(root) / name
    entries = importer.source_entries(folder)
    datum, rok = name_date(name)
    return {
        "nazev": name,
        "pocty": dict(Counter(importer.kind(e["nazev"]) for e in entries)),
        "velikost": sum(e["velikost"] for e in entries),
        "podslozky": [d for d in importer.source_dirs(folder) if d],
        "z_nazvu": {"datum": datum, "rok": rok},
    }


def details(root, name, cache_dir, exiftool=None):
    """Údaje složky z EXIF: rozsah dat a návrh akce (datum z EXIF, jinak
    z názvu, jinak bez data; název = název složky)."""
    data = importer.scan_source(Path(root) / name, cache_dir, exiftool)
    days = sorted(f["datum"][:10] for f in data.values() if f["datum"])
    od = days[0] if days else None
    datum = od or name_date(name)[0]
    return {
        "nazev": name,
        "od": od,
        "do": days[-1] if days else None,
        "navrh": {"datum": datum, "nazev": name,
                  "akce": f"{datum} {name}" if datum else None},
    }


def iter_overview(root, cache_dir, exiftool=None, exif=True):
    """Generátor přehledu pro stream NDJSON: nejdřív `vypis` (všechny
    složky bez EXIF), pak po složkách `slozka` s údaji z EXIF."""
    names = folders(root)
    yield {"typ": "vypis", "slozky": [listing(root, n) for n in names]}
    if not exif:
        return
    for i, name in enumerate(names):
        try:
            item = details(root, name, cache_dir, exiftool)
        except FileNotFoundError:
            continue  # mezitím zmizela (import)
        yield dict(item, typ="slozka", hotovo=i + 1, celkem=len(names))
