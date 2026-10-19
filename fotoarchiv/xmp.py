"""XMP sidecary z `_metadata.json` pro import do Immiche.

XML se skládá v Pythonu podle pevné šablony, ne exiftoolem: obsah závisí
jen na metadatech a názvu složky akce (bez časových razítek a verze
nástroje), takže změnu sidecaru pozná porovnání s obsahem na disku.
Mapování polí a konvence tagů viz docs/navrh/vystupy.md.
"""

import json
import os
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from PIL import Image

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
# Hlavička sidecaru s oblastmi obličejů (export pro obnovu).
HEAD_REGIONS = HEAD.replace(
    'xmlns:digiKam="http://www.digikam.org/ns/1.0/">',
    'xmlns:digiKam="http://www.digikam.org/ns/1.0/"\n'
    '    xmlns:mwg-rs="http://www.metadataworkinggroup.com/schemas/'
    'regions/"\n'
    '    xmlns:stDim="http://ns.adobe.com/xap/1.0/sType/Dimensions#"\n'
    '    xmlns:stArea="http://ns.adobe.com/xmp/sType/Area#">')
TAIL = """\
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
"""


def format_date(value):
    """`datum` pro `xmp:CreateDate`: čas bez zóny dostane Europe/Prague.

    Při podzimním posunu (hodina 2:00–3:00 dvakrát) platí `fold=0`, tedy
    letní čas. Samotné datum dostane poledne — Immich datum bez času
    nepřijme a poledne neposune den ani při převodu na UTC.
    """
    if "T" not in value:
        value = datetime.strptime(value, "%Y-%m-%d").date().isoformat() \
            + "T12:00:00"
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
    """Tagy v pořadí akce, autoři (jako v dokumentu).

    Osoby do tagů nejdou: Immich z nich osoby nevytvoří a své má
    z rozpoznávání obličejů.
    """
    result = [tag("akce", akce)]
    for name in values.get("autori") or []:
        if isinstance(name, str) and name.strip():
            result.append(tag("autor", name.strip()))
    return list(dict.fromkeys(result))


def stored_area(oblast, orientation):
    """Oblast vůči otočené fotce → vůči fotce v uloženém tvaru.

    Immich čte `mwg-rs:Regions` vůči uloženému obrázku a sám je otočí
    podle EXIF Orientation (ověřeno, viz docs/navrh/vystupy.md,
    Obnova obličejů).
    """
    x, y, w, h = oblast
    point = {
        1: (x, y), 2: (1 - x, y), 3: (1 - x, 1 - y), 4: (x, 1 - y),
        5: (y, x), 6: (y, 1 - x), 7: (1 - y, 1 - x), 8: (1 - y, x),
    }.get(orientation, (x, y))
    size = (h, w) if orientation in (5, 6, 7, 8) else (w, h)
    return [round(v, 4) for v in (*point, *size)]


def image_geometry(path):
    """(šířka, výška, EXIF Orientation) uloženého obrázku, jinak None."""
    try:
        with Image.open(path) as img:
            return img.width, img.height, img.getexif().get(0x0112, 1)
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


def regions(faces, geometry):
    """Řádky `mwg-rs:Regions` pro obličeje souboru."""
    width, height, orientation = geometry
    lines = ['   <mwg-rs:Regions rdf:parseType="Resource">',
             '    <mwg-rs:AppliedToDimensions rdf:parseType="Resource">',
             f"     <stDim:w>{width}</stDim:w>",
             f"     <stDim:h>{height}</stDim:h>",
             "     <stDim:unit>pixel</stDim:unit>",
             "    </mwg-rs:AppliedToDimensions>",
             "    <mwg-rs:RegionList>",
             "     <rdf:Bag>"]
    for face in faces:
        x, y, w, h = stored_area(face["oblast"], orientation)
        lines += ['      <rdf:li rdf:parseType="Resource">',
                  '       <mwg-rs:Area rdf:parseType="Resource">',
                  f"        <stArea:x>{x}</stArea:x>",
                  f"        <stArea:y>{y}</stArea:y>",
                  f"        <stArea:w>{w}</stArea:w>",
                  f"        <stArea:h>{h}</stArea:h>",
                  "        <stArea:unit>normalized</stArea:unit>",
                  "       </mwg-rs:Area>",
                  "       <mwg-rs:Type>Face</mwg-rs:Type>",
                  f"       <mwg-rs:Name>{escape(face['jmeno'])}</mwg-rs:Name>",
                  "      </rdf:li>"]
    lines += ["     </rdf:Bag>", "    </mwg-rs:RegionList>",
              "   </mwg-rs:Regions>"]
    return lines


def sidecar(doc, akce, soubor, geometry=None):
    """Text XMP sidecaru souboru `soubor` z akce ve složce `akce`.

    S `geometry` (viz image_geometry) navíc oblasti pojmenovaných
    obličejů pro obnovu Immiche; bez obličejů je sidecar běžný.
    """
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
    faces = doc.get("soubory", {}).get(soubor, {}).get("obliceje")
    if geometry and faces:
        lines += regions(faces, geometry)
        return HEAD_REGIONS + "\n".join(lines) + "\n" + TAIL
    return HEAD + "\n".join(lines) + "\n" + TAIL


def write_atomic(path, data, mode=None):
    """Zápis přes dočasný soubor (začíná tečkou) ve stejné složce.

    `mkstemp` zakládá soubor s právy 0600; `mode` je nastaví před
    přejmenováním (na SMB bez unixových rozšíření chmod nic neudělá).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=XMP_TMP_PREFIX,
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
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


def export(ws, akce, nanecisto=False, obliceje=False):
    """Exportuje sidecary akce; zapisuje jen chybějící a změněné.

    Vrací None, když akce nemá `_metadata.json`, jinak počty
    `zapsano`, `nezmeneno` a seznam `chyby` ({soubor, chyba}).
    Nanečisto nic nezapíše a `zapsano` je počet chybějících nebo
    neaktuálních. Po exportu bez chyb zapíše záznam o exportu, kromě
    exportu pro obnovu (`obliceje`), jehož sidecary běžné nejsou.
    """
    doc, version = ws.load(akce)
    if doc is None:
        return None
    written, unchanged, errors = 0, 0, []
    for disk_name, name in targets(ws, akce, doc):
        try:
            geometry = None
            if obliceje and doc["soubory"][name].get("obliceje"):
                geometry = image_geometry(ws.event_dir(akce) / disk_name)
            data = sidecar(doc, akce, name, geometry).encode("utf-8")
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
    if not nanecisto and not errors and not obliceje:
        record = {"version": version, "zapis": ws.zapis}
        write_atomic(ws.export_record_path(akce),
                     json.dumps(record).encode("utf-8"))
    return {"zapsano": written, "nezmeneno": unchanged, "chyby": errors}
