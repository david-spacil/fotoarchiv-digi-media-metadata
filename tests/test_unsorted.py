import pytest

from fotoarchiv import unsorted
from .conftest import make_tree


def test_folders_skip_ignored_and_files(tmp_path):
    root = tmp_path / "přetřídit"
    make_tree(tmp_path, {"přetřídit/": {
        "DOD 2017/": {"a.jpg": "a"}, "_duplicity.ignored/": {"b.jpg": "b"},
        "poznamky.txt": "x"}})
    assert unsorted.folders(root) == ["DOD 2017"]
    assert unsorted.folders(tmp_path / "neni") == []
    events = list(unsorted.iter_overview(tmp_path / "neni", tmp_path))
    assert events == [{"typ": "vypis", "slozky": []}]


def test_listing_counts_subfolders(tmp_path):
    root = tmp_path / "přetřídit"
    make_tree(tmp_path, {"přetřídit/": {"Stuchlík 70/": {
        "a.jpg": "a", "b.JPG": "b", "c.mp4": "c", "pozn.docx": "d",
        "Thumbs.db": "t",
        "NEF/": {"a.nef": "1", "b.NEF": "2", "Thumbs.db": "t"},
        "JPEG orig.ignored/": {"a.jpg": "a"}}}})
    item = unsorted.listing(root, "Stuchlík 70")
    assert item["pocty"] == {"foto": 2, "video": 1, "raw": 2,
                             "nepodporovany": 1}
    assert item["podslozky"] == ["NEF"]
    assert item["velikost"] == 6


@pytest.mark.parametrize("name, datum, rok", [
    ("komise_Vzorovice_31.8.2012", "2012-08-31", 2012),
    ("2018_10_22_Tisková konference", "2018-10-22", 2018),
    ("2019_4_8_Zlaty fond", "2019-04-08", 2019),
    ("Opavske_expozitury_Prislo_12_09_2019", "2019-09-12", 2019),
    ("AMČR 8.11.2017", "2017-11-08", 2017),
    ("DOD 2017", None, 2017),
    ("VZORNY", None, None),
    ("x 31.2.2012", None, 2012),
])
def test_name_date(name, datum, rok):
    assert unsorted.name_date(name) == (datum, rok)


def exif_dates(dates):
    calls = []

    def exiftool(folder, names):
        calls.append(sorted(names))
        return {n: {"DateTimeOriginal": dates[n]} for n in names
                if n in dates}
    return exiftool, calls


def test_details_exif_first_and_cached(tmp_path):
    root = tmp_path / "přetřídit"
    make_tree(tmp_path, {"přetřídit/": {
        "Vzorov 2017/": {"a.jpg": "a", "Den 2/": {"b.jpg": "b"}},
        "komise_Vzorovice_31.8.2012/": {"c.jpg": "c"},
        "DOD 2017/": {"d.jpg": "d"}}})
    exiftool, calls = exif_dates({"a.jpg": "2017:06:15 10:00:00",
                                  "b.jpg": "2017:06:14 09:00:00"})
    cache = tmp_path / "cache"
    d = unsorted.details(root, "Vzorov 2017", cache, exiftool)
    assert (d["od"], d["do"]) == ("2017-06-14", "2017-06-15")
    assert d["navrh"] == {"datum": "2017-06-14", "nazev": "Vzorov 2017",
                          "akce": "2017-06-14 Vzorov 2017"}
    d = unsorted.details(root, "komise_Vzorovice_31.8.2012", cache, exiftool)
    assert d["navrh"]["akce"] == \
        "2012-08-31 komise_Vzorovice_31.8.2012"
    d = unsorted.details(root, "DOD 2017", cache, exiftool)
    assert d["navrh"] == {"datum": None, "nazev": "DOD 2017", "akce": None}

    # Druhé otevření beze změny: exiftool se nespustí.
    calls.clear()
    events = list(unsorted.iter_overview(root, cache, exiftool))
    assert calls == []
    assert [e["typ"] for e in events] == ["vypis"] + ["slozka"] * 3
    assert [e["nazev"] for e in events[0]["slozky"]] == [
        "DOD 2017", "Vzorov 2017", "komise_Vzorovice_31.8.2012"]
    assert events[2]["navrh"]["datum"] == "2017-06-14"
    assert events[0]["slozky"][0]["z_nazvu"] == {"datum": None, "rok": 2017}
    assert list(unsorted.iter_overview(root, cache, exiftool, exif=False)) \
        == events[:1]
