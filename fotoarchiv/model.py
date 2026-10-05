"""Datový model `_metadata.json`: dědění a sloučení výsledku skenu.

Stejný výpočet dědění má klient v `static/inherit.js`; obě implementace
se ověřují proti fixturám v `tests/fixtures/inheritance/`.
"""

import unicodedata

from .archive import EVENT_RE, SCHEMA

# Klíče, které patří jen své úrovni a nedědí se.
LOCAL_KEYS = {
    # Účastníci akce jsou výčet lidí na akci, ne osoby na každé fotce.
    "akce": {"ucastnici"},
    "skupina": {"nazev"},
    "soubor": {"skupina", "sha256"},
}

TECHNICAL_KEYS = ("datum", "pristroj", "gps")


def resolve(doc, filename):
    """Výsledné hodnoty polí souboru s úrovní, odkud pocházejí.

    Vrací {pole: {"hodnota": …, "uroven": "akce"|"skupina"|"soubor"}}.
    Pole přítomné na nižší úrovni přepisuje vyšší, i když je prázdné.
    """
    record = doc.get("soubory", {}).get(filename, {})
    group = doc.get("skupiny", {}).get(record.get("skupina"), {})
    levels = [
        ("akce", doc.get("akce", {})),
        ("skupina", group),
        ("soubor", record),
    ]
    result = {}
    for level, values in levels:
        for key, value in values.items():
            if key in LOCAL_KEYS[level]:
                continue
            result[key] = {"hodnota": value, "uroven": level}
    return result


def technical(scanned):
    """Technické údaje ze skenu; neznámé se nezapisují, aby se dědily."""
    return {key: scanned[key] for key in TECHNICAL_KEYS
            if scanned.get(key) is not None}


def new_document(event_name, files, groups):
    """Návrh dokumentu pro novou akci.

    `files` je výsledek skenu, `groups` návrh skupin (`scan.propose_groups`).
    Název akce z názvu složky, datum od–do z dat souborů, jinak z názvu.
    """
    date, title = EVENT_RE.match(event_name).groups()
    days = sorted(f["datum"][:10] for f in files if f.get("datum"))
    soubory = {}
    for f in files:
        record = technical(f)
        record["skupina"] = groups["prirazeni"].get(f["nazev"])
        soubory[f["nazev"]] = record
    return {
        "schema": SCHEMA,
        "dokonceno": None,
        "akce": {
            "nazev": title,
            "datum_od": days[0] if days else date,
            "datum_do": days[-1] if days else date,
        },
        "skupiny": groups["skupiny"],
        "soubory": soubory,
    }


def merge_scan(doc, files):
    """Doplní do dokumentu nové soubory ze skenu.

    Existující záznamy se nemění (ruční opravy technických údajů zůstanou).
    Vrací (nové názvy, chybějící názvy); dokument mění na místě.
    """
    # Názvy na SMB mohou přijít v NFD i NFC, porovnává se po NFC.
    soubory = doc.setdefault("soubory", {})
    known = {_nfc(name) for name in soubory}
    on_disk = {_nfc(f["nazev"]) for f in files}
    added = []
    for f in files:
        if _nfc(f["nazev"]) not in known:
            soubory[f["nazev"]] = technical(f)
            added.append(f["nazev"])
    missing = sorted(name for name in soubory if _nfc(name) not in on_disk)
    return added, missing


def _nfc(name):
    return unicodedata.normalize("NFC", name)
