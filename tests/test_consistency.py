import unicodedata

from fotoarchiv import consistency
from .conftest import snapshot


def found(root, doc=None):
    return [(f["druh"], f["nazev"]) for f in consistency.check(root, doc)]


def test_unsupported_files(tree):
    root = tree({"P1503712.JPG": "", "prezentace.zip": "", "zprava.pdf": "",
                 "Thumbs.db": "", "obrazek.tif": ""})
    assert found(root) == [("nepodporovany", "obrazek.tif"),
                           ("nepodporovany", "prezentace.zip"),
                           ("nepodporovany", "zprava.pdf")]


def test_orphan_sidecar(tree):
    root = tree({"P1503712.JPG": "", "P1503712.JPG.xmp": "",
                 "P1503713.JPG.xmp": ""})
    assert found(root) == [("sirotek_xmp", "P1503713.JPG.xmp")]


def test_sidecar_case_insensitive(tree):
    root = tree({"a.jpg": "", "a.JPG.xmp": "", "b.RW2": "", "b.RW2.xmp": ""})
    assert found(root) == [("raw", "b.RW2")]


def test_missing_record(tree):
    root = tree({"P1503712.JPG": ""})
    doc = {"soubory": {"P1503712.JPG": {}, "P1503714.JPG": {}}}
    assert found(root, doc) == [("chybejici", "P1503714.JPG")]


def test_missing_record_nfd_on_disk(tree):
    nfd = unicodedata.normalize("NFD", "Záběr.jpg")
    nfc = unicodedata.normalize("NFC", "Záběr.jpg")
    root = tree({nfd: ""})
    assert found(root, {"soubory": {nfc: {}}}) == []


def test_subfolders(tree):
    root = tree({"Video/": {"v.mp4": ""}, "RAW.ignored/": {"a.RW2": ""},
                 "ostatni.ignored/": {"x.zip": ""}})
    assert found(root) == [("podslozka", "Video")]


def test_event_without_metadata(tree):
    root = tree({"P1503712.RW2": ""})
    assert found(root, None) == [("raw", "P1503712.RW2")]


def test_metadata_and_temp_files_not_reported(tree):
    root = tree({"_metadata.json": "{}", ".metadata-abc.tmp": "",
                 ".xmp-abc.tmp": "", ".import-x.jpg": "", "a.jpg": ""})
    assert found(root, {"soubory": {"a.jpg": {}}}) == []


def test_order_and_counts(tree):
    root = tree({"Video/": {}, "b.zip": "", "a.RW2": "", "x.xmp": ""})
    doc = {"soubory": {"z.jpg": {}}}
    result = consistency.check(root, doc)
    assert [f["druh"] for f in result] == [
        "nepodporovany", "sirotek_xmp", "raw", "podslozka", "chybejici"]
    assert consistency.counts(result) == {
        "nepodporovany": 1, "sirotek_xmp": 1, "raw": 1, "podslozka": 1,
        "chybejici": 1}


def test_check_changes_nothing(tree):
    root = tree({"Video/": {"v.mp4": ""}, "b.zip": "", "x.xmp": ""})
    before = snapshot(root)
    consistency.check(root, {"soubory": {"z.jpg": {}}})
    assert snapshot(root) == before
