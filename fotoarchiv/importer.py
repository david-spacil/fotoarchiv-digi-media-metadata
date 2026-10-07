"""Import fotek a videí do archivu přes prohlížeč.

Nahrané soubory čekají v pracovním adresáři (`work/import/<id>/`), do
archivu se před potvrzením nic nezapíše. Plán má tvar plánu úklidu
(operace s `blocked` a `duvod`), navíc `stav` ok / blokovano / duplicita.
`execute` plán sestaví znovu a soubory zkopíruje bez přepsání: dočasný
`.import-*.tmp` v cílové složce, kontrola cíle těsně před přejmenováním.
Plán i provedení jsou generátory událostí průběhu (pro stream NDJSON);
zavření generátoru uprostřed kopie smaže rozkopírovaný soubor.

Import se zdrojem (`zdroj` = složka první úrovně `přetřídit`) nic
nenahrává: záznamy souborů se sestaví z aktuálního obsahu zdroje
a provedení soubory přesune přejmenováním (stejný svazek).
"""

import hashlib
import json
import logging
import os
import re
import secrets
import shutil
import tempfile
import threading
import time
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

from . import names, scan
from .archive import (EVENT_RE, IMPORT_TMP_PREFIX, UNSORTED, is_metadata,
                      is_skipped)
from .cleanup import (BLOCKED, DONE, FAILED, IGNORED, RAW_DIR, Blocked, _key,
                      is_raw)

log = logging.getLogger(__name__)

FILES_DIR = "soubory"
# Soubor, jehož jméno už ve `soubory/` je (jiná podsložka výběru); v plánu
# se zablokuje, ale uživatel ho v přehledu uvidí.
OTHER_DIR = "kolize"
RECORD = "import.json"
PROPOSALS = "navrhy-skupin"  # návrhy skupin akcí bez `_metadata.json`
MAX_FILE = 20 * 2**30
RESERVE = 2**30          # volné místo, které nahrávání na disku nechá
MAX_AGE = 7 * 24 * 3600  # neaktivní importy se při startu smažou
CHUNK = 1 << 20
STEP = 64 * 2**20        # průběh hashování a kopie i uvnitř velkých souborů
TMP_AGE = 3600           # starší `.import-*.tmp` v akci jsou po výpadku
ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")

OK = "ok"
DUPLICATE = "duplicita"


class Refused(Exception):
    """Požadavek nejde provést; `code` a `detail` jdou klientovi."""

    def __init__(self, code, **detail):
        super().__init__(code)
        self.code = code
        self.detail = detail


def kind(name):
    if is_raw(name):
        return "raw"
    ext = scan.extension(name)
    if ext in scan.VIDEO_EXT:
        return "video"
    if ext in scan.MEDIA_EXT:
        return "foto"
    return "nepodporovany"


def flat_name(path):
    """Jméno souboru z relativní cesty výběru (podsložky se zploští)."""
    name = re.split(r"[/\\]", path or "")[-1]
    if name in ("", ".", "..") or "\0" in name:
        raise Refused("neplatne_jmeno")
    return name


def _drain(gen):
    """Doběhne generátor a vrátí jeho návratovou hodnotu."""
    while True:
        try:
            next(gen)
        except StopIteration as stop:
            return stop.value


def _relay(gen, event):
    """`yield from gen` s hodnotami převedenými přes `event`; vrátí výsledek
    `gen`. Zavření zavře i `gen` (smaže tak rozkopírovaný soubor)."""
    try:
        while True:
            try:
                value = next(gen)
            except StopIteration as stop:
                return stop.value
            yield event(value)
    finally:
        gen.close()


def _sha256_steps(path):
    """Po každých `STEP` bajtech vydá počet přečtených; vrátí sha256."""
    digest, done, reported = hashlib.sha256(), 0, 0
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            digest.update(chunk)
            done += len(chunk)
            if done - reported >= STEP:
                reported = done
                yield done
    return digest.hexdigest()


def file_sha256(path):
    return _drain(_sha256_steps(path))


# --- nová akce ---------------------------------------------------------------

def check_new_name(archiv, nazev):
    """Vyhodí Refused, když složku nové akce `nazev` nejde založit."""
    m = EVENT_RE.match(nazev) if isinstance(nazev, str) else None
    if (not m or nazev != nazev.strip() or nazev.endswith(".")
            or "/" in nazev or "\\" in nazev or nazev.startswith(".")):
        raise Refused("neplatny_nazev")
    try:
        date.fromisoformat(m.group(1))
    except ValueError:
        raise Refused("neplatny_nazev") from None
    # SMB nerozlišuje velikost písmen: existence přes _key, ne přes stat.
    existing = {_key(n): n for n in os.listdir(archiv)}
    if _key(nazev) in existing:
        raise Refused("existuje", akce=existing[_key(nazev)])


def create_event(archiv, nazev):
    """Založí složku nové akce; existující (i mezitím vzniklou) odmítne."""
    check_new_name(archiv, nazev)
    path = Path(archiv) / nazev
    try:
        os.mkdir(path)
    except FileExistsError:
        raise Refused("existuje", akce=nazev) from None
    return path


# --- plán a provedení ----------------------------------------------------------

def _listing(path):
    try:
        with os.scandir(path) as it:
            return {_key(e.name) for e in it}
    except FileNotFoundError:
        return set()


def _root_stats(event_dir):
    """[(název, cesta, stat)] souborů v kořeni akce (bez metadat)."""
    with os.scandir(event_dir) as it:
        return [(e.name, e.path, e.stat()) for e in it if e.is_file()
                and not is_skipped(e.name) and not is_metadata(e.name)]


def _iter_hashes(todo, cache_path):
    """{klíč: sha256} souborů `todo` = [(klíč, cesta, stat)].

    Hashe se cachují podle (klíč, velikost, mtime). Generátor průběhu:
    `hash` (kolik souborů a bajtů se porovná) a `hash_prubeh` (kolik je
    hotovo; po každém souboru, u velkých i po `STEP`). Hashe z cache se
    počítají hned jako hotové.
    """
    if not todo:
        return {}
    try:
        cache = json.loads(Path(cache_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        cache = {}
    yield {"typ": "hash", "souboru": len(todo),
           "bajtu": sum(st.st_size for _, _, st in todo)}
    shas, fresh, files, done = {}, [], 0, 0
    for key, path, st in todo:
        hit = cache.get(key)
        if hit and hit["size"] == st.st_size and \
                hit["mtime_ns"] == st.st_mtime_ns:
            shas[key] = hit["sha256"]
            files, done = files + 1, done + st.st_size
        else:
            fresh.append((key, path, st))

    def progress(n=0):
        return {"typ": "hash_prubeh", "hotovo_souboru": files,
                "hotovo_bajtu": done + n}
    if files:
        yield progress()
    for key, path, st in fresh:
        sha = yield from _relay(_sha256_steps(path), progress)
        shas[key] = sha
        cache[key] = {"size": st.st_size, "mtime_ns": st.st_mtime_ns,
                      "sha256": sha}
        files, done = files + 1, done + st.st_size
        yield progress()
    if fresh:
        cache_path = Path(cache_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, cache_path)
    return shas


def iter_root_hashes(event_dir, sizes, cache_path):
    """{sha256: název} souborů v kořeni akce, jejichž velikost je v `sizes`.

    Na SMB se čte jen málo dat: jen soubory shodné velikosti, hashe se
    cachují (`_iter_hashes`, klíčem je název).
    """
    todo = sorted((t for t in _root_stats(event_dir) if t[2].st_size in sizes),
                  key=lambda t: t[0])
    shas = yield from _iter_hashes(todo, cache_path)
    result = {}
    for name in sorted(shas):
        result.setdefault(shas[name], name)
    return result


def root_hashes(event_dir, sizes, cache_path):
    return _drain(iter_root_hashes(event_dir, sizes, cache_path))


# --- zdroj v `přetřídit` -------------------------------------------------------

def check_source(root, zdroj):
    """Složka zdroje `zdroj` v `root` (`přetřídit`); jen první úroveň bez
    `.ignored`, jinak Refused `neplatny_zdroj`."""
    if (not isinstance(zdroj, str) or not zdroj or "/" in zdroj or "\\" in zdroj or "\0" in zdroj
            or zdroj.startswith(".") or zdroj.endswith(IGNORED)
            or root is None or not (Path(root) / zdroj).is_dir()):
        raise Refused("neplatny_zdroj")
    return Path(root) / zdroj


def source_dirs(folder):
    """Relativní cesty složek zdroje (kořen = ""), bez podsložek
    `.ignored` a jejich obsahu."""
    result = []
    for dirpath, dirnames, _ in os.walk(folder):
        dirnames[:] = sorted(d for d in dirnames if not d.endswith(IGNORED))
        rel = os.path.relpath(dirpath, folder)
        result.append("" if rel == "." else rel.replace(os.sep, "/"))
    return result


def source_entries(folder):
    """Záznamy souborů zdroje jako u nahrané složky: `cesta` =
    `<složka>/<relativní cesta>`, `zdroj` = absolutní cesta, `sha256`
    None (doplní `iter_source_hashes`). `Thumbs.db` a podsložky
    `.ignored` se přeskočí."""
    folder = Path(folder)
    entries = []
    for rel in source_dirs(folder):
        path = folder / rel if rel else folder
        try:
            with os.scandir(path) as it:
                files = [(e.name, e.path, e.stat()) for e in it
                         if e.is_file() and not is_skipped(e.name)]
        except FileNotFoundError:
            continue
        prefix = f"{folder.name}/{rel}/" if rel else f"{folder.name}/"
        for name, full, st in sorted(files):
            entries.append({"nazev": name, "cesta": prefix + name,
                            "zdroj": full, "velikost": st.st_size,
                            "mtime_ns": st.st_mtime_ns, "sha256": None})
    return entries


def source_cache_name(rel):
    """Název cache skenu složky `rel` (cesta pod `přetřídit`, s `/`
    a diakritikou)."""
    return "pretridit-" + hashlib.sha1(rel.encode("utf-8")).hexdigest()


def scan_source(folder, cache_dir, exiftool=None):
    """{cesta: údaje skenu} médií zdroje; sken po složkách s vlastní
    cache (`source_cache_name`)."""
    folder = Path(folder)
    result = {}
    for rel in source_dirs(folder):
        path = folder / rel if rel else folder
        full = f"{folder.name}/{rel}" if rel else folder.name
        try:
            files, _ = scan.scan(path, cache_dir,
                                 exiftool or scan.run_exiftool,
                                 cache_name=source_cache_name(full))
        except FileNotFoundError:
            continue
        for f in files:
            result[f"{full}/{f['nazev']}"] = f
    return result


def iter_source_hashes(entries, event_dir, cache_path):
    """Doplní `sha256` záznamům zdroje; generátor průběhu (`_iter_hashes`).

    Čte se jen soubor, jehož velikost má soubor v kořeni cílové akce nebo
    jiný podporovaný soubor výběru; ostatní dostanou zástupnou hodnotu
    jedinečnou pro záznam (duplicitou být nemohou).
    """
    supported = [e for e in entries if not is_skipped(e["nazev"])
                 and kind(e["nazev"]) != "nepodporovany"]
    counts = Counter(e["velikost"] for e in supported)
    root = {st.st_size for _, _, st in _root_stats(event_dir)} \
        if event_dir is not None else set()
    todo = [e for e in supported
            if counts[e["velikost"]] > 1 or e["velikost"] in root]
    stats = []
    for e in todo:
        try:
            stats.append((e["cesta"], e["zdroj"], os.stat(e["zdroj"])))
        except FileNotFoundError:
            pass
    shas = yield from _iter_hashes(stats, cache_path)
    for e in entries:
        e["sha256"] = shas.get(e["cesta"]) or f"zdroj:{e['cesta']}"
    return entries


def prune_source(path):
    """Smaže odspodu složky zdroje, které jsou prázdné nebo mají jen
    `Thumbs.db`; podsložky `.ignored` se neprocházejí ani nemažou.
    Vrátí True, když zanikla i `path`."""
    try:
        with os.scandir(path) as it:
            items = [(e.name, e.path, e.is_dir(follow_symlinks=False))
                     for e in it]
    except FileNotFoundError:
        return True
    keep = False
    for name, full, is_dir in items:
        if is_dir:
            if name.endswith(IGNORED) or not prune_source(full):
                keep = True
        elif not is_skipped(name):
            keep = True
    if keep:
        return False
    try:
        for name, full, is_dir in items:
            if not is_dir:
                os.unlink(full)
        os.rmdir(path)
    except OSError as err:
        log.warning("import: %s nejde smazat: %s", path, err)
        return False
    log.info("import: smazána vyprázdněná složka %s", path)
    return True


def plan(event_dir, entries, sha_cache=None):
    return _drain(iter_plan(event_dir, entries, sha_cache))


def iter_plan(event_dir, entries, sha_cache=None):
    """Plán importu souborů `entries` (záznamy z `import.json`); generátor
    průběhu porovnání (`iter_root_hashes`), plán vrátí.

    `event_dir` = složka cílové akce, None = nová akce (prázdná). Média jdou
    do kořene, RAWy do `RAW.ignored/`. Duplicita (stejný sha256 jako soubor
    v kořeni akce nebo dřívější soubor výběru) se přeskočí; jméno, které
    v cíli existuje nebo ho má víc souborů výběru, se zablokuje.
    """
    entries = sorted((e for e in entries if not is_skipped(e["nazev"])),
                     key=lambda e: e["cesta"])
    supported = [e for e in entries if kind(e["nazev"]) != "nepodporovany"]
    root_dup, root, raw = {}, set(), set()
    if event_dir is not None:
        sizes = {e["velikost"] for e in supported}
        if sha_cache:
            root_dup = yield from iter_root_hashes(event_dir, sizes,
                                                   sha_cache)
        root = _listing(event_dir)
        raw = _listing(os.path.join(event_dir, RAW_DIR))

    ops, candidates, seen = [], [], {}
    for e in supported:
        dst = f"{RAW_DIR}/{e['nazev']}" if is_raw(e["nazev"]) else e["nazev"]
        o = {"typ": "import", "z": e["cesta"], "do": dst,
             "velikost": e["velikost"], "blocked": False, "duvod": None,
             "stav": OK}
        if e["sha256"] in root_dup:
            o.update(blocked=True, stav=DUPLICATE, duvod="stejný obsah jako "
                     f"{root_dup[e['sha256']]} v akci")
        elif e["sha256"] in seen:
            o.update(blocked=True, stav=DUPLICATE, duvod="stejný obsah jako "
                     f"{seen[e['sha256']]} ve výběru")
        else:
            seen[e["sha256"]] = e["cesta"]
            candidates.append(o)
        ops.append(o)

    names = Counter(_key(o["do"]) for o in candidates)
    for o in candidates:
        in_raw = o["do"].startswith(RAW_DIR + "/")
        name = _key(o["do"].rsplit("/", 1)[-1])
        if names[_key(o["do"])] > 1:
            o.update(blocked=True, stav=BLOCKED,
                     duvod="stejné jméno má jiný soubor výběru")
        elif name in (raw if in_raw else root):
            o.update(blocked=True, stav=BLOCKED, duvod="cíl už existuje")
    return {
        "operace": ops,
        "nepodporovane": [e["cesta"] for e in entries
                          if kind(e["nazev"]) == "nepodporovany"],
    }


# --- skupiny -------------------------------------------------------------------

GROUP_MODES = ("podslozky", "jedna", "auto", "zadne", "existujici")


def _dirs(cesta):
    return re.split(r"[/\\]", cesta)[:-1]


def selection_root(entries):
    """Nejdelší společná složka cest výběru (seznam částí)."""
    paths = [_dirs(e["cesta"]) for e in entries]
    if not paths:
        return []
    root = paths[0]
    for p in paths[1:]:
        n = 0
        while n < len(root) and n < len(p) and root[n] == p[n]:
            n += 1
        root = root[:n]
    return root


def check_groups(volba, existing):
    """Vyhodí Refused, když volbu skupin nejde použít; None = bez skupin."""
    if volba is None:
        return
    if not isinstance(volba, dict) or volba.get("rezim") not in GROUP_MODES:
        raise Refused("neplatne_skupiny")
    if volba["rezim"] == "jedna" and (
            not isinstance(volba.get("nazev"), str)
            or not volba["nazev"].strip()):
        raise Refused("bez_nazvu_skupiny")
    if volba["rezim"] == "existujici" and \
            volba.get("skupina") not in (existing or {}):
        raise Refused("neznama_skupina")


def _group_key(name):
    """Název skupiny k porovnání: bez diakritiky a velikosti písmen."""
    return names._plain(name).strip()


def group_plan(entries, chosen, devices, existing, volba, pripojit=None):
    """Rozdělení médií `chosen` (cesty výběru) do skupin podle `volba`.

    `entries` = všechny nahrané soubory (kořen výběru), `devices` =
    {název: přístroj}, `existing` = skupiny akce (z `_metadata.json` nebo
    návrhu). Vrací {"skupiny": {gid: {nazev, pristroj?}}, "prirazeni":
    {název: gid}, "nove": [gid…], "shody": {nový gid: [existující gid…]}}.
    Nová skupina se k existující připojí jen podle `pripojit`
    ({nový gid: existující gid}); neznámé gid se ignorují.
    """
    existing = existing or {}
    result = {"skupiny": {}, "prirazeni": {}, "nove": [], "shody": {}}
    rezim = (volba or {}).get("rezim", "zadne")
    media = [e for e in entries if e["cesta"] in chosen
             and kind(e["nazev"]) in ("foto", "video")]
    if rezim == "zadne" or not media:
        return result
    if rezim == "existujici":
        gid = volba["skupina"]
        result["skupiny"][gid] = existing[gid]
        result["prirazeni"] = {e["nazev"]: gid for e in media}
        return result

    # Návrh nových skupin: klíč → (název, přístroj), soubor → klíč.
    proposed, members = {}, {}
    if rezim == "auto":
        auto = scan.propose_groups(
            [{"nazev": e["nazev"], "pristroj": devices.get(e["nazev"])}
             for e in media])
        for name, key in auto["prirazeni"].items():
            members[name] = key
        proposed = {k: (g["nazev"], g.get("pristroj"))
                    for k, g in auto["skupiny"].items()}
    else:
        root = selection_root(entries)
        for e in media:
            if rezim == "jedna":
                title = volba["nazev"].strip()
            else:
                rest = _dirs(e["cesta"])[len(root):]
                title = rest[0] if rest else (root[-1] if root else None)
            if title:
                members[e["nazev"]] = title
                proposed[title] = (title, None)

    taken_ids = set(existing)
    taken_names = {_group_key(g.get("nazev") or "") for g in existing.values()}
    gids = {}
    for key in sorted(proposed, key=lambda k: proposed[k][0]):
        title, device = proposed[key]
        new_title, n = title, 2
        while _group_key(new_title) in taken_names:
            new_title, n = f"{title} {n}", n + 1
        taken_names.add(_group_key(new_title))
        base = scan.slug(new_title)
        gid, n = base, 2
        while gid in taken_ids:
            gid, n = f"{base}-{n}", n + 1
        taken_ids.add(gid)
        gids[key] = gid
        group = {"nazev": new_title}
        if device:
            group["pristroj"] = device
        used = {devices.get(name) for name, k in members.items() if k == key}
        result["shody"][gid] = [
            old for old, g in existing.items()
            if _group_key(g.get("nazev") or "") == _group_key(title)
            or (g.get("pristroj") and g["pristroj"] in used)]
        target = (pripojit or {}).get(gid)
        if target in existing:
            result["skupiny"][target] = existing[target]
            gids[key] = target
            del result["shody"][gid]
        else:
            result["skupiny"][gid] = group
            result["nove"].append(gid)
    result["prirazeni"] = {name: gids[key] for name, key in members.items()}
    return result


def plan_groups(plan, entries, devices, existing, volba, done=OK,
                pripojit=None):
    """Skupiny pro média plánu ve stavu `done`; doplní `skupina`
    k operacím a vrátí výsledek `group_plan`."""
    chosen = {o["z"] for o in plan["operace"] if o["stav"] == done}
    groups = group_plan(entries, chosen, devices, existing, volba, pripojit)
    by_path = {e["cesta"]: e["nazev"] for e in entries}
    for o in plan["operace"]:
        o["skupina"] = groups["prirazeni"].get(by_path[o["z"]]) \
            if o["stav"] == done else None
    return groups


def merge_proposal(proposal, groups):
    """Doplní návrh skupin (`skupiny`, `prirazeni`) o výsledek
    `group_plan`; dřívější přiřazení zůstávají."""
    proposal = proposal or {"skupiny": {}, "prirazeni": {}}
    for gid, group in groups["skupiny"].items():
        proposal["skupiny"].setdefault(gid, group)
    for name, gid in groups["prirazeni"].items():
        proposal["prirazeni"].setdefault(name, gid)
    return proposal


def apply_proposal(files, proposal):
    """Návrh skupin akce bez `_metadata.json`: přiřazení z návrhu pro
    soubory v kořeni, ostatním `scan.propose_groups`. Skupiny bez souborů
    vypadnou."""
    def nfc(s):
        return unicodedata.normalize("NFC", s)
    given = {nfc(n): gid for n, gid in proposal["prirazeni"].items()
             if gid in proposal["skupiny"]}
    assignment = {f["nazev"]: given[nfc(f["nazev"])] for f in files
                  if nfc(f["nazev"]) in given}
    auto = scan.propose_groups([f for f in files
                                if f["nazev"] not in assignment])
    groups = {gid: proposal["skupiny"][gid]
              for gid in sorted(set(assignment.values()))}
    rename = {}
    for gid, group in auto["skupiny"].items():
        new, n = gid, 2
        while new in groups:
            new, n = f"{gid}-{n}", n + 1
        rename[gid] = new
        groups[new] = group
    for name, gid in auto["prirazeni"].items():
        assignment[name] = rename[gid]
    return {"skupiny": groups, "prirazeni": assignment}


def purge_tmp(event_dir, max_age=TMP_AGE):
    """Smaže `.import-*.tmp` starší než `max_age` v kořeni akce
    a v `RAW.ignored/` (zbytky po výpadku SMB); vrátí jejich cesty.

    Volá se jen se zámkem akce, takže čerstvý dočasný soubor patří jen
    souběžnému importu, který zámek vylučuje; hodina kryje nepřesné
    hodiny SMB.
    """
    removed, now = [], time.time()
    for sub in ("", RAW_DIR):
        try:
            with os.scandir(os.path.join(event_dir, sub)) as it:
                old = [e for e in it if e.name.startswith(IMPORT_TMP_PREFIX)
                       and e.name.endswith(".tmp") and e.is_file()
                       and now - e.stat().st_mtime > max_age]
        except FileNotFoundError:
            continue
        for e in sorted(old, key=lambda e: e.name):
            rel = f"{sub}/{e.name}" if sub else e.name
            try:
                os.unlink(e.path)
            except OSError as err:
                log.warning("import %s: %s nejde smazat: %s",
                            os.path.basename(event_dir), rel, err)
                continue
            log.info("import %s: smazán starý dočasný soubor %s",
                     os.path.basename(event_dir), rel)
            removed.append(rel)
    return removed


def _copy(src, event_dir, dst, sha, mtime_ns):
    """Kopie ze stagingu do akce, která nikdy nepřepíše existující cíl.

    Generátor: po každých `STEP` bajtech vydá počet zkopírovaných.
    Zavření uprostřed smaže dočasný soubor."""
    dst_path = os.path.join(event_dir, dst)
    target_dir = os.path.dirname(dst_path)
    if os.path.basename(target_dir) == RAW_DIR and \
            not os.path.isdir(target_dir):
        os.mkdir(target_dir)
    # Staging a archiv jsou na různých souborových systémech: kopie do
    # dočasného jména vedle cíle, pak přejmenování. Ne mkstemp: ten
    # zakládá 0600, práva mají jít podle umask jako u běžné kopie.
    tmp = os.path.join(target_dir, f"{IMPORT_TMP_PREFIX}"
                       f"{secrets.token_hex(8)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    try:
        digest, done, reported = hashlib.sha256(), 0, 0
        with open(src, "rb") as fin, os.fdopen(fd, "wb") as fout:
            while chunk := fin.read(CHUNK):
                fout.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if done - reported >= STEP:
                    # Na SMB zápis končí v cache jádra: průběh hlásit až po
                    # fsync, jinak ukazatel předběhne přenos a přerušení
                    # čeká na odeslání celé cache.
                    fout.flush()
                    os.fsync(fout.fileno())
                    reported = done
                    yield done
            fout.flush()
            os.fsync(fout.fileno())
        if digest.hexdigest() != sha:
            raise OSError("obsah nahraného souboru se změnil")
        os.utime(tmp, ns=(mtime_ns, mtime_ns))
        # os.rename na Linuxu cíl přepíše: kontrola těsně před ním jako
        # v cleanup._move, souběh vylučuje zámek akce.
        if _key(os.path.basename(dst_path)) in _listing(target_dir):
            raise Blocked("cíl už existuje")
        os.rename(tmp, dst_path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _move(src, event_dir, dst):
    """Přesun ze zdroje do akce přejmenováním, které nikdy nepřepíše
    existující cíl; obsah i mtime zůstanou. Generátor bez průběhu."""
    if False:
        yield
    try:
        os.lstat(src)
    except FileNotFoundError:
        raise OSError("soubor ve zdroji už není") from None
    dst_path = os.path.join(event_dir, dst)
    target_dir = os.path.dirname(dst_path)
    if os.path.basename(target_dir) == RAW_DIR and \
            not os.path.isdir(target_dir):
        os.mkdir(target_dir)
    # os.rename na Linuxu cíl přepíše: kontrola těsně před ním jako
    # v cleanup._move, souběh v akci vylučuje zámek akce. Jiný svazek
    # (EXDEV) je chyba souboru, kopie se nedělá.
    if _key(os.path.basename(dst_path)) in _listing(target_dir):
        raise Blocked("cíl už existuje")
    os.rename(src, dst_path)


def copy_from(staging):
    """Přenos kopií ze stagingu (`_copy`)."""
    def transfer(entry, event_dir, dst):
        return _copy(Path(staging) / entry["ulozeno"], event_dir, dst,
                     entry["sha256"], entry["mtime_ns"])
    return transfer


def move_from_source(entry, event_dir, dst):
    """Přenos přesunem ze zdroje (`_move`)."""
    return _move(entry["zdroj"], event_dir, dst)


def execute(event_dir, entries, transfer, sha_cache=None):
    """Sestaví plán znovu a přenese jeho neblokované soubory.

    `transfer(záznam, akce, cíl)` = generátor přenosu (`copy_from`,
    `move_from_source`). Generátor událostí: průběh porovnání
    (`iter_plan`), `start` (kolik souborů a bajtů se přenese), `prubeh`
    (bajty souboru `z`, po `STEP`; jen u kopie), `soubor` (operace
    s výsledným stavem, po každém souboru) a nakonec `vysledek` (plán se
    `stav` hotovo / blokovano / duplicita / chyba a `chyba`, `smazano` =
    staré dočasné soubory). Selhání jednoho souboru ostatní nezastaví.
    Záznam s `po_planu` (zdroj: `zmizel` / `zmenil` od plánu) skončí
    jako chyba / blokovaný bez přenosu.
    """
    removed = purge_tmp(event_dir)
    result = yield from iter_plan(event_dir, entries, sha_cache)
    by_path = {e["cesta"]: e for e in entries}
    todo = [o for o in result["operace"] if not o["blocked"]]
    yield {"typ": "start", "souboru": len(todo),
           "bajtu": sum(o["velikost"] for o in todo)}
    for o in result["operace"]:
        o["chyba"] = None
        if o["stav"] != DUPLICATE:
            entry = by_path[o["z"]]
            try:
                if entry.get("po_planu") == "zmizel":
                    raise OSError("ve zdroji už není")
                if entry.get("po_planu") == "zmenil":
                    raise Blocked("změnil se po plánu")
                if o["blocked"]:
                    raise Blocked(o["duvod"])
                yield from _relay(
                    transfer(entry, event_dir, o["do"]),
                    lambda n: {"typ": "prubeh", "z": o["z"], "bajtu": n})
                o["stav"] = DONE
            except Blocked as e:
                o["stav"], o["duvod"] = BLOCKED, str(e)
            except OSError as e:
                o["stav"], o["chyba"] = FAILED, str(e)
            log.info("import %s: %s → %s: %s %s",
                     os.path.basename(event_dir), o["z"], o["do"], o["stav"],
                     o["chyba"] or o["duvod"] or "")
        yield {"typ": "soubor", "operace": o}
    yield dict(result, typ="vysledek", smazano=removed)


# --- staging -------------------------------------------------------------------

class Imports:
    """Rozpracované importy v `work/import/<id>/`.

    `import.json` drží jméno vlastníka, časy založení a poslední aktivity,
    zamýšlený cíl a nahrané soubory (cesta ve výběru, uložené jméno,
    velikost, mtime, sha256). Soubor se do něj zapíše až po úplném
    nahrání. Import patří jménu (porovnání jako u návrhů jmen), ne
    záložce; cizí se chová jako neexistující. Probíhající provedení
    drží příznak v paměti (server je jeden proces).

    Import se zdrojem má v `import.json` místo souborů `zdroj` (složka
    v `source_root`, tj. `přetřídit`); záznamy souborů se sestaví při
    každém přehledu, plánu i provedení znovu (`source_entries`).
    """

    def __init__(self, work, clock=time.time, disk_usage=shutil.disk_usage,
                 source_root=None):
        self.work = Path(work)
        self.root = self.work / "import"
        self.source_root = Path(source_root) if source_root else None
        self.clock = clock
        self.disk_usage = disk_usage
        self._mutex = threading.Lock()
        self._running = {}  # id → relace (záložka), která provádí
        self._uploads = {}  # id → {token: rozpracované nahrávání}

    def dir(self, id):
        if not isinstance(id, str) or not ID_RE.match(id):
            raise KeyError(id)
        path = self.root / id
        if not (path / RECORD).is_file():
            raise KeyError(id)
        return path

    def _write(self, path, record):
        tmp = path / (RECORD + ".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tmp, path / RECORD)

    @staticmethod
    def _owner(jmeno):
        return names.normalize(jmeno) if isinstance(jmeno, str) else ""

    def get(self, id, jmeno):
        """Záznam importu uživatele; cizí nebo neexistující vyhodí
        KeyError."""
        try:
            record = json.loads((self.dir(id) / RECORD).read_text("utf-8"))
        except (FileNotFoundError, ValueError):
            raise KeyError(id) from None
        owner = self._owner(jmeno)
        if not owner or self._owner(record.get("jmeno")) != owner:
            raise KeyError(id)
        return record

    def check_idle(self, id):
        """Vyhodí Refused `probiha`, když se import právě provádí."""
        if id in self._running:
            raise Refused("probiha")

    def source(self, record):
        """Složka zdroje importu, nebo None (nahrané soubory)."""
        if not record.get("zdroj") or self.source_root is None:
            return None
        return self.source_root / record["zdroj"]

    def entries(self, record):
        """Záznamy souborů importu: nahrané, nebo aktuální obsah zdroje
        (bez `sha256`, viz `iter_entries`)."""
        if record.get("zdroj"):
            folder = self.source(record)
            return source_entries(folder) if folder else []
        return record["soubory"]

    @staticmethod
    def _snapshot(entries):
        return [{"cesta": e["cesta"], "velikost": e["velikost"],
                 "mtime_ns": e["mtime_ns"]} for e in entries]

    def _against_plan(self, record, entries):
        """Záznamy zdroje proti snímku posledního plánu: (záznamy k plánu,
        cesty přibylé po plánu). Zmizelé se vrátí se `po_planu` =
        `zmizel`, změněné (velikost, mtime) se `zmenil`."""
        snap = {s["cesta"]: s for s in record["plan_zdroj"]}
        current = {e["cesta"]: e for e in entries}
        result, added = [], []
        for e in entries:
            old = snap.get(e["cesta"])
            if old is None:
                added.append(e["cesta"])
                continue
            if (old["velikost"], old["mtime_ns"]) != \
                    (e["velikost"], e["mtime_ns"]):
                e["po_planu"] = "zmenil"
            result.append(e)
        for cesta, old in snap.items():
            if cesta not in current:
                result.append(dict(old, nazev=cesta.rsplit("/", 1)[-1],
                                   zdroj=str(self.source_root / cesta),
                                   sha256=None, po_planu="zmizel"))
        return result, sorted(added)

    def _set_snapshot(self, id, jmeno, snapshot):
        with self._mutex:
            record = self.get(id, jmeno)
            record["plan_zdroj"] = snapshot
            self._write(self.dir(id), record)

    def check_plan(self, record):
        """Import se zdrojem jde provést jen se snímkem plánu."""
        if record.get("zdroj") and self.source(record) is None:
            raise Refused("neplatny_zdroj")
        if record.get("zdroj") and record.get("plan_zdroj") is None:
            raise Refused("bez_planu")

    def iter_entries(self, record, event_dir):
        """`entries` s `sha256`; u zdroje generátor průběhu hashování."""
        entries = self.entries(record)
        if record.get("zdroj"):
            cache = self.work / "cache" / "sha256" / \
                f"{source_cache_name(UNSORTED + '/' + record['zdroj'])}.json"
            yield from iter_source_hashes(entries, event_dir, cache)
        return entries

    def owned(self, jmeno):
        """Rozpracované importy uživatele, nejnovější aktivita první."""
        result = []
        if not self.root.is_dir():
            return result
        for path in self.root.iterdir():
            try:
                record = self.get(path.name, jmeno)
            except KeyError:
                continue
            files = self.entries(record)
            result.append({
                "id": path.name, "zalozeno": record["zalozeno"],
                "aktivita": record["aktivita"], "souboru": len(files),
                "velikost": sum(s["velikost"] for s in files),
                "cil": record.get("cil"), "nova": record.get("nova", False),
                "zdroj": record.get("zdroj"),
                "probiha": path.name in self._running,
                "nahrava": bool(self._uploads.get(path.name))})
        return sorted(result, key=lambda i: -i["aktivita"])

    def check_space(self, size):
        free = self.disk_usage(self.root).free
        if size + RESERVE > free:
            raise Refused("malo_mista", volno=free)

    def create(self, jmeno, celkem=0, zdroj=None, cil=None, nova=False):
        """Založí import; `celkem` = součet velikostí ohlášený klientem.

        Se `zdrojem` (složka v `přetřídit`) se nic nenahrává; rozpracovaný
        import téže složky uživatele se vrátí místo nového. `cil` a `nova`
        = zamýšlený cíl (jako `set_target`)."""
        self.root.mkdir(parents=True, exist_ok=True)
        if zdroj is not None:
            check_source(self.source_root, zdroj)
            with self._mutex:
                for item in self.owned(jmeno):
                    if item["zdroj"] == zdroj:
                        return item["id"]
                return self._new(jmeno, zdroj=zdroj, cil=cil, nova=nova)
        self.check_space(celkem)
        return self._new(jmeno)

    def _new(self, jmeno, zdroj=None, cil=None, nova=False):
        id = secrets.token_urlsafe(16)
        path = self.root / id
        if zdroj is None:
            (path / FILES_DIR).mkdir(parents=True)
        else:
            path.mkdir()
        now = self.clock()
        record = {"jmeno": jmeno, "zalozeno": now, "aktivita": now,
                  "cil": cil, "nova": bool(nova), "soubory": []}
        if zdroj is not None:
            record["zdroj"] = zdroj
        self._write(path, record)
        return id

    def activity(self, id, relace):
        """Co s importem právě dělají jiné záložky než `relace`."""
        uploads = [{"cesta": u["cesta"], "prijato": u["prijato"],
                    "velikost": u["velikost"]}
                   for u in list(self._uploads.get(id, {}).values())
                   if u["relace"] != relace]
        return {"nahrava": sorted(uploads, key=lambda u: u["cesta"]),
                "probiha": id in self._running
                and self._running[id] != relace}

    def add_file(self, id, jmeno, cesta, stream, length, mtime_ms=None,
                 relace=None):
        """Uloží jeden nahraný soubor ze streamu; vrátí jeho záznam.

        Zapisuje do dočasného jména, do `import.json` jde až úplný soubor.
        Stejná `cesta` nahraná znovu nahradí předchozí. `Thumbs.db` se
        zahodí (None). Během provedení importu odmítne (`probiha`).
        """
        if self.get(id, jmeno).get("zdroj"):
            raise Refused("ma_zdroj")
        self.check_idle(id)
        name = flat_name(cesta)
        if length is None:
            raise Refused("bez_delky")
        if length > MAX_FILE:
            raise Refused("prilis_velky", limit=MAX_FILE)
        path = self.dir(id)
        if is_skipped(name):
            while stream.read(CHUNK):
                pass
            return None
        self.check_space(length)
        fd, tmp = tempfile.mkstemp(dir=path / FILES_DIR,
                                   prefix=IMPORT_TMP_PREFIX, suffix=".tmp")
        # Rozpracované nahrávání vidí jiné záložky (`activity`).
        token = object()
        progress = {"relace": relace, "cesta": cesta, "prijato": 0,
                    "velikost": length}
        with self._mutex:
            self._uploads.setdefault(id, {})[token] = progress
        try:
            digest, size = hashlib.sha256(), 0
            with os.fdopen(fd, "wb") as f:
                while size <= length and (chunk := stream.read(CHUNK)):
                    f.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                    progress["prijato"] = size
            if size != length:
                raise Refused("neuplny")
            if mtime_ms is not None:
                ns = int(mtime_ms) * 1_000_000
                os.utime(tmp, ns=(ns, ns))
            with self._mutex:
                record = self.get(id, jmeno)
                self.check_idle(id)
                for old in [s for s in record["soubory"]
                            if s["cesta"] == cesta]:
                    record["soubory"].remove(old)
                    (path / old["ulozeno"]).unlink(missing_ok=True)
                taken = {_key(s["nazev"]) for s in record["soubory"]
                         if s["ulozeno"] == f"{FILES_DIR}/{s['nazev']}"}
                if _key(name) in taken:
                    n = 1
                    while (path / OTHER_DIR / str(n)).exists():
                        n += 1
                    stored = f"{OTHER_DIR}/{n}/{name}"
                    (path / OTHER_DIR / str(n)).mkdir(parents=True)
                else:
                    stored = f"{FILES_DIR}/{name}"
                os.replace(tmp, path / stored)
                entry = {"nazev": name, "cesta": cesta, "ulozeno": stored,
                         "velikost": size,
                         "mtime_ns": os.stat(path / stored).st_mtime_ns,
                         "sha256": digest.hexdigest()}
                record["soubory"].append(entry)
                record["aktivita"] = self.clock()
                self._write(path, record)
        finally:
            Path(tmp).unlink(missing_ok=True)
            with self._mutex:
                uploads = self._uploads.get(id, {})
                uploads.pop(token, None)
                if not uploads:
                    self._uploads.pop(id, None)
        return entry

    def _remove(self, id):
        shutil.rmtree(self.root / id, ignore_errors=True)
        (self.work / "cache" / "scan" / f"import-{id}.json").unlink(
            missing_ok=True)

    def discard(self, id, jmeno):
        self.get(id, jmeno)
        with self._mutex:
            self.check_idle(id)
            self._remove(id)

    def purge(self, max_age=MAX_AGE):
        """Smaže importy neaktivní déle než `max_age`; vrátí jejich id."""
        removed = []
        if not self.root.is_dir():
            return removed
        now = self.clock()
        for path in self.root.iterdir():
            if not path.is_dir():
                continue
            try:
                record = json.loads((path / RECORD).read_text("utf-8"))
                last = record["aktivita"]
            except (OSError, ValueError, KeyError, TypeError):
                last = path.stat().st_mtime
            if now - last > max_age:
                self._remove(path.name)
                removed.append(path.name)
        return removed

    def _scanned(self, id, record, exiftool=None):
        """{cesta: údaje skenu} souborů importu (cache exiftoolu); nahrané
        jen ze `soubory/` (ne z `kolize/`)."""
        if record.get("zdroj"):
            folder = self.source(record)
            return scan_source(folder, self.work / "cache", exiftool) \
                if folder else {}
        files, _ = scan.scan(self.dir(id) / FILES_DIR, self.work / "cache",
                             exiftool or scan.run_exiftool,
                             cache_name=f"import-{id}")
        data = {f["nazev"]: f for f in files}
        return {s["cesta"]: data[s["nazev"]] for s in record["soubory"]
                if s["ulozeno"] == f"{FILES_DIR}/{s['nazev']}"
                and s["nazev"] in data}

    def devices(self, id, record, exiftool=None):
        """{název: přístroj} pro skupiny (klíčem je zploštělé jméno)."""
        by_path = {s["cesta"]: s["nazev"] for s in self.entries(record)}
        return {by_path[c]: f["pristroj"] for c, f
                in self._scanned(id, record, exiftool).items()
                if f.get("pristroj") and c in by_path}

    def overview(self, id, jmeno, exiftool=None, relace=None):
        """Přehled souborů importu: typy, data a přístroje z EXIF;
        `jinde` = co s importem dělají jiné záložky než `relace`."""
        record = self.get(id, jmeno)
        data = self._scanned(id, record, exiftool)
        items = []
        for s in sorted(self.entries(record), key=lambda s: s["cesta"]):
            d = data.get(s["cesta"])
            items.append({"nazev": s["nazev"], "cesta": s["cesta"],
                          "typ": kind(s["nazev"]), "velikost": s["velikost"],
                          "datum": d and d["datum"],
                          "pristroj": d and d["pristroj"]})
        days = sorted(i["datum"][:10] for i in items if i["datum"])
        return {
            "id": id,
            "soubory": items,
            "pocty": dict(Counter(i["typ"] for i in items)),
            "od": days[0] if days else None,
            "do": days[-1] if days else None,
            "pristroje": sorted({i["pristroj"] for i in items
                                 if i["pristroj"]}),
            "nepodporovane": [i["cesta"] for i in items
                              if i["typ"] == "nepodporovany"],
            "cil": record.get("cil"),
            "nova": record.get("nova", False),
            "skupiny": record.get("skupiny"),
            "zdroj": record.get("zdroj"),
            "jinde": self.activity(id, relace),
        }

    def sha_cache(self, event_dir):
        if event_dir is None:
            return None
        return self.work / "cache" / "sha256" / f"{Path(event_dir).name}.json"

    def set_target(self, id, jmeno, cil, nova, skupiny=None):
        """Uloží zamýšlený cíl (název akce, nová?) a volbu skupin pro
        návrat k importu."""
        with self._mutex:
            record = self.get(id, jmeno)
            record.update(cil=cil, nova=bool(nova), skupiny=skupiny,
                          aktivita=self.clock())
            self._write(self.dir(id), record)

    def plan(self, id, jmeno, event_dir, existing=None, volba=None):
        """Generátor průběhu porovnání, nakonec událost `plan` se
        `skupina` u operací a `skupiny` (`nove` s `shody`, `existujici`)."""
        record = self.get(id, jmeno)
        devices = self.devices(id, record) if volba else {}
        entries = yield from self.iter_entries(record, event_dir)
        if record.get("zdroj"):
            # Měřítko provedení: co plán ukázal (`_against_plan`).
            self._set_snapshot(id, jmeno, self._snapshot(entries))
        result = yield from iter_plan(event_dir, entries,
                                      self.sha_cache(event_dir))
        groups = plan_groups(result, entries, devices, existing, volba)
        yield dict(result, typ="plan", skupiny={
            "nove": {gid: dict(groups["skupiny"][gid],
                               shody=groups["shody"][gid])
                     for gid in groups["nove"]},
            "existujici": existing or {}})

    def execute(self, id, jmeno, event_dir, relace=None, existing=None,
                volba=None, pripojit=None):
        """Generátor událostí provedení (`execute`); přenesený soubor
        zmizí ze stagingu hned po přenosu, prázdný staging se na konci
        smaže. `vysledek` nese `skupina` u operací a `skupiny` (výsledek
        `group_plan` pro přenesená média). Odmítnutí (`probiha`, cizí
        import) vyhodí už první `next()`; zavření generátoru příznak
        provádění uvolní.

        Import se zdrojem soubory přesune (`move_from_source`); po
        provedení se zdroj uklidí (`prune_source`) a `vysledek` nese
        `zdroj_zbyva` (počty zbylých souborů podle typu) a `zdroj_smazan`.
        Import bez zbylých podporovaných souborů ve zdroji se zruší.

        Měřítkem je snímek posledního plánu (`_against_plan`): přibylé
        soubory se nepřesunou a `vysledek` je nese v `po_planu`; bez
        snímku Refused `bez_planu`. Provedení snímek spotřebuje."""
        record = self.get(id, jmeno)
        path = self.dir(id)
        folder = self.source(record)
        self.check_plan(record)
        with self._mutex:
            self.check_idle(id)
            self._running[id] = relace
        try:
            # Přístroje před přenosem: přenesené soubory ze stagingu zmizí.
            devices = self.devices(id, record) if volba else {}
            entries = yield from self.iter_entries(record, event_dir)
            added = []
            if folder:
                entries, added = self._against_plan(record, entries)
            by_path = {e["cesta"]: e for e in entries}
            transfer = move_from_source if folder else copy_from(path)
            for event in execute(event_dir, entries, transfer,
                                 self.sha_cache(event_dir)):
                if event["typ"] == "soubor" and \
                        event["operace"]["stav"] == DONE and not folder:
                    self._moved(id, jmeno, by_path[event["operace"]["z"]])
                elif event["typ"] == "vysledek":
                    event["skupiny"] = plan_groups(
                        event, entries, devices, existing, volba,
                        DONE, pripojit)
                    if folder:
                        event["po_planu"] = added
                        self._source_result(id, jmeno, folder, event)
                    else:
                        with self._mutex:
                            left = self.get(id, jmeno)["soubory"]
                            event["zahozeno"] = not left
                            if not left:
                                self._remove(id)
                yield event
        finally:
            self._running.pop(id, None)

    def _source_result(self, id, jmeno, folder, event):
        """Úklid zdroje po provedení; doplní `zdroj_zbyva`,
        `zdroj_smazan` a `zahozeno` do výsledku."""
        gone = prune_source(folder)
        left = [] if gone else source_entries(folder)
        event["zdroj_smazan"] = gone
        event["zdroj_zbyva"] = dict(Counter(kind(e["nazev"]) for e in left))
        keep = any(kind(e["nazev"]) != "nepodporovany" for e in left)
        with self._mutex:
            event["zahozeno"] = not keep
            if keep:
                record = self.get(id, jmeno)
                record["aktivita"] = self.clock()
                record.pop("plan_zdroj", None)  # další provedení = nový plán
                self._write(self.dir(id), record)
            else:
                self._remove(id)

    # --- návrh skupin akce bez `_metadata.json` ---

    def _proposal_path(self, akce):
        return self.work / PROPOSALS / f"{akce}.json"

    def proposal(self, akce):
        """Návrh skupin z importu ({skupiny, prirazeni}), nebo None."""
        try:
            return json.loads(self._proposal_path(akce)
                              .read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return None

    def add_proposal(self, akce, groups):
        """Doplní návrh akce o skupiny importu (`group_plan`)."""
        path = self._proposal_path(akce)
        with self._mutex:
            proposal = merge_proposal(self.proposal(akce), groups)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(proposal, ensure_ascii=False, indent=1),
                           encoding="utf-8")
            os.replace(tmp, path)

    def drop_proposal(self, akce):
        self._proposal_path(akce).unlink(missing_ok=True)

    def _moved(self, id, jmeno, entry):
        """Odebere přenesený soubor ze stagingu i z `import.json`."""
        with self._mutex:
            path = self.dir(id)
            record = self.get(id, jmeno)
            (path / entry["ulozeno"]).unlink(missing_ok=True)
            record["soubory"] = [s for s in record["soubory"]
                                 if s["cesta"] != entry["cesta"]]
            record["aktivita"] = self.clock()
            self._write(path, record)
