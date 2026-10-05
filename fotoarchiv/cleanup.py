"""Plán úklidu kořene akce: podsložky a RAWy.

Plán je seznam operací `move`, `rename` a `delete` s příznakem `blocked`.
V prototypu se jen zobrazí; provedení doplní pozdější změna nad stejným
plánem. Nic se nikdy nepřepíše: cíl, který existuje (nebo vznikne dřívější
operací plánu), operaci zablokuje.
"""

import os
import unicodedata

from .archive import is_skipped

RAW_EXT = {"rw2", "cr2", "cr3", "nef", "arw", "dng", "orf", "raf"}
RAW_DIR = "RAW.ignored"
IGNORED = ".ignored"

MOVE = "presunout"
KEEP = "ponechat"


def is_raw(name):
    return name.rsplit(".", 1)[-1].lower() in RAW_EXT if "." in name else False


def _key(name):
    # Porovnání cílů: SMB nerozlišuje velikost písmen ani NFC/NFD.
    return unicodedata.normalize("NFC", name).casefold()


def _scan_dir(path):
    files, dirs = [], []
    with os.scandir(path) as it:
        for entry in it:
            (dirs if entry.is_dir() else files).append(entry.name)
    return sorted(files), sorted(dirs)


def subfolders(event_dir):
    """Podsložky bez `.ignored` s počty souborů a RAWů a cílem ponechání."""
    _, dirs = _scan_dir(event_dir)
    result = []
    for name in dirs:
        if name.endswith(IGNORED):
            continue
        files, nested = _scan_dir(os.path.join(event_dir, name))
        counted = [f for f in files if not is_skipped(f)]
        raws = sum(1 for f in counted if is_raw(f))
        mostly_raw = raws * 2 > len(counted)
        result.append({
            "nazev": name,
            "souboru": len(counted),
            "rawu": raws,
            "podslozek": len(nested),
            "cil": RAW_DIR if mostly_raw else name + IGNORED,
            # Návrh volby: RAWovou složku ponechat, ostatní k rozhodnutí.
            "navrh": KEEP if mostly_raw else None,
        })
    return result


def plan(event_dir, choices=None, raw_from_root=True):
    """Plán úklidu.

    `choices` = {název podsložky: "presunout" | "ponechat" | None}; chybějící
    volba bere návrh z `subfolders`. `raw_from_root` = přesunout RAWy
    z kořene do `RAW.ignored`.
    """
    choices = choices or {}
    root_files, root_dirs = _scan_dir(event_dir)
    root = {_key(n) for n in root_files + root_dirs}
    raw_dir_exists = RAW_DIR in root_dirs
    # Obsah RAW.ignored po dosud naplánovaných operacích (None = neexistuje).
    raw_content = None
    if raw_dir_exists:
        files, dirs = _scan_dir(os.path.join(event_dir, RAW_DIR))
        raw_content = {_key(n) for n in files + dirs}

    folders = subfolders(event_dir)
    ops = []

    def op(typ, src, dst=None, reason=None):
        ops.append({"typ": typ, "z": src, "do": dst,
                    "blocked": reason is not None, "duvod": reason})
        return reason is None

    def move_into(target_set, src, dst, name):
        if _key(name) in target_set:
            return op("move", src, dst, "cíl už existuje")
        target_set.add(_key(name))
        return op("move", src, dst)

    for folder in folders:
        name = folder["nazev"]
        choice = choices.get(name, folder["navrh"])
        folder["volba"] = choice
        if choice is None:
            continue
        files, nested = _scan_dir(os.path.join(event_dir, name))
        if choice == MOVE:
            ok = True
            for f in files:
                if is_skipped(f):
                    continue
                ok &= move_into(root, f"{name}/{f}", f, f)
            if nested:
                op("delete", name, None, "obsahuje další podsložky")
            elif ok:
                op("delete", name)
            else:
                op("delete", name, None, "složka nebude prázdná")
        elif choice == KEEP:
            target = folder["cil"]
            if target == RAW_DIR and raw_content is not None:
                # RAW.ignored už je (nebo vznikne): soubory se do ní přidají.
                ok = True
                for f in files:
                    if is_skipped(f):
                        continue
                    ok &= move_into(raw_content, f"{name}/{f}",
                                    f"{RAW_DIR}/{f}", f)
                if nested:
                    op("delete", name, None, "obsahuje další podsložky")
                elif ok:
                    op("delete", name)
                else:
                    op("delete", name, None, "složka nebude prázdná")
            elif _key(target) in root:
                op("rename", name, target, "cíl už existuje")
            else:
                op("rename", name, target)
                root.add(_key(target))
                if target == RAW_DIR:
                    raw_content = {_key(f) for f in files + nested}

    if raw_from_root:
        for f in root_files:
            if not is_raw(f):
                continue
            if raw_content is None:
                raw_content = set()
            move_into(raw_content, f, f"{RAW_DIR}/{f}", f)

    return {
        "podslozky": folders,
        "raw_v_koreni": sum(1 for f in root_files if is_raw(f)),
        "operace": ops,
    }
