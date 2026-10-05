"""Náhledy s lokální cache mimo archiv.

Klíč cache = hash (cesta, velikost, mtime); dokud se soubor nezmění,
originál se znovu nečte. Fotky přes Pillow s `draft` (zmenšení už při
dekódování JPEG), videa snímkem z `ffmpeg`. Když náhled nejde vytvořit,
vrací se None a klient ukáže zástupnou ikonu.
"""

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

from .scan import is_video

SIZE = 320


def cache_key(path, st):
    raw = f"{Path(path).resolve()}|{st.st_size}|{st.st_mtime}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def make_image_thumb(src, dst):
    with Image.open(src) as img:
        img.draft("RGB", (SIZE * 2, SIZE * 2))
        img = ImageOps.exif_transpose(img)
        img.thumbnail((SIZE, SIZE))
        img.convert("RGB").save(dst, "JPEG", quality=80)


def make_video_thumb(src, dst):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg není k dispozici")
    # Snímek z 1. sekundy; krátké video bez ní zkusí začátek.
    for seek in ("1", "0"):
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", seek, "-i", str(src),
             "-frames:v", "1", "-vf",
             f"scale={SIZE}:{SIZE}:force_original_aspect_ratio=decrease",
             "-f", "image2",
             "-c:v", "mjpeg", str(dst)],
            capture_output=True)
        if proc.returncode == 0 and os.path.getsize(dst) > 0:
            return
    raise RuntimeError(proc.stderr.decode("utf-8", "replace"))


def thumbnail(src, cache_dir, make_image=make_image_thumb,
              make_video=make_video_thumb):
    """Cesta k náhledu v cache (vytvoří ho při prvním požadavku)."""
    st = os.stat(src)
    thumbs = Path(cache_dir) / "thumbs"
    dst = thumbs / f"{cache_key(src, st)}.jpg"
    if dst.exists():
        return dst
    failed = dst.with_suffix(".failed")
    if failed.exists():
        return None
    thumbs.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=thumbs, suffix=".tmp")
    os.close(fd)
    try:
        (make_video if is_video(src.name) else make_image)(src, tmp)
        os.replace(tmp, dst)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        failed.touch()
        return None
    return dst
