"""Archiv akcí a pracovní kopie `_metadata.json`.

`_metadata.json` se čte a ukládá v kořeni metadat: v produkčním režimu
(`zapis=True`) je to archiv, ve vývojovém pracovní adresář `work/metadata`,
který zrcadlí názvy složek akcí. Cestu skládá jediná funkce
`Workspace.metadata_path`.
"""

import hashlib
import json
import os
import re
import tempfile
import threading
from pathlib import Path

SCHEMA = "fotoarchiv-digi-media-metadata/1"
EVENT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (.+)$")
METADATA_NAME = "_metadata.json"
TMP_PREFIX = ".metadata-"
XMP_TMP_PREFIX = ".xmp-"
IMPORT_TMP_PREFIX = ".import-"
# Nezatříděné akce v kořeni archivu; mění je jen import (`unsorted`).
UNSORTED = "přetřídit"
# Přípona ignorované složky: Immich ji vylučuje (`**/*.ignored/**`).
# U složky akce znamená nedokončenou akci skrytou před Immichem.
IGNORED = ".ignored"


def is_skipped(name):
    """Soubory, které se nikde nepočítají ani nezpracovávají."""
    return name.lower() == "thumbs.db"


def is_metadata(name):
    """`_metadata.json`, sidecary `.xmp`, jejich dočasné soubory
    a rozpracované kopie importu (ne média)."""
    return (name == METADATA_NAME or name.startswith(TMP_PREFIX)
            or name.startswith(XMP_TMP_PREFIX)
            or name.startswith(IMPORT_TMP_PREFIX)
            or name.lower().endswith(".xmp"))


class Conflict(Exception):
    """`_metadata.json` se od načtení změnil."""

    def __init__(self, current_version):
        super().__init__("metadata changed since load")
        self.current_version = current_version


class Collision(KeyError):
    """Složka akce je v archivu s příponou `.ignored` i bez ní."""


def event_name(folder):
    """Název akce ze jména složky (bez přípony `.ignored`)."""
    folder = Path(folder).name
    return folder[:-len(IGNORED)] if folder.endswith(IGNORED) else folder


def version_of(data):
    return hashlib.sha256(data).hexdigest()


def samples(present, doc, count=4):
    """Až `count` názvů souborů rovnoměrně přes seřazené `present`.

    Soubory označené v `doc` k vyřazení se vynechají. Bere se prostředek
    každé `count`-tiny, takže velká akce nedá jen první soubory.
    """
    soubory = (doc or {}).get("soubory") or {}
    names = sorted(n for n in present
                   if not (soubory.get(n) or {}).get("vyradit"))
    if len(names) <= count:
        return names
    return [names[int((i + 0.5) * len(names) / count)]
            for i in range(count)]


class Workspace:
    def __init__(self, archiv, work, zapis=False):
        self.archiv = Path(archiv).resolve()
        self.work = Path(work).resolve()
        self.zapis = zapis
        self.metadata_root = self.archiv if zapis else self.work / "metadata"
        self._save_lock = threading.Lock()

    # --- archiv -----------------------------------------------------------

    def event_names(self):
        """Názvy akcí (bez přípony `.ignored`), každý jednou."""
        names = set()
        with os.scandir(self.archiv) as it:
            for entry in it:
                name = event_name(entry.name)
                if (EVENT_RE.match(name) and not name.endswith(IGNORED)
                        and entry.is_dir()):
                    names.add(name)
        return sorted(names, reverse=True)

    def event_dir(self, name):
        """Složka akce `name` na disku, s příponou `.ignored` i bez ní.

        Neplatný název (i s příponou) nebo chybějící složka vyhodí
        KeyError, obě složky zároveň Collision.
        """
        if ("/" in name or "\\" in name or not EVENT_RE.match(name)
                or name.endswith(IGNORED)):
            raise KeyError(name)
        plain = self.archiv / name
        hidden = self.archiv / (name + IGNORED)
        found = [p for p in (plain, hidden) if p.is_dir()]
        if len(found) == 2:
            raise Collision(name)
        if not found:
            raise KeyError(name)
        return found[0]

    def is_hidden(self, name):
        return self.event_dir(name).name.endswith(IGNORED)

    def _rename(self, name, src, dst):
        # os.rename na Linuxu přepíše prázdnou cílovou složku.
        if os.path.lexists(dst):
            raise Collision(name)
        os.rename(src, dst)
        return dst

    def publish(self, name):
        """Odebere složce akce příponu `.ignored` (zveřejní ji pro Immich).

        Ve vývojovém režimu a u složky bez přípony nic nedělá. Vrací
        složku akce; selhání přejmenování vyhodí OSError.
        """
        path = self.event_dir(name)
        if not self.zapis or not path.name.endswith(IGNORED):
            return path
        return self._rename(name, path, self.archiv / name)

    def hide(self, name):
        """Přidá složce akce příponu `.ignored`; jen pro příkaz `skryt`."""
        path = self.event_dir(name)
        if path.name.endswith(IGNORED):
            return path
        return self._rename(name, path, self.archiv / (name + IGNORED))

    def list_events(self):
        # model a consistency importují archive
        from .consistency import classify, counts
        from .integrity import counted, event_cache_path, summary
        from .model import completeness, incomplete
        events = []
        for name in self.event_names():
            try:
                path = self.event_dir(name)
            except Collision:
                events.append({
                    "nazev": name,
                    "datum": EVENT_RE.match(name).group(1),
                    "souboru": 0,
                    "stav": "kolize",
                    "zmeneno_po_exportu": False,
                    "chybi": [],
                    "kontrola": {},
                    "poskozene": 0,
                    "hotovost": None,
                    "ukazky": [],
                    "upravili": {},
                })
                continue
            present = set()
            files, dirs = [], []
            with os.scandir(path) as it:
                for entry in it:
                    if entry.is_dir():
                        dirs.append(entry.name)
                        continue
                    files.append(entry.name)
                    if (entry.is_file() and not is_skipped(entry.name)
                            and not is_metadata(entry.name)):
                        present.add(entry.name)
            doc, version = self.load(name)
            zmeneno = False
            chybi = []
            hotovost = None
            if doc is not None:
                hotovost = completeness(doc, present)
            if doc is None:
                stav = "nezpracovano"
            elif doc.get("dokonceno"):
                stav = "hotovo"
                exported = self.export_version(name)
                zmeneno = exported is not None and exported != version
                chybi = incomplete(doc, present, hotovost)
            else:
                stav = "rozpracovano"
            events.append({
                "nazev": name,
                "datum": EVENT_RE.match(name).group(1),
                "souboru": len(present),
                "stav": stav,
                "zmeneno_po_exportu": zmeneno,
                "chybi": chybi,
                "kontrola": counts(classify(files, dirs, doc)),
                # Počet poškozených z cache kontroly (issue #10); bez
                # vyřazených a ručně potvrzených, bez čtení souborů.
                "poskozene": counted(summary(
                    event_cache_path(self.work, name), doc, present)),
                "hotovost": hotovost,
                "ukazky": samples(present, doc),
                "upravili": (doc or {}).get("upravili") or {},
            })
        return events

    # --- metadata ---------------------------------------------------------

    def metadata_path(self, name):
        if self.zapis:
            return self.event_dir(name) / METADATA_NAME
        return self.metadata_root / name / METADATA_NAME

    def metadata_files(self):
        """Všechny `_metadata.json`, které aplikace vidí.

        Ve vývojovém režimu pracovní kopie i archiv, v produkčním jen archiv.
        """
        paths = []
        if not self.zapis:
            paths = list(self.metadata_root.glob(f"*/{METADATA_NAME}"))
        for name in self.event_names():
            try:
                path = self.event_dir(name) / METADATA_NAME
            except Collision:
                continue
            if path.is_file():
                paths.append(path)
        return paths

    # --- export -----------------------------------------------------------

    def sidecar_path(self, name, soubor):
        """Sidecar vedle souboru, ve vývojovém režimu v `work/xmp/<akce>/`."""
        if self.zapis:
            return self.event_dir(name) / f"{soubor}.xmp"
        return self.work / "xmp" / name / f"{soubor}.xmp"

    def export_record_path(self, name):
        return self.work / "export" / f"{name}.json"

    def export_version(self, name):
        """Verze `_metadata.json` posledního exportu bez chyb, nebo None.

        Záznam z druhého režimu se nepočítá (jiný `_metadata.json`
        i jiné sidecary).
        """
        try:
            record = json.loads(self.export_record_path(name).read_bytes())
        except (FileNotFoundError, ValueError):
            return None
        if record.get("zapis") != self.zapis:
            return None
        return record.get("version")

    def load(self, name):
        """Vrátí (dokument, verze), nebo (None, None), když soubor není."""
        path = self.metadata_path(name)
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return None, None
        return json.loads(data), version_of(data)

    def save(self, name, doc, version):
        """Atomicky uloží dokument; při neshodě verze vyhodí Conflict.

        `version` je verze, ze které klient vycházel (None = nový soubor).
        """
        path = self.metadata_path(name)
        data = (json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
        data = data.encode("utf-8")
        with self._save_lock:
            try:
                current = version_of(path.read_bytes())
            except FileNotFoundError:
                current = None
            if current != version:
                raise Conflict(current)
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(
                dir=path.parent, prefix=TMP_PREFIX, suffix=".tmp")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, path)
            except BaseException:
                Path(tmp).unlink(missing_ok=True)
                raise
        return version_of(data)


def adopt(archiv, work):
    """Převezme `_metadata.json` z pracovního adresáře do složek akcí.

    Zapisuje jen tam, kde v archivu soubor ještě není (`xb`). Vrátí
    (převzaté, přeskočené) jako seznamy (název akce, důvod).
    """
    ws = Workspace(archiv, work)
    adopted, skipped = [], []
    for src in sorted(ws.metadata_root.glob(f"*/{METADATA_NAME}")):
        name = src.parent.name
        try:
            dst = ws.event_dir(name) / METADATA_NAME
        except KeyError:
            skipped.append((name, "akce v archivu není"))
            continue
        data = src.read_bytes()
        try:
            with open(dst, "xb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        except FileExistsError:
            skipped.append((name, "metadata v archivu už jsou"))
            continue
        adopted.append((name, None))
    return adopted, skipped
