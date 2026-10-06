"""Import fotek a videí do archivu přes prohlížeč.

Nahrané soubory čekají v pracovním adresáři (`work/import/<id>/`), do
archivu se před potvrzením nic nezapíše. Plán má tvar plánu úklidu
(operace s `blocked` a `duvod`), navíc `stav` ok / blokovano / duplicita.
`execute` plán sestaví znovu a soubory zkopíruje bez přepsání: dočasný
`.import-*.tmp` v cílové složce, kontrola cíle těsně před přejmenováním.
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
from collections import Counter
from datetime import date
from pathlib import Path

from . import scan
from .archive import EVENT_RE, IMPORT_TMP_PREFIX, is_metadata, is_skipped
from .cleanup import BLOCKED, DONE, FAILED, RAW_DIR, Blocked, _key, is_raw

log = logging.getLogger(__name__)

FILES_DIR = "soubory"
# Soubor, jehož jméno už ve `soubory/` je (jiná podsložka výběru); v plánu
# se zablokuje, ale uživatel ho v přehledu uvidí.
OTHER_DIR = "kolize"
RECORD = "import.json"
MAX_FILE = 20 * 2**30
RESERVE = 2**30          # volné místo, které nahrávání na disku nechá
MAX_AGE = 7 * 24 * 3600  # neaktivní importy se při startu smažou
CHUNK = 1 << 20
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


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


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


def root_hashes(event_dir, sizes, cache_path):
    """{sha256: název} souborů v kořeni akce, jejichž velikost je v `sizes`.

    Na SMB se čte jen málo dat: jen soubory shodné velikosti, hashe se
    cachují podle (název, velikost, mtime).
    """
    try:
        cache = json.loads(Path(cache_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        cache = {}
    result, changed = {}, False
    with os.scandir(event_dir) as it:
        entries = sorted((e for e in it if e.is_file()), key=lambda e: e.name)
    for e in entries:
        if is_skipped(e.name) or is_metadata(e.name):
            continue
        st = e.stat()
        if st.st_size not in sizes:
            continue
        hit = cache.get(e.name)
        if hit and hit["size"] == st.st_size and \
                hit["mtime_ns"] == st.st_mtime_ns:
            sha = hit["sha256"]
        else:
            sha = file_sha256(e.path)
            cache[e.name] = {"size": st.st_size, "mtime_ns": st.st_mtime_ns,
                             "sha256": sha}
            changed = True
        result.setdefault(sha, e.name)
    if changed:
        cache_path = Path(cache_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, cache_path)
    return result


def plan(event_dir, entries, sha_cache=None):
    """Plán importu souborů `entries` (záznamy z `import.json`).

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
        root_dup = root_hashes(event_dir, sizes, sha_cache) if sha_cache \
            else {}
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


def _copy(src, event_dir, dst, sha, mtime_ns):
    """Kopie ze stagingu do akce, která nikdy nepřepíše existující cíl."""
    dst_path = os.path.join(event_dir, dst)
    target_dir = os.path.dirname(dst_path)
    if os.path.basename(target_dir) == RAW_DIR and \
            not os.path.isdir(target_dir):
        os.mkdir(target_dir)
    # Staging a archiv jsou na různých souborových systémech: kopie do
    # dočasného jména vedle cíle, pak přejmenování.
    fd, tmp = tempfile.mkstemp(dir=target_dir, prefix=IMPORT_TMP_PREFIX,
                               suffix=".tmp")
    try:
        digest = hashlib.sha256()
        with open(src, "rb") as fin, os.fdopen(fd, "wb") as fout:
            while chunk := fin.read(CHUNK):
                fout.write(chunk)
                digest.update(chunk)
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


def execute(event_dir, entries, staging, sha_cache=None):
    """Sestaví plán znovu a zkopíruje jeho neblokované soubory.

    Vrátí (výsledek, přenesené záznamy). Operace dostanou `stav` hotovo /
    blokovano / duplicita / chyba a `chyba`; selhání jednoho souboru
    ostatní nezastaví.
    """
    result = plan(event_dir, entries, sha_cache)
    by_path = {e["cesta"]: e for e in entries}
    done = []
    for o in result["operace"]:
        o["chyba"] = None
        if o["stav"] == DUPLICATE:
            continue
        entry = by_path[o["z"]]
        try:
            if o["blocked"]:
                raise Blocked(o["duvod"])
            _copy(Path(staging) / entry["ulozeno"], event_dir, o["do"],
                  entry["sha256"], entry["mtime_ns"])
            o["stav"] = DONE
            done.append(entry)
        except Blocked as e:
            o["stav"], o["duvod"] = BLOCKED, str(e)
        except OSError as e:
            o["stav"], o["chyba"] = FAILED, str(e)
        log.info("import %s: %s → %s: %s %s", os.path.basename(event_dir),
                 o["z"], o["do"], o["stav"], o["chyba"] or o["duvod"] or "")
    return result, done


# --- staging -------------------------------------------------------------------

class Imports:
    """Rozpracované importy v `work/import/<id>/`.

    `import.json` drží relaci, jméno, čas poslední aktivity a nahrané
    soubory (cesta ve výběru, uložené jméno, velikost, mtime, sha256).
    Soubor se do něj zapíše až po úplném nahrání.
    """

    def __init__(self, work, clock=time.time, disk_usage=shutil.disk_usage):
        self.work = Path(work)
        self.root = self.work / "import"
        self.clock = clock
        self.disk_usage = disk_usage
        self._mutex = threading.Lock()

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

    def get(self, id, relace):
        """Záznam importu relace; cizí nebo neexistující vyhodí KeyError."""
        try:
            record = json.loads((self.dir(id) / RECORD).read_text("utf-8"))
        except (FileNotFoundError, ValueError):
            raise KeyError(id) from None
        if not relace or record.get("relace") != relace:
            raise KeyError(id)
        return record

    def check_space(self, size):
        free = self.disk_usage(self.root).free
        if size + RESERVE > free:
            raise Refused("malo_mista", volno=free)

    def create(self, relace, jmeno, celkem=0):
        """Založí import; `celkem` = součet velikostí ohlášený klientem."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.check_space(celkem)
        id = secrets.token_urlsafe(16)
        path = self.root / id
        (path / FILES_DIR).mkdir(parents=True)
        now = self.clock()
        self._write(path, {"relace": relace, "jmeno": jmeno,
                           "zalozeno": now, "aktivita": now, "soubory": []})
        return id

    def add_file(self, id, relace, cesta, stream, length, mtime_ms=None):
        """Uloží jeden nahraný soubor ze streamu; vrátí jeho záznam.

        Zapisuje do dočasného jména, do `import.json` jde až úplný soubor.
        Stejná `cesta` nahraná znovu nahradí předchozí. `Thumbs.db` se
        zahodí (None).
        """
        self.get(id, relace)
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
        try:
            digest, size = hashlib.sha256(), 0
            with os.fdopen(fd, "wb") as f:
                while size <= length and (chunk := stream.read(CHUNK)):
                    f.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            if size != length:
                raise Refused("neuplny")
            if mtime_ms is not None:
                ns = int(mtime_ms) * 1_000_000
                os.utime(tmp, ns=(ns, ns))
            with self._mutex:
                record = self.get(id, relace)
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
        return entry

    def _remove(self, id):
        shutil.rmtree(self.root / id, ignore_errors=True)
        (self.work / "cache" / "scan" / f"import-{id}.json").unlink(
            missing_ok=True)

    def discard(self, id, relace):
        self.get(id, relace)
        with self._mutex:
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

    def overview(self, id, relace, exiftool=scan.run_exiftool):
        """Přehled nahraných souborů: typy, data a přístroje z EXIF."""
        record = self.get(id, relace)
        path = self.dir(id)
        files, _ = scan.scan(path / FILES_DIR, self.work / "cache", exiftool,
                             cache_name=f"import-{id}")
        data = {f["nazev"]: f for f in files}
        items = []
        for s in sorted(record["soubory"], key=lambda s: s["cesta"]):
            d = data.get(s["nazev"]) \
                if s["ulozeno"] == f"{FILES_DIR}/{s['nazev']}" else None
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
        }

    def sha_cache(self, event_dir):
        if event_dir is None:
            return None
        return self.work / "cache" / "sha256" / f"{Path(event_dir).name}.json"

    def plan(self, id, relace, event_dir):
        record = self.get(id, relace)
        return plan(event_dir, record["soubory"], self.sha_cache(event_dir))

    def execute(self, id, relace, event_dir):
        """Provede import; přenesené soubory zmizí ze stagingu, prázdný
        staging se smaže."""
        record = self.get(id, relace)
        path = self.dir(id)
        result, done = execute(event_dir, record["soubory"], path,
                               self.sha_cache(event_dir))
        with self._mutex:
            record = self.get(id, relace)
            moved = {e["cesta"] for e in done}
            for e in done:
                (path / e["ulozeno"]).unlink(missing_ok=True)
            record["soubory"] = [s for s in record["soubory"]
                                 if s["cesta"] not in moved]
            record["aktivita"] = self.clock()
            result["zahozeno"] = not record["soubory"]
            if record["soubory"]:
                self._write(path, record)
            else:
                self._remove(id)
        return result
