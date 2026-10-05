import os

from fotoarchiv import scan


def test_parse_panasonic():
    rec = scan.parse_record("P1503712.JPG", {
        "DateTimeOriginal": "2026:04:28 09:44:36",
        "CreateDate": "2026:04:28 09:44:36",
        "Make": "Panasonic", "Model": "DC-G9"})
    assert rec == {"nazev": "P1503712.JPG", "datum": "2026-04-28T09:44:36",
                   "pristroj": "Panasonic DC-G9", "gps": None}


def test_parse_samsung_gps_and_video_offset():
    rec = scan.parse_record("20260428_150641.jpg", {
        "DateTimeOriginal": "2026:04:28 15:06:41",
        "Make": "samsung", "Model": "SM-A528B",
        "GPSLatitude": 49.407, "GPSLongitude": 16.777})
    assert rec["pristroj"] == "samsung SM-A528B"
    assert rec["gps"] == [49.407, 16.777]
    video = scan.parse_record("20260428_144812.mp4", {
        "CreateDate": "2026:04:28 14:49:02+02:00"})
    assert video["datum"] == "2026-04-28T14:49:02"
    assert video["pristroj"] is None


def test_parse_whatsapp_date_from_name():
    rec = scan.parse_record("IMG-20260428-WA0003.jpg", {})
    assert rec["datum"] == "2026-04-28"
    zero = scan.parse_record("IMG-20260428-WA0004.jpg",
                             {"CreateDate": "0000:00:00 00:00:00"})
    assert zero["datum"] == "2026-04-28"


def test_device_model_contains_make():
    assert scan.device("Canon", "Canon EOS 5D") == "Canon EOS 5D"
    assert scan.device(None, None) is None


def test_root_files_filtering(tree):
    root = tree({"a.JPG": "", "b.mp4": "", "c.MOV": "", "d.png": "",
                 "prezentace.zip": "", "e.RW2": "", "Thumbs.db": "",
                 "Video/": {}})
    media, other = scan.root_files(root)
    assert [n for n, _ in media] == ["a.JPG", "b.mp4", "c.MOV", "d.png"]
    assert other == ["e.RW2", "prezentace.zip"]


def test_scan_cache(tree, tmp_path_factory):
    root = tree({"a.jpg": "1", "b.jpg": "2"})
    cache = tmp_path_factory.mktemp("cache")
    calls = []

    def fake(event_dir, names):
        calls.append(list(names))
        return {n: {"Make": "X", "Model": "Y"} for n in names}

    files, _ = scan.scan(root, cache, exiftool=fake)
    assert [f["pristroj"] for f in files] == ["X Y", "X Y"]
    scan.scan(root, cache, exiftool=fake)
    assert calls == [["a.jpg", "b.jpg"]]
    (root / "b.jpg").write_text("changed")
    os.utime(root / "b.jpg", (1, 1))
    (root / "c.jpg").write_text("3")
    scan.scan(root, cache, exiftool=fake)
    assert calls[1] == ["b.jpg", "c.jpg"]


def f(name, dev):
    return {"nazev": name, "pristroj": dev}


def test_groups_two_devices():
    g = scan.propose_groups([
        f("P1503712.JPG", "Panasonic DC-G9"),
        f("P1503713.JPG", "Panasonic DC-G9"),
        f("20260428_150641.jpg", "samsung SM-A528B")])
    assert len(g["skupiny"]) == 2
    assert g["prirazeni"]["P1503712.JPG"] == "dc-g9"
    assert g["prirazeni"]["20260428_150641.jpg"] == "sm-a528b"
    assert g["skupiny"]["dc-g9"] == {"nazev": "Panasonic DC-G9",
                                     "pristroj": "Panasonic DC-G9"}


def test_groups_without_device_by_pattern():
    g = scan.propose_groups([
        f("IMG-20260428-WA0003.jpg", None),
        f("IMG-20260428-WA0004.jpg", None),
        f("P1503712.JPG", "Panasonic DC-G9")])
    assert g["prirazeni"]["IMG-20260428-WA0003.jpg"] == "whatsapp"
    assert g["prirazeni"]["IMG-20260428-WA0004.jpg"] == "whatsapp"
    assert g["skupiny"]["whatsapp"] == {"nazev": "WhatsApp"}


def test_groups_video_without_device_joins_single_device():
    g = scan.propose_groups([
        f("20260428_150641.jpg", "samsung SM-A528B"),
        f("20260428_144812.mp4", None),
        f("prezentace.png", None)])
    assert g["prirazeni"]["20260428_144812.mp4"] == "sm-a528b"
    assert g["prirazeni"]["prezentace.png"] == "ostatni"
