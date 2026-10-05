"""Jména osob a autorů: otevřený seznam, našeptávání a návrh opravy.

Porovnání ignoruje diakritiku, velikost písmen a pořadí slov.
Kanonický tvar je `Příjmení, Jméno`.
"""

import json
import os
import re
import unicodedata

NAME_KEYS = ("osoby", "autori")


def _plain(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.casefold()


def tokens(name):
    return re.findall(r"\w+", _plain(name))


def normalize(name):
    """Klíč pro porovnání: bez diakritiky, malými, slova seřazená."""
    return " ".join(sorted(tokens(name)))


def names_in(doc):
    """Všechna jména z polí `osoby` a `autori` na všech úrovních."""
    records = [doc.get("akce", {})]
    records += doc.get("skupiny", {}).values()
    records += doc.get("soubory", {}).values()
    found = set()
    for record in records:
        for key in NAME_KEYS:
            for name in record.get(key) or []:
                if isinstance(name, str) and name.strip():
                    found.add(name.strip())
    return found


class NameIndex:
    """Seznam jmen ze všech `_metadata.json`; soubory cachuje podle mtime."""

    def __init__(self, paths_fn):
        self._paths_fn = paths_fn
        self._cache = {}

    def names(self):
        result = set()
        seen = set()
        for path in self._paths_fn():
            key = str(path)
            seen.add(key)
            try:
                mtime = os.stat(path).st_mtime
            except FileNotFoundError:
                continue
            hit = self._cache.get(key)
            if not hit or hit[0] != mtime:
                try:
                    doc = json.loads(path.read_bytes())
                    hit = (mtime, names_in(doc))
                except (OSError, ValueError):
                    hit = (mtime, set())
                self._cache[key] = hit
            result |= hit[1]
        for key in set(self._cache) - seen:
            del self._cache[key]
        return sorted(result, key=_plain)


def suggest(query, names, limit=10):
    """Jména, jejichž slova začínají slovy dotazu (v libovolném pořadí)."""
    wanted = tokens(query)
    if not wanted:
        return []
    result = []
    for name in names:
        have = tokens(name)
        if all(any(h.startswith(w) for h in have) for w in wanted):
            result.append(name)
            if len(result) >= limit:
                break
    return result


def canonical(name):
    """`Jan Novák` → `Novák, Jan`; jiný tvar vrací None."""
    name = " ".join(name.split())
    if "," in name:
        return None
    parts = name.split(" ")
    if len(parts) != 2:
        return None
    return f"{parts[1]}, {parts[0]}"


def check(name, names):
    """Kontrola zadaného jména proti seznamu.

    Vrací {"znamo": bool, "mysleli_jste": jméno | None,
    "prevod": kanonický tvar | None}.
    """
    name = " ".join(name.split())
    if name in names:
        return {"znamo": True, "mysleli_jste": None, "prevod": None}
    key = normalize(name)
    for known in names:
        if normalize(known) == key:
            return {"znamo": False, "mysleli_jste": known, "prevod": None}
    return {"znamo": False, "mysleli_jste": None, "prevod": canonical(name)}
