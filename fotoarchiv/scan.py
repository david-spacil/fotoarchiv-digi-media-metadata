"""Sken kořene akce: technická metadata přes `exiftool` a návrh skupin."""

import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path

from .archive import is_skipped

MEDIA_EXT = {"jpg", "jpeg", "png", "mp4", "mov"}
VIDEO_EXT = {"mp4", "mov"}
TAGS = ["DateTimeOriginal", "CreateDate", "Make", "Model",
        "GPSLatitude", "GPSLongitude"]

WHATSAPP_RE = re.compile(r"^IMG-(\d{4})(\d{2})(\d{2})-WA\d+", re.I)
# (id, název skupiny bez přístroje, vzor názvu souboru)
PATTERNS = [
    ("panasonic", "Soubory P… bez přístroje",
     re.compile(r"^P\d{7}\.", re.I)),
    ("samsung", "Soubory RRRRMMDD_HHMMSS bez přístroje",
     re.compile(r"^\d{8}_\d{6}")),
    ("whatsapp", "WhatsApp", WHATSAPP_RE),
    ("img", "Soubory IMG_… bez přístroje", re.compile(r"^IMG_\d{4}", re.I)),
]
OTHER = ("ostatni", "Ostatní")
EXIF_DATE_RE = re.compile(r"^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})")


def extension(name):
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def is_video(name):
    return extension(name) in VIDEO_EXT


def root_files(event_dir):
    """(média, nezpracované) v kořeni akce; média jako (název, stat)."""
    media, other = [], []
    with os.scandir(event_dir) as it:
        for entry in it:
            if not entry.is_file() or is_skipped(entry.name):
                continue
            if extension(entry.name) in MEDIA_EXT:
                media.append((entry.name, entry.stat()))
            else:
                other.append(entry.name)
    return sorted(media), sorted(other)


# --- parsování výstupu exiftool ------------------------------------------

def parse_date(value):
    if not isinstance(value, str):
        return None
    m = EXIF_DATE_RE.match(value)
    if not m or m.group(1) == "0000":
        return None
    y, mo, d, h, mi, s = m.groups()
    return f"{y}-{mo}-{d}T{h}:{mi}:{s}"


def device(make, model):
    make = (make or "").strip()
    model = (model or "").strip()
    if not model:
        return make or None
    if not make or model.lower().startswith(make.lower()):
        return model
    return f"{make} {model}"


def parse_record(name, tags):
    """Technické údaje souboru z jednoho záznamu `exiftool -json -n`."""
    datum = parse_date(tags.get("DateTimeOriginal")) or \
        parse_date(tags.get("CreateDate"))
    if datum is None:
        m = WHATSAPP_RE.match(name)
        if m:
            datum = "-".join(m.groups())
    lat, lon = tags.get("GPSLatitude"), tags.get("GPSLongitude")
    gps = [lat, lon] if isinstance(lat, (int, float)) and \
        isinstance(lon, (int, float)) else None
    return {
        "nazev": name,
        "datum": datum,
        "pristroj": device(tags.get("Make"), tags.get("Model")),
        "gps": gps,
    }


def run_exiftool(event_dir, names):
    """Jedno volání exiftool nad seznamem souborů; vrací {název: tagy}."""
    if not names:
        return {}
    cmd = ["exiftool", "-json", "-n", "-api", "QuickTimeUTC",
           "-charset", "filename=utf8", "-@", "-"]
    cmd += [f"-{t}" for t in TAGS]
    args = "\n".join(names) + "\n"
    proc = subprocess.run(cmd, cwd=event_dir, input=args.encode("utf-8"),
                          capture_output=True)
    if not proc.stdout.strip():
        return {}
    return {r["SourceFile"]: r for r in json.loads(proc.stdout)}


# --- sken s cache ---------------------------------------------------------

def scan(event_dir, cache_dir, exiftool=run_exiftool):
    """Technické údaje všech médií v kořeni akce.

    Výsledek se cachuje podle (název, velikost, mtime); exiftool dostane jen
    soubory, které v cache nejsou nebo se změnily.
    """
    event_dir = Path(event_dir)
    cache_path = Path(cache_dir) / "scan" / f"{event_dir.name}.json"
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        cache = {}
    media, other = root_files(event_dir)
    todo = []
    for name, st in media:
        hit = cache.get(name)
        if not hit or hit["size"] != st.st_size or \
                hit["mtime"] != st.st_mtime:
            todo.append(name)
    if todo:
        tags = exiftool(event_dir, todo)
        for name, st in media:
            if name in todo:
                cache[name] = {
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "data": parse_record(name, tags.get(name, {})),
                }
        cache = {name: cache[name] for name, _ in media}
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache, ensure_ascii=False),
                       encoding="utf-8")
        os.replace(tmp, cache_path)
    files = []
    for name, st in media:
        record = dict(cache[name]["data"])
        record["velikost"] = st.st_size
        record["video"] = is_video(name)
        files.append(record)
    return files, other


# --- návrh skupin --------------------------------------------------------

def name_pattern(name):
    for pid, label, regex in PATTERNS:
        if regex.match(name):
            return pid, label
    return OTHER


def slug(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text or "skupina"


def propose_groups(files):
    """Skupiny podle (přístroj, vzor názvu).

    Soubor bez přístroje patří ke skupině se stejným vzorem, pokud ji tvoří
    jediný přístroj (např. mp4 ze Samsungu bez Make/Model), jinak do skupiny
    podle vzoru. Vrací {"skupiny": {id: {...}}, "prirazeni": {soubor: id}}.
    """
    keyed = [(f["nazev"], f.get("pristroj"), name_pattern(f["nazev"]))
             for f in files]
    devices_by_pattern = {}
    for _, dev, pat in keyed:
        if dev:
            devices_by_pattern.setdefault(pat[0], set()).add(dev)
    keys = {}
    for name, dev, pat in keyed:
        if not dev and pat != OTHER and \
                len(devices_by_pattern.get(pat[0], ())) == 1:
            dev = next(iter(devices_by_pattern[pat[0]]))
        keys[name] = (dev, pat)

    groups, ids, assignment = {}, {}, {}
    for name, key in keys.items():
        if key not in ids:
            dev, (pid, label) = key
            base = slug(dev.split(" ", 1)[-1]) if dev else pid
            gid, n = base, 2
            while gid in groups:
                gid, n = f"{base}-{n}", n + 1
            ids[key] = gid
            groups[gid] = {"nazev": dev or label}
            if dev:
                groups[gid]["pristroj"] = dev
        assignment[name] = ids[key]
    return {"skupiny": groups, "prirazeni": assignment}
