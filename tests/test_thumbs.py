from PIL import Image

from fotoarchiv import thumbs


def test_thumbnail_cached(tmp_path):
    src = tmp_path / "a.jpg"
    Image.new("RGB", (1200, 800), "red").save(src)
    cache = tmp_path / "cache"
    calls = []

    def make(s, d, size):
        calls.append(s)
        thumbs.make_image_thumb(s, d, size)

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

    def fail(s, d, size):
        calls.append(s)
        raise RuntimeError("x")

    assert thumbs.thumbnail(src, tmp_path / "c", make_video=fail) is None
    assert thumbs.thumbnail(src, tmp_path / "c", make_video=fail) is None
    assert len(calls) == 1


def test_sizes_cached_separately(tmp_path):
    src = tmp_path / "a.jpg"
    Image.new("RGB", (4000, 3000), "red").save(src)
    cache = tmp_path / "cache"
    calls = []

    def make(s, d, size):
        calls.append(size)
        thumbs.make_image_thumb(s, d, size)

    small = thumbs.thumbnail(src, cache, make_image=make)
    large = thumbs.thumbnail(src, cache, thumbs.LARGE, make_image=make)
    again = thumbs.thumbnail(src, cache, thumbs.LARGE, make_image=make)
    assert small != large == again
    assert calls == [thumbs.SIZE, thumbs.LARGE]
    with Image.open(large) as img:
        assert max(img.size) == thumbs.LARGE


def test_large_exif_orientation(tmp_path):
    src = tmp_path / "r.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6
    Image.new("RGB", (3000, 2000)).save(src, exif=exif)
    with Image.open(thumbs.thumbnail(src, tmp_path / "c",
                                     thumbs.LARGE)) as img:
        assert img.size == (1067, 1600)
