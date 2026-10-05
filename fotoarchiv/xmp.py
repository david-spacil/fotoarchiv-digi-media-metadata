"""XMP sidecary z `_metadata.json` pro import do Immiche.

XML se skládá v Pythonu podle pevné šablony, ne exiftoolem: obsah závisí
jen na metadatech a názvu složky akce (bez časových razítek a verze
nástroje), takže změnu sidecaru pozná porovnání s obsahem na disku.
Mapování polí a konvence tagů viz README, Výstupy.
"""

import json
import os
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from .archive import XMP_TMP_PREFIX
from .model import resolve

ZONE = ZoneInfo("Europe/Prague")

HEAD = """\
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    xmlns:exif="http://ns.adobe.com/exif/1.0/"
    xmlns:digiKam="http://www.digikam.org/ns/1.0/">
"""
TAIL = """\
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
"""


def format_date(value):
    """`datum` pro `xmp:CreateDate`: čas bez zóny dostane Europe/Prague.

    Při podzimním posunu (hodina 2:00–3:00 dvakrát) platí `fold=0`, tedy
    letní čas. Samotné datum zůstane bez času a zóny.
    """
    if "T" not in value:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZONE)
    return dt.isoformat()


def format_coord(value, positive, negative):
    """Souřadnice ve formátu XMP `DDD,MM.mmmmmmK` (6 míst minut)."""
    # Celočíselně v milióntinách minuty, ať zaokrouhlení nedá 60 minut.
    micro = round(abs(value) * 60 * 1_000_000)
    degrees, micro = divmod(micro, 60 * 1_000_000)
    minutes, fraction = divmod(micro, 1_000_000)
    ref = negative if value < 0 else positive
    return f"{degrees},{minutes:02d}.{fraction:06d}{ref}"


def tag(root, name):
    return f"{root}/{name.replace('/', '-')}"


def tags(akce, values):
    """Tagy v pořadí akce, autoři, osoby; uvnitř skupiny jako v dokumentu."""
    result = [tag("akce", akce)]
    for key, root in (("autori", "autor"), ("osoby", "osoba")):
        for name in values.get(key) or []:
            if isinstance(name, str) and name.strip():
                result.append(tag(root, name.strip()))
    return list(dict.fromkeys(result))


def sidecar(doc, akce, soubor):
    """Text XMP sidecaru souboru `soubor` z akce ve složce `akce`."""
    values = {k: v["hodnota"] for k, v in resolve(doc, soubor).items()}
    lines = []
    popis = values.get("popis")
    if isinstance(popis, str) and popis.strip():
        lines += ["   <dc:description>",
                  "    <rdf:Alt>",
                  '     <rdf:li xml:lang="x-default">'
                  f"{escape(popis)}</rdf:li>",
                  "    </rdf:Alt>",
                  "   </dc:description>"]
    if values.get("datum"):
        lines.append(f"   <xmp:CreateDate>{format_date(values['datum'])}"
                     "</xmp:CreateDate>")
    gps = values.get("gps")
    if gps:
        lat, lon = gps
        lines.append("   <exif:GPSLatitude>"
                     f"{format_coord(lat, 'N', 'S')}</exif:GPSLatitude>")
        lines.append("   <exif:GPSLongitude>"
                     f"{format_coord(lon, 'E', 'W')}</exif:GPSLongitude>")
    lines += ["   <digiKam:TagsList>", "    <rdf:Bag>"]
    lines += [f"     <rdf:li>{escape(t)}</rdf:li>" for t in tags(akce, values)]
    lines += ["    </rdf:Bag>", "   </digiKam:TagsList>"]
    return HEAD + "\n".join(lines) + "\n" + TAIL


def write_atomic(path, data):
    """Zápis přes dočasný soubor (začíná tečkou) ve stejné složce."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=XMP_TMP_PREFIX,
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def targets(ws, akce, doc):
    """Soubory k exportu: se záznamem, v kořeni, neoznačené k vyřazení.

    Vrací [(název na disku, název záznamu)]; názvy na SMB mohou přijít
    v NFD i NFC, porovnává se po NFC.
    """
    on_disk = {}
    with os.scandir(ws.event_dir(akce)) as it:
        for entry in it:
            if entry.is_file():
                on_disk[unicodedata.normalize("NFC", entry.name)] = entry.name
    result = []
    for name, record in sorted(doc.get("soubory", {}).items()):
        disk_name = on_disk.get(unicodedata.normalize("NFC", name))
        if disk_name and not record.get("vyradit"):
            result.append((disk_name, name))
    return result


def export(ws, akce, nanecisto=False):
    """Exportuje sidecary akce; zapisuje jen chybějící a změněné.

    Vrací None, když akce nemá `_metadata.json`, jinak počty
    `zapsano`, `nezmeneno` a seznam `chyby` ({soubor, chyba}).
    Nanečisto nic nezapíše a `zapsano` je počet chybějících nebo
    neaktuálních. Po exportu bez chyb zapíše záznam o exportu.
    """
    doc, version = ws.load(akce)
    if doc is None:
        return None
    written, unchanged, errors = 0, 0, []
    for disk_name, name in targets(ws, akce, doc):
        try:
            data = sidecar(doc, akce, name).encode("utf-8")
            path = ws.sidecar_path(akce, disk_name)
            try:
                current = path.read_bytes()
            except FileNotFoundError:
                current = None
            if current == data:
                unchanged += 1
                continue
            if not nanecisto:
                write_atomic(path, data)
            written += 1
        except (OSError, ValueError, TypeError) as e:
            errors.append({"soubor": name, "chyba": str(e)})
    if not nanecisto and not errors:
        record = {"version": version, "zapis": ws.zapis}
        write_atomic(ws.export_record_path(akce),
                     json.dumps(record).encode("utf-8"))
    return {"zapsano": written, "nezmeneno": unchanged, "chyby": errors}
