"""Plán úklidu kořene akce: podsložky a RAWy.

Plán je seznam operací `move`, `rename` a `delete` s příznakem `blocked`.
Ve vývojovém režimu se jen zobrazí, v produkčním ho `execute` sestaví znovu
a provede. Nic se nikdy nepřepíše: cíl, který existuje (nebo vznikne
dřívější operací plánu, nebo mezi náhledem a provedením), operaci zablokuje.
"""

import logging
import os
import unicodedata

from .archive import is_skipped

log = logging.getLogger(__name__)

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


DONE = "hotovo"
BLOCKED = "blokovano"
FAILED = "chyba"


class Blocked(Exception):
    pass


def _move(event_dir, src, dst):
    """Přesun/přejmenování, které nikdy nepřepíše existující cíl."""
    dst_path = os.path.join(event_dir, dst)
    target_dir = os.path.dirname(dst_path)
    if os.path.basename(target_dir) == RAW_DIR and \
            not os.path.isdir(target_dir):
        os.mkdir(target_dir)
    # os.rename na Linuxu cíl přepíše: kontrola těsně před ním, souběh
    # vylučuje zámek akce. Porovnání jako v plánu (SMB, NFC/NFD).
    with os.scandir(target_dir) as it:
        existing = {_key(e.name) for e in it}
    if _key(os.path.basename(dst_path)) in existing:
        raise Blocked("cíl už existuje")
    os.rename(os.path.join(event_dir, src), dst_path)


def _delete(event_dir, name):
    """Smaže podsložku, ve které zbyl nejvýš `Thumbs.db`."""
    path = os.path.join(event_dir, name)
    entries = os.listdir(path)
    if any(not is_skipped(e) for e in entries):
        raise OSError(f"složka není prázdná: {name}")
    for e in entries:
        os.remove(os.path.join(path, e))
    os.rmdir(path)


def execute(event_dir, choices=None, raw_from_root=True):
    """Sestaví plán znovu a provede jeho neblokované operace.

    Vrátí operace plánu doplněné o `stav` (hotovo / blokovano / chyba)
    a `chyba`. Selhaný nebo blokovaný přesun zablokuje smazání své
    podsložky, ostatní operace běží dál.
    """
    result = plan(event_dir, choices, raw_from_root)
    unfinished = set()  # podsložky, ze kterých se nepřesunulo všechno
    for o in result["operace"]:
        o["chyba"] = None
        source_dir = o["z"].split("/")[0] if "/" in o["z"] else None
        try:
            if o["blocked"]:
                raise Blocked(o["duvod"])
            if o["typ"] == "delete":
                if o["z"] in unfinished:
                    raise Blocked("přesun ze složky neproběhl")
                _delete(event_dir, o["z"])
            else:
                _move(event_dir, o["z"], o["do"])
            o["stav"] = DONE
        except Blocked as e:
            o["stav"], o["duvod"] = BLOCKED, str(e)
        except OSError as e:
            o["stav"], o["chyba"] = FAILED, str(e)
        if o["stav"] != DONE and o["typ"] == "move" and source_dir:
            unfinished.add(source_dir)
        log.info("úklid %s: %s %s → %s: %s %s", os.path.basename(event_dir),
                 o["typ"], o["z"], o["do"], o["stav"],
                 o["chyba"] or o["duvod"] or "")
    return result
