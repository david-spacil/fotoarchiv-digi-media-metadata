"""Náhled z EXIF hlavičky JPEG (IFD1) bez čtení celého souboru."""

THUMB_OFFSET = 0x0201
THUMB_LENGTH = 0x0202
ORIENTATION = 0x0112


def nahled(data):
    """(JPEG náhled, orientace 1–8) ze začátku JPEG souboru `data`.
    Náhled je None, když v hlavičce není nebo je useknutý."""
    if data[:2] != b"\xff\xd8":
        return None, 1
    i = 2
    while i + 4 <= len(data) and data[i] == 0xFF:
        marker = data[i + 1]
        if marker in (0xD9, 0xDA):  # konec obrázku, začátek dat
            break
        delka = int.from_bytes(data[i + 2:i + 4], "big")
        if marker == 0xE1 and data[i + 4:i + 10] == b"Exif\0\0":
            return _z_tiff(data[i + 10:i + 2 + delka])
        i += 2 + delka
    return None, 1


def _z_tiff(tiff):
    if tiff[:2] == b"II":
        order = "little"
    elif tiff[:2] == b"MM":
        order = "big"
    else:
        return None, 1

    def num(pos, n):
        if pos < 0 or pos + n > len(tiff):
            raise ValueError
        return int.from_bytes(tiff[pos:pos + n], order)

    def ifd(pos):
        """{tag: hodnota} pro SHORT/LONG a offset dalšího IFD."""
        tags = {}
        for k in range(num(pos, 2)):
            e = pos + 2 + 12 * k
            tag, typ = num(e, 2), num(e + 2, 2)
            if typ == 3:
                tags[tag] = num(e + 8, 2)
            elif typ == 4:
                tags[tag] = num(e + 8, 4)
        return tags, num(pos + 2 + 12 * num(pos, 2), 4)

    try:
        ifd0, dalsi = ifd(num(4, 4))
        orientace = ifd0.get(ORIENTATION, 1)
        if not 1 <= orientace <= 8:
            orientace = 1
        if not dalsi:
            return None, orientace
        ifd1, _ = ifd(dalsi)
    except ValueError:
        return None, 1
    off, n = ifd1.get(THUMB_OFFSET), ifd1.get(THUMB_LENGTH)
    if not off or not n or off + n > len(tiff):
        return None, orientace
    jpeg = tiff[off:off + n]
    if jpeg[:2] != b"\xff\xd8":
        return None, orientace
    return jpeg, orientace
