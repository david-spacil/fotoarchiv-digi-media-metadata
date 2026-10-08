"""Rozsahy obrazových dat ve videu MP4/MOV (ISO BMFF, QuickTime).

Kontrola poškozených souborů (`integrity`) hledá u videa úseky nul jen
v datech obrazové stopy: nuly mimo ně jsou běžná součást formátu
(výplňové atomy `free`, pevně velké `udta` a `meta`, ticho
v nekomprimovaném zvuku PCM). Snímky H.264/HEVC obsahují zabraňovací
bajty, souvislý blok nul v nich platně nevznikne.

Čte jen hlavičky (atomy na nejvyšší úrovni a `moov`), ne data. Když
tabulky vzorků nejdou přečíst nebo neodpovídají souboru, vrátí None
a kontrola projde celý soubor přísně.
"""

import bisect
import os
import struct

CONTAINERS = {b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts"}
MAX_MOOV = 256 * 2**20     # větší hlavička = nesmysl, kontrola přísně
MAX_ATOMS = 100_000


class Invalid(Exception):
    """Struktura souboru neodpovídá MP4/MOV."""


def _atoms(f, start, end):
    """(typ, začátek dat, konec) atomů v [start, end) souboru `f`."""
    pos, n = start, 0
    while pos + 8 <= end:
        f.seek(pos)
        head = f.read(16)
        if len(head) < 8:
            raise Invalid("useknutá hlavička atomu")
        size, typ = struct.unpack(">I4s", head[:8])
        data = pos + 8
        if size == 1:
            if len(head) < 16:
                raise Invalid("useknutá velikost atomu")
            size = struct.unpack(">Q", head[8:16])[0]
            data = pos + 16
        elif size == 0:
            size = end - pos
        if size < data - pos or pos + size > end:
            raise Invalid("velikost atomu mimo soubor")
        yield typ, data, pos + size
        pos += size
        n += 1
        if n > MAX_ATOMS:
            raise Invalid("příliš mnoho atomů")


def _children(buf, start=0, end=None):
    """(typ, začátek dat, konec) atomů v bufferu hlavičky."""
    end = len(buf) if end is None else end
    pos = start
    while pos + 8 <= end:
        size, typ = struct.unpack_from(">I4s", buf, pos)
        data = pos + 8
        if size == 1:
            if pos + 16 > end:
                raise Invalid("useknutá velikost atomu")
            size = struct.unpack_from(">Q", buf, pos + 8)[0]
            data = pos + 16
        elif size == 0:
            size = end - pos
        if size < data - pos or pos + size > end:
            raise Invalid("velikost atomu mimo hlavičku")
        yield typ, data, pos + size
        pos += size


def _find(buf, start, end, path):
    """Data prvního atomu na cestě `path` (např. [b"mdia", b"hdlr"])."""
    for typ, data, stop in _children(buf, start, end):
        if typ == path[0]:
            return (data, stop) if len(path) == 1 else \
                _find(buf, data, stop, path[1:])
    return None


def _handler(buf, mdia):
    hdlr = _find(buf, *mdia, [b"hdlr"])
    if hdlr is None or hdlr[1] - hdlr[0] < 12:
        raise Invalid("stopa bez hdlr")
    return buf[hdlr[0] + 8:hdlr[0] + 12]


def _table(buf, box, fmt, width):
    """Položky tabulky FullBox (verze+příznaky, počet, položky)."""
    data, stop = box
    if stop - data < 8:
        raise Invalid("useknutá tabulka")
    (count,) = struct.unpack_from(">I", buf, data + 4)
    if data + 8 + count * width > stop:
        raise Invalid("tabulka delší než atom")
    return [struct.unpack_from(fmt, buf, data + 8 + i * width)
            for i in range(count)]


def _track_ranges(buf, stbl):
    """[(začátek, konec)] dat vzorků stopy podle `stco`/`co64`, `stsc`
    a `stsz`."""
    stco = _find(buf, *stbl, [b"stco"])
    if stco is not None:
        offsets = [o for (o,) in _table(buf, stco, ">I", 4)]
    else:
        co64 = _find(buf, *stbl, [b"co64"])
        if co64 is None:
            raise Invalid("stopa bez stco/co64")
        offsets = [o for (o,) in _table(buf, co64, ">Q", 8)]
    stsc = _find(buf, *stbl, [b"stsc"])
    stsz = _find(buf, *stbl, [b"stsz"])
    if stsc is None or stsz is None:
        raise Invalid("stopa bez stsc/stsz")
    runs = _table(buf, stsc, ">III", 12)
    data, stop = stsz
    if stop - data < 12:
        raise Invalid("useknutá stsz")
    fixed, count = struct.unpack_from(">II", buf, data + 4)
    if fixed:
        sizes = None
    else:
        if data + 12 + 4 * count > stop:
            raise Invalid("stsz delší než atom")
        sizes = struct.unpack_from(f">{count}I", buf, data + 12)
    firsts = [r[0] for r in runs]
    ranges, sample = [], 0
    for i, offset in enumerate(offsets):
        chunk = i + 1
        k = bisect.bisect_right(firsts, chunk) - 1
        if k < 0:
            raise Invalid("stsc nepokrývá chunk")
        per_chunk = runs[k][1]
        if sizes is None:
            length = per_chunk * fixed
        else:
            if sample + per_chunk > count:
                raise Invalid("stsz kratší než stsc")
            length = sum(sizes[sample:sample + per_chunk])
        sample += per_chunk
        if length:
            ranges.append((offset, offset + length))
    return ranges


def merge(ranges):
    """Seřazené rozsahy bez překryvů (sousední spojené)."""
    result = []
    for start, end in sorted(ranges):
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else:
            result.append((start, end))
    return result


def video_ranges(path):
    """Seřazené [(začátek, konec)] obrazových dat všech obrazových stop,
    nebo None (není MP4/MOV, fragmentované, poškozená hlavička, rozsahy
    mimo `mdat`)."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            top = list(_atoms(f, 0, size))
            if any(t == b"moof" for t, _, _ in top):
                return None  # fragmentované: vzorky popisují moof, ne moov
            moov = [(d, e) for t, d, e in top if t == b"moov"]
            mdats = merge((d, e) for t, d, e in top if t == b"mdat")
            if len(moov) != 1 or not mdats or \
                    moov[0][1] - moov[0][0] > MAX_MOOV:
                return None
            f.seek(moov[0][0])
            buf = f.read(moov[0][1] - moov[0][0])
        ranges = []
        for typ, data, stop in _children(buf):
            if typ != b"trak":
                continue
            mdia = _find(buf, data, stop, [b"mdia"])
            if mdia is None or _handler(buf, mdia) != b"vide":
                continue
            stbl = _find(buf, *mdia, [b"minf", b"stbl"])
            if stbl is None:
                raise Invalid("obrazová stopa bez stbl")
            ranges += _track_ranges(buf, stbl)
    except (Invalid, struct.error, OSError, ValueError):
        return None
    ranges = merge(ranges)
    if not ranges:
        return None
    # Rozsahy musí ležet v mdat; jinak tabulky neodpovídají souboru
    # (např. vynulované nebo cizí) a kontrola má jít přísně.
    starts = [m[0] for m in mdats]
    for start, end in ranges:
        k = bisect.bisect_right(starts, start) - 1
        if k < 0 or end > mdats[k][1]:
            return None
    return ranges


def overlap(ranges, start, end):
    """(délka průniku [start, end) s `ranges`, začátek prvního průniku)."""
    total, first = 0, None
    k = max(0, bisect.bisect_right(ranges, (start, float("inf"))) - 1)
    while k < len(ranges) and ranges[k][0] < end:
        a, b = max(ranges[k][0], start), min(ranges[k][1], end)
        if a < b:
            total += b - a
            first = a if first is None else first
        k += 1
    return total, first
