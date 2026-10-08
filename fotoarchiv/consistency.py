"""Kontrola konzistence kořene akce: co v něm nepatří nebo si odporuje.

Čte jen výpis kořene a předaný `_metadata.json`, obsah souborů ne,
a nic nemění — volá ji i seznam akcí. Nápravu (přesuny) dělá úklid
(`cleanup.py`); záznam bez souboru se jen hlásí.
"""

import os

from .archive import (IGNORED, IMPORT_TMP_PREFIX, METADATA_NAME, TMP_PREFIX,
                      XMP_TMP_PREFIX, is_skipped)
from .cleanup import _key, is_raw
from .scan import MEDIA_EXT, extension

# Druhy nálezů v pořadí, v jakém se ukazují.
NEPODPOROVANY = "nepodporovany"
SIROTEK_XMP = "sirotek_xmp"
RAW = "raw"
PODSLOZKA = "podslozka"
CHYBEJICI = "chybejici"
DRUHY = (NEPODPOROVANY, SIROTEK_XMP, RAW, PODSLOZKA, CHYBEJICI)
# Nálezy, které úklid umí napravit přesunem do `ostatni.ignored`.
OSTATNI = (NEPODPOROVANY, SIROTEK_XMP)

_TMP = (TMP_PREFIX, XMP_TMP_PREFIX, IMPORT_TMP_PREFIX)


def _scan(event_dir):
    files, dirs = [], []
    with os.scandir(event_dir) as it:
        for entry in it:
            (dirs if entry.is_dir() else files).append(entry.name)
    return files, dirs


def classify(files, dirs, doc):
    """Nálezy z výpisu kořene (`files`, `dirs`) a dokumentu `doc`."""
    found = []
    keys = {_key(f) for f in files}
    for f in files:
        if is_skipped(f) or f == METADATA_NAME or f.startswith(_TMP):
            continue
        if f.lower().endswith(".xmp"):
            if _key(f[:-4]) not in keys:
                found.append((SIROTEK_XMP, f))
        elif is_raw(f):
            found.append((RAW, f))
        elif extension(f) not in MEDIA_EXT:
            found.append((NEPODPOROVANY, f))
    found += [(PODSLOZKA, d) for d in dirs if not d.endswith(IGNORED)]
    found += [(CHYBEJICI, name) for name in ((doc or {}).get("soubory") or {})
              if _key(name) not in keys]
    found.sort(key=lambda x: (DRUHY.index(x[0]), _key(x[1])))
    return [{"druh": druh, "nazev": nazev} for druh, nazev in found]


def check(event_dir, doc):
    """Nálezy kontroly kořene složky akce `event_dir`."""
    return classify(*_scan(event_dir), doc)


def counts(findings):
    """Počty nálezů podle druhu (jen nenulové)."""
    result = {}
    for f in findings:
        result[f["druh"]] = result.get(f["druh"], 0) + 1
    return result
