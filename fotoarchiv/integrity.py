"""Kontrola, zda soubor média není poškozený (issue #10).

Typická vada archivu: bloky souboru vynulované na kartě nebo v souborovém
systému, délka souboru zůstala. Dekodér obrázků nuly uprostřed často
přijme jako platná data (šedý pruh), proto hlavní kontrolou je test
souvislého úseku nul zarovnaného na blok 4 KiB; doplňuje ho dekódování
fotky (useknutý soubor) a `ffprobe` u videa.

Soubor se čte jednou: tentýž průchod spočítá i sha256 (pro plán importu).
U videa MP4/MOV se nuly počítají jen v datech obrazové stopy (`mp4`):
výplňové atomy a ticho v nekomprimovaném zvuku PCM jsou dlouhé úseky
nul ve zdravém souboru. Když tabulky vzorků nejdou přečíst, test běží
přes celý soubor.

Výsledek: `stav` ok / podezrely / necitelny, `duvody` (česky, pro
uživatele), `nuly` = nejdelší započítaný zarovnaný úsek nul (`delka`,
`od`) nebo None, u videa s přečtenými tabulkami `nuly_rozsah` = "obraz"
a `nuly_soubor` = nejdelší úsek v celém souboru, případně `poznamka`.
Archiv se jen čte; cache je v pracovním adresáři.
"""

import hashlib
import io
import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

from PIL import Image

from . import mp4

OK = "ok"
SUSPECT = "podezrely"
UNREADABLE = "necitelny"

BLOCK = 4096              # zarovnání úseku nul (blok souborového systému)
THRESHOLD = 64 * 1024     # od kolika bajtů souvislých nul je soubor podezřelý
CHUNK = 256 * BLOCK       # čtení po 1 MiB (násobek bloku)
STEP = 64 * 2**20         # průběh i uvnitř velkých souborů
PREVIEW = 1600            # měřítko dekódování fotky (`draft`, jako náhled)
FFPROBE_TIMEOUT = 120
# Změna pravidel zneplatní cache výsledků (2: u videa jen obrazová data).
VERSION = 2

_ZERO = bytes(BLOCK)
_LEVEL = {OK: 0, SUSPECT: 1, UNREADABLE: 2}


def _worse(a, b):
    return a if _LEVEL[a] >= _LEVEL[b] else b


def fmt_bytes(n):
    """Velikost úseku pro důvod: KiB, od 10 MiB v MiB s desetinnou čárkou."""
    if n >= 10 * 2**20:
        return f"{n / 2**20:.1f}".replace(".", ",") + " MiB"
    return f"{max(1, round(n / 1024))} KiB"


class _Zeros:
    """Souvislé úseky nul po blocích `BLOCK` zarovnaných od začátku
    souboru; neúplný poslední blok se počítá, je-li celý nulový."""

    def __init__(self, keep_all=False):
        self.offset = 0
        self.start = None      # začátek běžícího úseku
        self.runs = []         # [(od, délka)] úseků >= THRESHOLD
        self.all = [] if keep_all else None  # všechny úseky (video)
        self.longest = None    # (délka, od)

    def _close(self, end):
        if self.start is None:
            return
        length = end - self.start
        if self.longest is None or length > self.longest[0]:
            self.longest = (length, self.start)
        if length >= THRESHOLD:
            self.runs.append((self.start, length))
        if self.all is not None:
            self.all.append((self.start, length))
        self.start = None

    def feed(self, chunk):
        # Rychlá cesta: bez celého nulového bloku v datech se jen uzavře
        # běžící úsek (poslední neúplný blok souboru projde smyčkou).
        if len(chunk) % BLOCK == 0 and _ZERO not in chunk:
            self._close(self.offset)
            self.offset += len(chunk)
            return
        for i in range(0, len(chunk), BLOCK):
            block = chunk[i:i + BLOCK]
            if block == _ZERO[:len(block)]:
                if self.start is None:
                    self.start = self.offset + i
            else:
                self._close(self.offset + i)
        self.offset += len(chunk)

    def finish(self):
        self._close(self.offset)


def _at(start):
    return f"{start / 2**20:.1f}".replace(".", ",") + " MiB" \
        if start >= 2**20 else fmt_bytes(start)


def _video_zeros(zeros, ranges):
    """Úseky nul započítané jen v obrazových datech `ranges`: [(od,
    délka)] nad prahem a nejdelší (délka, od) nebo None. Úsek přes
    střídající se obraz a zvuk se počítá součtem částí v obrazu."""
    runs, longest = [], None
    for start, length in zeros.all:
        total, first = mp4.overlap(ranges, start, start + length)
        if not total:
            continue
        if longest is None or total > longest[0]:
            longest = (total, first)
        if total >= THRESHOLD:
            runs.append((first, total))
    return runs, longest


def _zero_reasons(zeros, size):
    reasons = []
    for start, length in zeros.runs:
        text = fmt_bytes(length) + " nul"
        if start == 0:
            reasons.append(f"{text} od začátku")
        elif start + length >= size:
            reasons.append(f"{text} na konci")
        else:
            reasons.append(f"{text} uprostřed (od {_at(start)})")
    return reasons


def decode_image(data):
    """(stav, důvod) dekódování fotky; None = v pořádku.

    `draft` zmenší JPEG už při dekódování (jako náhled); chybu useknutých
    dat zachytí stejně jako plné dekódování. Pillow má mít vypnuté
    `LOAD_TRUNCATED_IMAGES`, jinak useknutý obraz projde."""
    try:
        img = Image.open(io.BytesIO(data))
    except Image.DecompressionBombError:
        return None
    except Exception:  # UnidentifiedImageError a rozbité hlavičky
        return UNREADABLE, "soubor nejde otevřít jako obrázek"
    try:
        with img:
            img.draft("RGB", (PREVIEW, PREVIEW))
            img.load()
    except Image.DecompressionBombError:
        return None
    except Exception as err:
        if "truncated" in str(err):
            return SUSPECT, "obraz je neúplný (useknutý soubor)"
        return SUSPECT, f"chyba při dekódování obrazu: {err}"
    return None


def probe_video(path):
    """(stav, důvod) z `ffprobe`; None = v pořádku. Bez `ffprobe`
    vyhodí FileNotFoundError."""
    if not shutil.which("ffprobe"):
        raise FileNotFoundError("ffprobe")
    # `file:` = jméno souboru se nikdy nevyloží jako protokol (`a:b.mp4`).
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_type", "-of", "json",
         "file:" + str(path)],
        capture_output=True, timeout=FFPROBE_TIMEOUT)
    err = proc.stderr.decode("utf-8", "replace").strip().splitlines()
    first = err[0] if err else ""
    try:
        streams = json.loads(proc.stdout or b"{}").get("streams") or []
    except ValueError:
        streams = []
    if proc.returncode != 0 or not streams:
        return UNREADABLE, "video nejde přečíst" + (f" ({first})"
                                                    if first else "")
    if first:
        return SUSPECT, f"ffprobe hlásí chybu: {first}"
    return None


def iter_check(path, typ):
    """Kontrola souboru `path` typu `typ` (foto / video / raw).

    Generátor: po každých `STEP` bajtech vydá počet přečtených. Vrátí
    výsledek (viz modul) se `sha256`."""
    digest, done, reported = hashlib.sha256(), 0, 0
    zeros = _Zeros(keep_all=typ == "video")
    keep = [] if typ == "foto" else None
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            digest.update(chunk)
            zeros.feed(chunk)
            if keep is not None:
                keep.append(chunk)
            done += len(chunk)
            if done - reported >= STEP:
                reported = done
                yield done
    zeros.finish()
    stav, duvody, poznamka = OK, [], None
    longest, ranges = zeros.longest, None
    if typ == "video" and done and zeros.all:
        ranges = mp4.video_ranges(path)
    if done == 0:
        stav, duvody = UNREADABLE, ["prázdný soubor (0 B)"]
    elif zeros.longest and zeros.longest[0] == done:
        stav, duvody = UNREADABLE, ["soubor obsahuje jen nuly"]
    else:
        found = None
        if typ == "foto":
            found = decode_image(b"".join(keep or []))
        elif typ == "video":
            try:
                found = probe_video(path)
            except FileNotFoundError:
                poznamka = "video ověřeno jen testem nul (chybí ffprobe)"
            except subprocess.TimeoutExpired:
                poznamka = "ffprobe nedoběhl, video ověřeno jen testem nul"
        if found:
            stav, duvody = found[0], [found[1]]
        if ranges:
            runs, longest = _video_zeros(zeros, ranges)
            zero = [f"{fmt_bytes(n)} nul v obrazových datech "
                    f"(od {_at(start)})" for start, n in runs]
        else:
            zero = _zero_reasons(zeros, done)
        if zero:
            stav = _worse(stav, SUSPECT)
            duvody += zero
    result = {"stav": stav, "duvody": duvody,
              "nuly": {"delka": longest[0], "od": longest[1]}
              if longest else None,
              "sha256": digest.hexdigest()}
    if ranges:
        result["nuly_rozsah"] = "obraz"
        result["nuly_soubor"] = {"delka": zeros.longest[0],
                                 "od": zeros.longest[1]}
    if poznamka:
        result["poznamka"] = poznamka
    return result


def check(path, typ):
    gen = iter_check(path, typ)
    while True:
        try:
            next(gen)
        except StopIteration as stop:
            return stop.value


# --- cache ------------------------------------------------------------------

def _load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def _save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _hit(entry, st):
    return (entry and entry.get("verze") == VERSION
            and entry.get("size") == st.st_size
            and entry.get("mtime_ns") == st.st_mtime_ns)


# Cache akce zapisuje i server z více vláken (líné náhledy téže akce);
# znovunačtení před zápisem kryje zpoždění vlákna, zámek řeší i současné
# čtení-zápis téhož procesu.
_CACHE_LOCK = threading.Lock()


def cached(todo, cache_path):
    """{klíč: výsledek} z cache pro `todo` = [(klíč, cesta, stat, typ)];
    soubory bez platného záznamu chybí. Nic nečte."""
    cache = _load(cache_path)
    return {key: cache[key]["vysledek"] for key, _, st, _ in todo
            if _hit(cache.get(key), st)}


def event_cache_path(work, nazev):
    """Cache výsledků jedné akce (`zkontrolovat`, náhledy, souhrny)."""
    return Path(work) / "cache" / "kontrola" / f"{nazev}.json"


def ensure_event_file(path, cache_path, key=None):
    """Výsledek kontroly jednoho souboru, uložený do cache akce.

    Hit z cache nic nečte; při miss se soubor zkontroluje a výsledek
    se uloží (bez sha256). Nepodporovaný typ a chyba čtení vrátí None
    bez zápisu — kontrola nesmí zastavit generování náhledu.
    """
    from .importer import kind  # importer importuje tento modul
    key = key or Path(path).name
    if kind(key) == "nepodporovany":
        return None
    try:
        st = os.stat(path)
    except OSError:
        return None
    cache = _load(cache_path)
    if _hit(cache.get(key), st):
        return cache[key]["vysledek"]
    try:
        result = check(path, kind(key))
    except OSError:
        return None
    result.pop("sha256", None)
    # Před zápisem znovu načíst: náhledy jedné akce se počítají
    # souběžně a každý zapisuje jen svůj záznam (nejde přepsat cizí).
    with _CACHE_LOCK:
        cache = _load(cache_path)
        cache[key] = {"verze": VERSION, "size": st.st_size,
                      "mtime_ns": st.st_mtime_ns, "vysledek": result}
        _save(cache_path, cache)
    return result


def summary(cache_path, doc, present=None):
    """{název: {"stav", "duvody", "overeno"?, "vyradit"?}} poškozených.

    `doc` je `_metadata.json` akce (může být None); u souborů s ručním
    potvrzením nebo označením k vyřazení přídá příznak — počty je nechají
    vyniknout, dialog úklidu je ukáže šedě. `present` jsou názvy souborů
    v kořeni: bez něj se počítají i výsledky souborů, které už byly
    vytroupeny (zastaralá cache). Záznamy starší verze pravidel a klíče
    z podsložek (RAW.ignored) do souhrnu nepatří; kromě cache JSONu
    se nic nečte."""
    files = (doc or {}).get("soubory") or {}
    present = None if present is None else set(present)
    out = {}
    for key, entry in sorted(_load(cache_path).items()):
        if "/" in key or entry.get("verze") != VERSION:
            continue
        if present is not None and key not in present:
            continue
        result = entry.get("vysledek") or {}
        if result.get("stav") not in (SUSPECT, UNREADABLE):
            continue
        record = files.get(key) or {}
        item = {"stav": result["stav"], "duvody": result.get("duvody") or []}
        if record.get("overeno"):
            item["overeno"] = True
        if record.get("vyradit"):
            item["vyradit"] = True
        out[key] = item
    return out


def counted(summary_map):
    """Počet do odznaku: bez ručně potvrzených a označených k vyřazení."""
    return sum(1 for item in summary_map.values()
               if not (item.get("overeno") or item.get("vyradit")))


def iter_check_files(todo, cache_path, sha_cache=None):
    """Kontrola souborů `todo` = [(klíč, cesta, stat, typ)] s cache
    `cache_path` podle (klíč, velikost, mtime_ns).

    Generátor průběhu: `kontrola` (kolik souborů a bajtů), pak
    `kontrola_prubeh` (hotovo; po souboru, u velkých i po `STEP`); hity
    z cache jsou hned hotové. Vrátí {klíč: výsledek bez sha256}. Spočítané
    sha256 zapíše i do cache hashů `sha_cache` (tvar importu), aby je plán
    nečetl znovu. Cache se uloží i při přerušení."""
    cache = _load(cache_path)
    yield {"typ": "kontrola", "souboru": len(todo),
           "bajtu": sum(st.st_size for _, _, st, _ in todo)}
    results, fresh, files, done = {}, [], 0, 0
    for item in todo:
        key, _, st, _ = item
        if _hit(cache.get(key), st):
            results[key] = cache[key]["vysledek"]
            files, done = files + 1, done + st.st_size
        else:
            fresh.append(item)

    def progress(n=0):
        return {"typ": "kontrola_prubeh", "hotovo_souboru": files,
                "hotovo_bajtu": done + n}
    if files:
        yield progress()
    shas = {}
    try:
        for key, path, st, typ in fresh:
            gen = iter_check(path, typ)
            try:
                while True:
                    yield progress(next(gen))
            except StopIteration as stop:
                result = stop.value
            except FileNotFoundError:
                continue  # mezitím zmizel; plán ho ohlásí
            except OSError as err:
                # Chyba čtení (výpadek SMB, práva) není vlastnost souboru:
                # výsledek se ukáže, ale necachuje.
                results[key] = {"stav": UNREADABLE, "duvody": [
                    f"soubor nejde přečíst ({err.strerror or err})"],
                    "nuly": None, "chyba_cteni": True}
                files, done = files + 1, done + st.st_size
                yield progress()
                continue
            finally:
                gen.close()
            sha = result.pop("sha256")
            shas[key] = (st, sha)
            results[key] = result
            cache[key] = {"verze": VERSION, "size": st.st_size,
                          "mtime_ns": st.st_mtime_ns, "vysledek": result}
            files, done = files + 1, done + st.st_size
            yield progress()
    finally:
        if shas:
            _save(cache_path, cache)
            if sha_cache:
                hashes = _load(sha_cache)
                for key, (st, sha) in shas.items():
                    hashes[key] = {"size": st.st_size,
                                   "mtime_ns": st.st_mtime_ns,
                                   "sha256": sha}
                _save(sha_cache, hashes)
    return results


def check_files(todo, cache_path, sha_cache=None):
    gen = iter_check_files(todo, cache_path, sha_cache)
    while True:
        try:
            next(gen)
        except StopIteration as stop:
            return stop.value


# --- akce v archivu -----------------------------------------------------------

def event_files(event_dir):
    """Soubory akce ke kontrole jako `todo` pro `iter_check_files`: média
    a RAWy v kořeni a RAWy v `RAW.ignored/` (klíč = relativní cesta);
    ostatní podsložky a `Thumbs.db` se přeskočí."""
    from .archive import is_skipped
    from .cleanup import RAW_DIR
    from .importer import kind  # importer importuje tento modul
    todo = []
    for sub in ("", RAW_DIR):
        folder = Path(event_dir) / sub if sub else Path(event_dir)
        try:
            with os.scandir(folder) as it:
                found = sorted((e.name, e.path, e.stat()) for e in it
                               if e.is_file(follow_symlinks=False)
                               and not is_skipped(e.name))
        except (FileNotFoundError, NotADirectoryError):
            continue
        for name, path, st in found:
            typ = kind(name)
            if typ == "nepodporovany" or (sub and typ != "raw"):
                continue
            todo.append((f"{sub}/{name}" if sub else name, path, st, typ))
    return todo
