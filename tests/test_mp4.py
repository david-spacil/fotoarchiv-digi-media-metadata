"""Rozsahy obrazových dat v MP4/MOV (`fotoarchiv.mp4`).

Parser se ověřuje dvěma cestami: ručně sestavené atomy (co64, pevná
stsz, víc řádků stsc, poškozené tabulky) a srovnání s pozicemi paketů
podle `ffprobe` na videích z ffmpeg.
"""

import json
import shutil
import struct
import subprocess

import pytest

from fotoarchiv import mp4


def atom(typ, *parts):
    body = b"".join(parts)
    return struct.pack(">I4s", 8 + len(body), typ) + body


def full(typ, body):
    return atom(typ, b"\0\0\0\0", body)


def hdlr(kind):
    return full(b"hdlr", b"\0" * 4 + kind + b"\0" * 12)


def trak(kind, offsets, sizes=None, fixed=0, count=0, stsc=None, co64=False):
    stsc = stsc or [(1, 1, 1)]
    table = full(b"co64", struct.pack(">I", len(offsets)) + b"".join(
        struct.pack(">Q", o) for o in offsets)) if co64 else \
        full(b"stco", struct.pack(">I", len(offsets)) + b"".join(
            struct.pack(">I", o) for o in offsets))
    if sizes is not None:
        stsz = full(b"stsz", struct.pack(">II", 0, len(sizes)) + b"".join(
            struct.pack(">I", s) for s in sizes))
    else:
        stsz = full(b"stsz", struct.pack(">II", fixed, count))
    stsc_box = full(b"stsc", struct.pack(">I", len(stsc)) + b"".join(
        struct.pack(">III", *r) for r in stsc))
    stbl = atom(b"stbl", stsc_box, stsz, table)
    return atom(b"trak", atom(b"mdia", hdlr(kind),
                              atom(b"minf", stbl)))


def mp4_file(tmp_path, traks, mdat_size=10_000, name="a.mp4", extra=b""):
    """ftyp + mdat (data od bajtu 16+8) + moov."""
    ftyp = atom(b"ftyp", b"isom\0\0\0\0")
    mdat = atom(b"mdat", b"\x01" * mdat_size)
    path = tmp_path / name
    path.write_bytes(ftyp + mdat + atom(b"moov", *traks) + extra)
    return path, len(ftyp) + 8


def test_simple_tracks(tmp_path):
    _, base = mp4_file(tmp_path, [])
    path, _ = mp4_file(tmp_path, [
        trak(b"vide", [base, base + 3000], sizes=[1000, 500, 700],
             stsc=[(1, 2, 1), (2, 1, 1)]),
        trak(b"soun", [base + 1500], fixed=4, count=200)])
    # Chunk 1: dva vzorky (1500 B), chunk 2: jeden (700 B); zvuk se nepočítá.
    assert mp4.video_ranges(path) == [(base, base + 1500),
                                      (base + 3000, base + 3700)]


def test_co64_and_fixed_size(tmp_path):
    _, base = mp4_file(tmp_path, [])
    path, _ = mp4_file(tmp_path, [
        trak(b"vide", [base, base + 4000], fixed=100, count=20,
             stsc=[(1, 10, 1)], co64=True)])
    assert mp4.video_ranges(path) == [(base, base + 1000),
                                      (base + 4000, base + 5000)]


def test_two_video_tracks_merged(tmp_path):
    _, base = mp4_file(tmp_path, [])
    path, _ = mp4_file(tmp_path, [
        trak(b"vide", [base], sizes=[1000]),
        trak(b"vide", [base + 1000], sizes=[500])])
    assert mp4.video_ranges(path) == [(base, base + 1500)]


@pytest.mark.parametrize("case", ["mimo_mdat", "bez_videa", "useknuta",
                                  "frag", "jpeg", "stsz_kratka"])
def test_invalid_returns_none(tmp_path, case):
    _, base = mp4_file(tmp_path, [])
    if case == "mimo_mdat":  # vynulované nebo cizí tabulky
        path, _ = mp4_file(tmp_path, [trak(b"vide", [0], sizes=[100])])
    elif case == "bez_videa":
        path, _ = mp4_file(tmp_path, [trak(b"soun", [base], sizes=[100])])
    elif case == "useknuta":
        path, _ = mp4_file(tmp_path, [trak(b"vide", [base], sizes=[100])])
        path.write_bytes(path.read_bytes()[:-20])
    elif case == "frag":
        path, _ = mp4_file(tmp_path, [trak(b"vide", [base], sizes=[100])],
                           extra=atom(b"moof", b"\0" * 8))
    elif case == "stsz_kratka":
        path, _ = mp4_file(tmp_path, [
            trak(b"vide", [base, base + 100], sizes=[100])])
    else:
        path = tmp_path / "a.mp4"
        path.write_bytes(b"\xff\xd8\xff\xe0" + b"\0" * 5000)
    assert mp4.video_ranges(path) is None


def test_overlap():
    ranges = [(0, 100), (200, 300), (400, 500)]
    assert mp4.overlap(ranges, 50, 450) == (50 + 100 + 50, 50)
    assert mp4.overlap(ranges, 100, 200) == (0, None)
    assert mp4.overlap(ranges, 250, 260) == (10, 250)
    assert mp4.overlap([], 0, 10) == (0, None)


def test_merge():
    assert mp4.merge([(5, 8), (0, 3), (3, 4), (7, 10)]) == [(0, 4), (5, 10)]


# --- srovnání s ffprobe -----------------------------------------------------

ENCODES = {
    "moov_konec.mov": ["-c:v", "mpeg4", "-c:a", "pcm_s16be"],
    "faststart.mov": ["-c:v", "mpeg4", "-c:a", "pcm_s16be",
                      "-movflags", "+faststart"],
    "aac.mp4": ["-c:v", "mpeg4", "-c:a", "aac"],
}


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                    reason="bez ffmpeg/ffprobe")
@pytest.mark.parametrize("name", sorted(ENCODES))
def test_matches_ffprobe(tmp_path, name):
    path = tmp_path / name
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
         "testsrc2=size=320x240:rate=25:duration=2", "-f", "lavfi", "-i",
         "sine=f=440:r=48000", "-t", "2", *ENCODES[name], str(path)],
        check=True, capture_output=True)
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
         "packet=pos,size", "-of", "json", str(path)],
        check=True, capture_output=True).stdout
    packets = json.loads(out)["packets"]
    expected = mp4.merge((int(p["pos"]), int(p["pos"]) + int(p["size"]))
                         for p in packets)
    assert mp4.video_ranges(path) == expected


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="bez ffmpeg")
def test_fragmented_returns_none(tmp_path):
    path = tmp_path / "frag.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
         "testsrc2=size=320x240:rate=25:duration=2", "-c:v", "mpeg4",
         "-movflags", "+frag_keyframe+empty_moov", str(path)],
        check=True, capture_output=True)
    assert mp4.video_ranges(path) is None
