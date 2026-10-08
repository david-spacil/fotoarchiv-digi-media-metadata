"""Vzorky poškozených souborů pro testy kontroly (`fotoarchiv.integrity`).

Vznikají za běhu testu z pevného seedu, v repozitáři nejsou binární
soubory. Fotka je šum (jako snímek z fotoaparátu), vady odpovídají
vzorkům z issue #10: vynulované bloky souborového systému na začátku,
na konci a uprostřed, useknutý soubor. Video potřebuje `ffmpeg`.

Ručně: python tests/fixtures/integrity/make_samples.py CÍLOVÁ_SLOŽKA
"""

import io
import random
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

BLOCK = 4096
WIDTH, HEIGHT = 1280, 960


def noise_jpeg(seed=10, size=(WIDTH, HEIGHT)):
    data = random.Random(seed).randbytes(size[0] * size[1] * 3)
    out = io.BytesIO()
    Image.frombytes("RGB", size, data).save(out, "JPEG", quality=90)
    return out.getvalue()


def zeroed(data, start, length):
    z = bytearray(data)
    z[start:start + length] = bytes(min(length, len(data) - start))
    return bytes(z)


def aligned(n):
    return n // BLOCK * BLOCK


def with_zero_run(data, run, at):
    """Vloží zarovnaný úsek nul délky `run` (data se nezvětší)."""
    return zeroed(data, aligned(at), run)


def samples():
    """{název: bajty} obrazových vzorků."""
    ok = noise_jpeg()
    n = len(ok)
    return {
        "ok.jpg": ok,
        "nuly_zacatek.jpg": zeroed(ok, 0, 192 * BLOCK),
        "nuly_konec.jpg": zeroed(ok, aligned(n * 88 // 100), n),
        "nuly_uprostred.jpg": with_zero_run(ok, 16 * BLOCK, n // 2),
        # Zdravý soubor s krátkým úsekem nul (jako metadata z Photoshopu).
        "nuly_pod_prahem.jpg": with_zero_run(ok, 6 * BLOCK, n // 2),
        "useknuty.jpg": ok[:n * 7 // 10],
        "useknuty_ffd9.jpg": ok[:n // 2] + b"\xff\xd9",
        "prazdny.jpg": b"",
        "jen_nuly.jpg": bytes(n),
        "nuly.nef": zeroed(random.Random(3).randbytes(300_000), 0,
                           32 * BLOCK),
        "ok.nef": random.Random(4).randbytes(300_000),
    }


def make_video(path):
    """Krátké MP4 (1 s); False bez `ffmpeg`."""
    if not shutil.which("ffmpeg"):
        return False
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
         "testsrc=size=160x120:rate=10:duration=1", "-c:v", "mpeg4",
         "-pix_fmt", "yuv420p", str(path)],
        check=True, capture_output=True)
    return True


def make_silent_pcm_video(path):
    """MOV jako z Panasonicu: obraz + nekomprimovaný zvuk PCM s tichem
    po 1 s (184 KiB nul v kuse); False bez `ffmpeg`. Snímky jen
    vnitrosnímkové a velké, aby šly vynulovat uvnitř obrazu."""
    if not shutil.which("ffmpeg"):
        return False
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
         "testsrc2=size=1280x720:rate=10:duration=2", "-f", "lavfi", "-i",
         "anullsrc=r=48000:cl=stereo", "-t", "2",
         "-af", "asetnsamples=n=48000:p=0", "-c:v", "mpeg4", "-q:v", "1",
         "-g", "1", "-c:a", "pcm_s16be", str(path)],
        check=True, capture_output=True)
    return True


def without_moov(data):
    """MP4 bez atomu `moov` (přerušené nahrávání): useknutý před ním."""
    i = data.find(b"moov")
    j = data.find(b"mdat")
    # moov za mdat (výchozí ffmpeg): useknout těsně před moov.
    return data[:i - 4] if i > j else data[:j + 4] + bytes(1000)


def write(target):
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    for name, data in samples().items():
        (target / name).write_bytes(data)
    if make_video(target / "ok.mp4"):
        (target / "bez_moov.mp4").write_bytes(
            without_moov((target / "ok.mp4").read_bytes()))
    if make_silent_pcm_video(target / "ticho_pcm.mov"):
        # Nuly uvnitř obrazových dat (rozsahy z `fotoarchiv.mp4`, tady
        # pevně: první snímek začíná za `ftyp`/`wide`/`mdat`, je > 79 KiB).
        data = (target / "ticho_pcm.mov").read_bytes()
        start = aligned(data.find(b"mdat") + 4) + 2 * BLOCK
        (target / "nuly_v_obraze.mov").write_bytes(
            zeroed(data, start, 16 * BLOCK))
    return target


if __name__ == "__main__":
    write(sys.argv[1] if len(sys.argv) > 1 else "vzorky")
