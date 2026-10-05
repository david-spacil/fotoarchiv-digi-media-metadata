from PIL import Image

from fotoarchiv import thumbs


def test_thumbnail_cached(tmp_path):
    src = tmp_path / "a.jpg"
    Image.new("RGB", (1200, 800), "red").save(src)
    cache = tmp_path / "cache"
    calls = []

    def make(s, d):
        calls.append(s)
        thumbs.make_image_thumb(s, d)

    first = thumbs.thumbnail(src, cache, make_image=make)
    second = thumbs.thumbnail(src, cache, make_image=make)
    assert first == second and len(calls) == 1
    with Image.open(first) as img:
        assert max(img.size) == thumbs.SIZE


def test_thumbnail_exif_orientation(tmp_path):
    src = tmp_path / "r.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6            # otočeno o 90°
    Image.new("RGB", (600, 400)).save(src, exif=exif)
    with Image.open(thumbs.thumbnail(src, tmp_path / "c")) as img:
        assert img.size[1] > img.size[0]


def test_video_failure_gives_none_once(tmp_path):
    src = tmp_path / "v.mp4"
    src.write_bytes(b"not a video")
    calls = []

    def fail(s, d):
        calls.append(s)
        raise RuntimeError("x")

    assert thumbs.thumbnail(src, tmp_path / "c", make_video=fail) is None
    assert thumbs.thumbnail(src, tmp_path / "c", make_video=fail) is None
    assert len(calls) == 1
