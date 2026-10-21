"""Stažení originálů: streamovaný ZIP akce nebo výběru s metadaty.

ZIP se zapisuje do proudu bez převíjení (velikosti v datových
deskriptorech, zip64 nad 4 GiB) bez komprese — média jsou už
komprimovaná. Na disku nevzniká nic, obsah jde po blocích rovnou
do odpovědi. Návrh viz docs/navrh/ a změna `stahovani-originalu`.
"""

import io
import json
import os
import time
import unicodedata
import zipfile
from urllib.parse import quote

from . import scan, xmp
from .archive import METADATA_NAME, upgrade

CHUNK = 1024 * 1024


class _Sink(io.RawIOBase):
    """Proud pro `zipfile`, který jen hromadí zapsané bajty."""

    def __init__(self):
        self.chunks = []

    def writable(self):
        return True

    def write(self, data):
        self.chunks.append(bytes(data))
        return len(data)

    def take(self):
        """Nahromaděné bajty jako jeden blok, nebo nic."""
        data = b"".join(self.chunks)
        self.chunks.clear()
        return [data] if data else []


def _info(name, seconds):
    # ZIP neumí data před rokem 1980; práva rw-r--r-- pro rozbalení.
    info = zipfile.ZipInfo(name, max(time.localtime(seconds)[:6],
                                     (1980, 1, 1, 0, 0, 0)))
    info.external_attr = 0o644 << 16
    return info


def stream(entries):
    """Bajty ZIPu po blocích z `entries` = [(název v ZIPu, zdroj)].

    Zdroj je cesta k souboru (čte se po blocích; zmizelý soubor se
    přeskočí), nebo bajty vygenerované v paměti. Prázdné bloky se
    neposílají (v chunked odpovědi by znamenaly konec).
    """
    sink = _Sink()
    with zipfile.ZipFile(sink, "w", zipfile.ZIP_STORED) as zf:
        for name, source in entries:
            if isinstance(source, bytes):
                info = _info(name, time.time())
                info.file_size = len(source)
                with zf.open(info, "w") as out:
                    out.write(source)
                yield from sink.take()
                continue
            try:
                f = open(source, "rb")
            except FileNotFoundError:
                continue
            with f:
                st = os.fstat(f.fileno())
                info = _info(name, st.st_mtime)
                # Velikost předem rozhodne o zip64 hlavičce záznamu.
                info.file_size = st.st_size
                with zf.open(info, "w") as out:
                    while block := f.read(CHUNK):
                        out.write(block)
                        yield from sink.take()
            yield from sink.take()
    yield from sink.take()


def load_metadata(ws, akce):
    """(bajty, dokument) uloženého `_metadata.json`, nebo (None, None)."""
    try:
        data = ws.metadata_path(akce).read_bytes()
    except FileNotFoundError:
        return None, None
    doc = json.loads(data)
    upgrade(doc)
    return data, doc


def _records(doc):
    """Záznamy souborů podle názvu po NFC (názvy na SMB i v NFD)."""
    return {unicodedata.normalize("NFC", name): (name, record)
            for name, record in (doc or {}).get("soubory", {}).items()}


def event_media(event_dir, doc):
    """Média kořene akce kromě označených k vyřazení (názvy z disku)."""
    records = _records(doc)
    media, _ = scan.root_files(event_dir)
    result = []
    for name, _ in media:
        found = records.get(unicodedata.normalize("NFC", name))
        if not (found and found[1].get("vyradit")):
            result.append(name)
    return result


def entries(event_dir, akce, files, data, doc):
    """Položky ZIPu: média `files` (názvy z disku) se sidecary
    z aktuálního dokumentu (bez obličejů) a `_metadata.json`."""
    records = _records(doc)
    for name in files:
        yield name, event_dir / name
        found = records.get(unicodedata.normalize("NFC", name))
        if found:
            text = xmp.sidecar(doc, akce, found[0])
            yield f"{name}.xmp", text.encode("utf-8")
    if data is not None:
        yield METADATA_NAME, data


def plural(n, one, few, many):
    return one if n == 1 else few if 2 <= n <= 4 else many


def selection_name(akce, count):
    files = plural(count, "soubor", "soubory", "souborů")
    return f"{akce} ({count} {files}).zip"


def attachment(name):
    """Hodnota `Content-Disposition` s UTF-8 názvem a ASCII zálohou."""
    try:
        name.encode("ascii")
    except UnicodeEncodeError:
        simple = unicodedata.normalize("NFKD", name).encode(
            "ascii", "ignore").decode("ascii")
        simple = simple.replace("\\", "").replace('"', "")
        quoted = quote(name, safe="!#$&+^`|~")
        return f"attachment; filename=\"{simple}\"; filename*=UTF-8''{quoted}"
    return 'attachment; filename="{}"'.format(
        name.replace("\\", "").replace('"', ""))
