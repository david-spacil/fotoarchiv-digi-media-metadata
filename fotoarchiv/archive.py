"""Archiv akcí a pracovní kopie `_metadata.json`.

Archiv se jen čte. `_metadata.json` se čte a ukládá v pracovním adresáři,
který zrcadlí názvy složek akcí; cestu skládá jediná funkce
`Workspace.metadata_path`, aby pozdější přepnutí na zápis do archivu
byla jen změna kořene.
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


def is_skipped(name):
    """Soubory, které se nikde nepočítají ani nezpracovávají."""
    return name.lower() == "thumbs.db"


class Conflict(Exception):
    """`_metadata.json` se od načtení změnil."""

    def __init__(self, current_version):
        super().__init__("metadata changed since load")
        self.current_version = current_version


def version_of(data):
    return hashlib.sha256(data).hexdigest()


class Workspace:
    def __init__(self, archiv, work):
        self.archiv = Path(archiv).resolve()
        self.work = Path(work).resolve()
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
                    if entry.is_file() and not is_skipped(entry.name):
                        count += 1
            doc, _ = self.load(name)
            if doc is None:
                stav = "nezpracovano"
            elif doc.get("dokonceno"):
                stav = "hotovo"
            else:
                stav = "rozpracovano"
            events.append({
                "nazev": name,
                "datum": EVENT_RE.match(name).group(1),
                "souboru": count,
                "stav": stav,
            })
        return events

    # --- metadata ---------------------------------------------------------

    def metadata_path(self, name):
        return self.work / "metadata" / name / METADATA_NAME

    def metadata_files(self):
        """Všechny `_metadata.json`, které aplikace vidí (práce i archiv)."""
        paths = list(self.work.glob(f"metadata/*/{METADATA_NAME}"))
        for name in self.event_names():
            path = self.archiv / name / METADATA_NAME
            if path.is_file():
                paths.append(path)
        return paths

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
                dir=path.parent, prefix=".metadata-", suffix=".tmp")
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
