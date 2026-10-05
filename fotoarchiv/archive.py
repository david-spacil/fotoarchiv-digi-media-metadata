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


def is_skipped(name):
    """Soubory, které se nikde nepočítají ani nezpracovávají."""
    return name.lower() == "thumbs.db"


def is_metadata(name):
    """`_metadata.json`, sidecary `.xmp` a jejich dočasné soubory (ne
    média)."""
    return (name == METADATA_NAME or name.startswith(TMP_PREFIX)
            or name.startswith(XMP_TMP_PREFIX)
            or name.lower().endswith(".xmp"))


class Conflict(Exception):
    """`_metadata.json` se od načtení změnil."""

    def __init__(self, current_version):
        super().__init__("metadata changed since load")
        self.current_version = current_version


def version_of(data):
    return hashlib.sha256(data).hexdigest()


class Workspace:
    def __init__(self, archiv, work, zapis=False):
        self.archiv = Path(archiv).resolve()
        self.work = Path(work).resolve()
        self.zapis = zapis
        self.metadata_root = self.archiv if zapis else self.work / "metadata"
        self._save_lock = threading.Lock()

    # --- archiv -----------------------------------------------------------

    def event_names(self):
        names = []
        with os.scandir(self.archiv) as it:
            for entry in it:
                if EVENT_RE.match(entry.name) and entry.is_dir():
                    names.append(entry.name)
        return sorted(names, reverse=True)

    def event_dir(self, name):
        """Cesta ke složce akce; jiný než platný název akce vyhodí KeyError."""
        if "/" in name or "\\" in name or not EVENT_RE.match(name):
            raise KeyError(name)
        path = self.archiv / name
        if not path.is_dir():
            raise KeyError(name)
        return path

    def list_events(self):
        events = []
        for name in self.event_names():
            count = 0
            with os.scandir(self.archiv / name) as it:
                for entry in it:
                    if (entry.is_file() and not is_skipped(entry.name)
                            and not is_metadata(entry.name)):
                        count += 1
            doc, version = self.load(name)
            zmeneno = False
            if doc is None:
                stav = "nezpracovano"
            elif doc.get("dokonceno"):
                stav = "hotovo"
                exported = self.export_version(name)
                zmeneno = exported is not None and exported != version
            else:
                stav = "rozpracovano"
            events.append({
                "nazev": name,
                "datum": EVENT_RE.match(name).group(1),
                "souboru": count,
                "stav": stav,
                "zmeneno_po_exportu": zmeneno,
            })
        return events

    # --- metadata ---------------------------------------------------------

    def metadata_path(self, name):
        return self.metadata_root / name / METADATA_NAME

    def metadata_files(self):
        """Všechny `_metadata.json`, které aplikace vidí.

        Ve vývojovém režimu pracovní kopie i archiv, v produkčním jen archiv.
        """
        paths = []
        if not self.zapis:
            paths = list(self.metadata_root.glob(f"*/{METADATA_NAME}"))
        for name in self.event_names():
            path = self.archiv / name / METADATA_NAME
            if path.is_file():
                paths.append(path)
        return paths

    # --- export -----------------------------------------------------------

    def sidecar_path(self, name, soubor):
        """Sidecar vedle souboru, ve vývojovém režimu v `work/xmp/<akce>/`."""
        if self.zapis:
            return self.archiv / name / f"{soubor}.xmp"
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
