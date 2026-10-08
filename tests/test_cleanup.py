import os

import pytest

from fotoarchiv import cleanup
from .conftest import snapshot


def ops(plan, blocked=None):
    return [(o["typ"], o["z"], o["do"]) for o in plan["operace"]
            if blocked is None or o["blocked"] == blocked]


def test_subfolders_listed_ignored_skipped(tree):
    root = tree({"RAW/": {"a.RW2": "", "b.rw2": "", "Thumbs.db": ""},
                 "Video/": {"v.mp4": ""},
                 "Staré.ignored/": {"x.jpg": ""},
                 "a.jpg": ""})
    folders = {f["nazev"]: f for f in cleanup.subfolders(root)}
    assert set(folders) == {"RAW", "Video"}
    assert folders["RAW"]["souboru"] == 2 and folders["RAW"]["rawu"] == 2
    assert folders["RAW"]["navrh"] == "ponechat"
    assert folders["Video"]["navrh"] is None


def test_mostly_raw_becomes_raw_ignored(tree):
    root = tree({"RAWy/": {f"P{i}.RW2": "" for i in range(176)}})
    plan = cleanup.plan(root, {"RAWy": "ponechat"})
    assert ops(plan) == [("rename", "RAWy", "RAW.ignored")]


def test_other_folder_kept(tree):
    root = tree({"Prezentační/": {"a.pptx": ""}})
    plan = cleanup.plan(root, {"Prezentační": "ponechat"})
    assert ops(plan) == [("rename", "Prezentační", "Prezentační.ignored")]


def test_undecided_folder_has_no_ops(tree):
    root = tree({"Video/": {"v.mp4": ""}})
    plan = cleanup.plan(root)
    assert ops(plan) == []
    assert plan["podslozky"][0]["volba"] is None


def test_move_to_root_and_delete(tree):
    root = tree({"Video/": {"v.mp4": "", "Thumbs.db": ""}})
    plan = cleanup.plan(root, {"Video": "presunout"})
    assert ops(plan) == [("move", "Video/v.mp4", "v.mp4"),
                         ("delete", "Video", None)]
    assert not any(o["blocked"] for o in plan["operace"])


def test_collision_blocks(tree):
    root = tree({"Video/": {"a.mp4": "", "b.mp4": ""}, "A.MP4": ""})
    plan = cleanup.plan(root, {"Video": "presunout"})
    assert ops(plan, blocked=True) == [("move", "Video/a.mp4", "a.mp4"),
                                       ("delete", "Video", None)]
    assert ops(plan, blocked=False) == [("move", "Video/b.mp4", "b.mp4")]


def test_raw_in_root(tree):
    root = tree({"P1503712.RW2": "", "P1503712.JPG": ""})
    plan = cleanup.plan(root)
    assert ops(plan) == [("move", "P1503712.RW2", "RAW.ignored/P1503712.RW2")]
    assert plan["raw_v_koreni"] == 1
    assert ops(cleanup.plan(root, raw_from_root=False)) == []


def test_existing_raw_ignored_is_merged(tree):
    root = tree({"RAW.ignored/": {"a.rw2": ""},
                 "raw/": {"a.rw2": "", "b.rw2": ""},
                 "c.rw2": ""})
    plan = cleanup.plan(root, {"raw": "ponechat"})
    assert ops(plan, blocked=False) == [
        ("move", "raw/b.rw2", "RAW.ignored/b.rw2"),
        ("move", "c.rw2", "RAW.ignored/c.rw2")]
    assert ops(plan, blocked=True) == [
        ("move", "raw/a.rw2", "RAW.ignored/a.rw2"),
        ("delete", "raw", None)]


def test_root_raw_into_renamed_folder(tree):
    root = tree({"RAW/": {"a.rw2": ""}, "a.rw2": "", "b.rw2": ""})
    plan = cleanup.plan(root)
    assert ops(plan, blocked=False) == [
        ("rename", "RAW", "RAW.ignored"),
        ("move", "b.rw2", "RAW.ignored/b.rw2")]
    assert ops(plan, blocked=True) == [
        ("move", "a.rw2", "RAW.ignored/a.rw2")]


def test_rename_target_exists(tree):
    root = tree({"Video/": {"v.mp4": ""}, "Video.ignored/": {}})
    plan = cleanup.plan(root, {"Video": "ponechat"})
    assert ops(plan, blocked=True) == [("rename", "Video", "Video.ignored")]


def test_plan_is_dry(tree):
    root = tree({"RAW/": {"a.rw2": ""}, "Video/": {"v.mp4": ""},
                 "b.rw2": ""})
    before = snapshot(root)
    cleanup.plan(root, {"Video": "presunout"})
    assert snapshot(root) == before


def states(result):
    return [(o["typ"], o["z"], o["stav"]) for o in result["operace"]]


def test_execute_move_folder_to_root(tree):
    files = {f"v{i:02}.mp4": str(i) for i in range(22)}
    root = tree({"Video/": dict(files, **{"Thumbs.db": ""}), "a.jpg": ""})
    result = cleanup.execute(root, {"Video": "presunout"})
    assert all(o["stav"] == "hotovo" for o in result["operace"])
    assert sorted(p.name for p in root.iterdir()) == sorted([*files, "a.jpg"])
    assert (root / "v07.mp4").read_text() == "7"


def test_execute_keep_folder_renamed(tree):
    root = tree({"RAWy/": {"a.rw2": "", "b.rw2": ""}, "c.RW2": "x"})
    result = cleanup.execute(root, {"RAWy": "ponechat"})
    assert states(result) == [("rename", "RAWy", "hotovo"),
                              ("move", "c.RW2", "hotovo")]
    assert sorted(p.name for p in root.iterdir()) == ["RAW.ignored"]
    assert sorted(p.name for p in (root / "RAW.ignored").iterdir()) == \
        ["a.rw2", "b.rw2", "c.RW2"]


def test_execute_creates_raw_ignored(tree):
    root = tree({"a.rw2": "", "a.jpg": ""})
    cleanup.execute(root)
    assert (root / "RAW.ignored" / "a.rw2").is_file()


def test_execute_collision_after_preview(tree, monkeypatch):
    root = tree({"Video/": {"a.mp4": "nový", "b.mp4": ""}})
    stale = cleanup.plan(root, {"Video": "presunout"})
    # Mezi náhledem a provedením vznikne v kořeni A.MP4.
    (root / "A.MP4").write_text("starý")
    monkeypatch.setattr(cleanup, "plan", lambda *a: stale)
    result = cleanup.execute(root, {"Video": "presunout"})
    assert states(result) == [("move", "Video/a.mp4", "blokovano"),
                              ("move", "Video/b.mp4", "hotovo"),
                              ("delete", "Video", "blokovano")]
    assert (root / "A.MP4").read_text() == "starý"
    assert (root / "Video" / "a.mp4").read_text() == "nový"


def test_execute_collision_replanned(tree):
    root = tree({"Video/": {"a.mp4": ""}})
    cleanup.plan(root, {"Video": "presunout"})
    (root / "a.mp4").write_text("starý")
    result = cleanup.execute(root, {"Video": "presunout"})
    assert {o["stav"] for o in result["operace"]} == {"blokovano"}
    assert (root / "a.mp4").read_text() == "starý"
    assert (root / "Video" / "a.mp4").exists()


def test_execute_permission_error(tree, monkeypatch):
    root = tree({"Video/": {"a.mp4": "", "b.mp4": "", "c.mp4": ""}})
    real = os.rename

    def rename(src, dst):
        if src.endswith("b.mp4"):
            raise PermissionError(13, "Permission denied", src)
        real(src, dst)
    monkeypatch.setattr(cleanup.os, "rename", rename)
    result = cleanup.execute(root, {"Video": "presunout"})
    assert states(result) == [("move", "Video/a.mp4", "hotovo"),
                              ("move", "Video/b.mp4", "chyba"),
                              ("move", "Video/c.mp4", "hotovo"),
                              ("delete", "Video", "blokovano")]
    assert "Permission denied" in result["operace"][1]["chyba"]
    assert (root / "Video" / "b.mp4").exists()


def test_execute_delete_refuses_non_empty(tree):
    root = tree({"Video/": {"a.mp4": ""}})
    with pytest.raises(OSError):
        cleanup._delete(root, "Video")
    assert (root / "Video" / "a.mp4").exists()


# --- vyřazení ---------------------------------------------------------------

def test_discard_planned(tree):
    root = tree({"P1503712.JPG": "", "a.jpg": ""})
    plan = cleanup.plan(root, raw_from_root=False, discard=["P1503712.JPG"])
    assert ops(plan) == [("move", "P1503712.JPG",
                          "k_odstraneni.ignored/P1503712.JPG")]
    assert plan["operace"][0]["vyradit"]
    assert plan["operace"][0]["soubor"] == "P1503712.JPG"


def test_discard_missing_file_skipped(tree):
    root = tree({"a.jpg": ""})
    assert ops(cleanup.plan(root, discard=["neni.jpg"])) == []


def test_discard_collision(tree):
    root = tree({"k_odstraneni.ignored/": {"A.JPG": "", "b.jpg.xmp": ""},
                 "a.jpg": "", "b.jpg": "", "c.jpg": ""})
    plan = cleanup.plan(root, discard=["a.jpg", "b.jpg", "c.jpg"])
    assert ops(plan, blocked=True) == [
        ("move", "a.jpg", "k_odstraneni.ignored/a.jpg"),
        ("move", "b.jpg", "k_odstraneni.ignored/b.jpg")]
    assert ops(plan, blocked=False) == [
        ("move", "c.jpg", "k_odstraneni.ignored/c.jpg")]


def test_discard_existing_folder_not_a_subfolder(tree):
    root = tree({"k_odstraneni.ignored/": {"x.jpg": ""}, "a.jpg": ""})
    plan = cleanup.plan(root, discard=["a.jpg"])
    assert plan["podslozky"] == []
    assert ops(plan) == [("move", "a.jpg", "k_odstraneni.ignored/a.jpg")]


def xmp_of(name):
    return f"<xmp>{name}</xmp>"


@pytest.mark.parametrize("existing", [False, True])
def test_execute_discard(tree, existing):
    spec = {"a.jpg": "A", "a.jpg.xmp": "starý", "b.jpg": "B"}
    if existing:
        spec["k_odstraneni.ignored/"] = {"x.jpg": "X"}
    root = tree(spec)
    result = cleanup.execute(root, discard=["a.jpg"], sidecar=xmp_of)
    assert states(result) == [("move", "a.jpg", "hotovo")]
    target = root / "k_odstraneni.ignored"
    assert (target / "a.jpg").read_text() == "A"
    assert (target / "a.jpg.xmp").read_text() == "<xmp>a.jpg</xmp>"
    assert not (root / "a.jpg").exists()
    assert not (root / "a.jpg.xmp").exists()
    assert (root / "b.jpg").exists()


def test_execute_discard_xmp_collision(tree):
    root = tree({"k_odstraneni.ignored/": {"a.jpg.xmp": "cizí"},
                 "a.jpg": "A"})
    result = cleanup.execute(root, discard=["a.jpg"], sidecar=xmp_of)
    assert states(result) == [("move", "a.jpg", "blokovano")]
    assert (root / "a.jpg").read_text() == "A"
    assert (root / "k_odstraneni.ignored" / "a.jpg.xmp").read_text() == "cizí"


def test_execute_discard_sidecar_fails(tree):
    root = tree({"a.jpg": "A", "a.jpg.xmp": "starý"})

    def failing(name):
        raise ValueError("neplatné datum")
    result = cleanup.execute(root, discard=["a.jpg"], sidecar=failing)
    assert states(result) == [("move", "a.jpg", "chyba")]
    assert (root / "a.jpg").read_text() == "A"
    assert (root / "a.jpg.xmp").read_text() == "starý"
    assert not (root / "k_odstraneni.ignored").exists()


def test_execute_discard_move_fails_removes_sidecar(tree, monkeypatch):
    root = tree({"a.jpg": "A"})

    def rename(src, dst):
        raise PermissionError(13, "Permission denied", src)
    monkeypatch.setattr(cleanup.os, "rename", rename)
    result = cleanup.execute(root, discard=["a.jpg"], sidecar=xmp_of)
    assert states(result) == [("move", "a.jpg", "chyba")]
    assert (root / "a.jpg").exists()
    assert list((root / "k_odstraneni.ignored").iterdir()) == []


def test_subfolder_samples_spread_media_first(tree):
    photos = {f"P{i:02}.jpg": "" for i in range(13)}
    root = tree({"PPA/": dict(photos, **{"a.txt": "", "Thumbs.db": ""}),
                 "Prez/": {"b.pdf": "", "a.pptx": "", "Thumbs.db": ""},
                 "Prázdná/": {}})
    folders = {f["nazev"]: f for f in cleanup.subfolders(root)}
    samples = folders["PPA"]["ukazky"]
    assert len(samples) == 8 and samples[0] == "P00.jpg"
    assert samples == sorted(set(samples)) and samples[-1] >= "P11.jpg"
    assert folders["Prez"]["ukazky"] == ["a.pptx", "b.pdf"]
    assert folders["Prázdná"]["ukazky"] == []


# --- ostatní soubory do ostatni.ignored (issue #11) ------------------------

def test_other_files_to_ostatni(tree):
    root = tree({"a.jpg": "", "a.jpg.xmp": "", "prezentace.zip": "",
                 "P1503713.JPG.xmp": "", "Thumbs.db": "",
                 "_metadata.json": "{}"})
    plan = cleanup.plan(root)
    # Pořadí podle druhu nálezu: nepodporované, pak osiřelé sidecary.
    assert ops(plan) == [
        ("move", "prezentace.zip", "ostatni.ignored/prezentace.zip"),
        ("move", "P1503713.JPG.xmp", "ostatni.ignored/P1503713.JPG.xmp")]
    assert plan["ostatni_v_koreni"] == 2


def test_other_files_disabled(tree):
    root = tree({"prezentace.zip": ""})
    plan = cleanup.plan(root, other=False)
    assert ops(plan) == []
    assert plan["ostatni_v_koreni"] == 1


def test_other_collision_and_existing_dir(tree):
    root = tree({"zprava.pdf": "", "b.doc": "",
                 "ostatni.ignored/": {"ZPRAVA.pdf": ""}})
    plan = cleanup.plan(root)
    assert ops(plan, blocked=True) == [
        ("move", "zprava.pdf", "ostatni.ignored/zprava.pdf")]
    assert ops(plan, blocked=False) == [
        ("move", "b.doc", "ostatni.ignored/b.doc")]
    # ostatni.ignored se jako podsložka přeskakuje.
    assert plan["podslozky"] == []


def test_other_target_is_file(tree):
    root = tree({"ostatni.ignored": "", "b.doc": ""})
    plan = cleanup.plan(root)
    # Soubor `ostatni.ignored` je sám nepodporovaný; cíl blokuje oba.
    assert ops(plan, blocked=True) == [
        ("move", "b.doc", "ostatni.ignored/b.doc"),
        ("move", "ostatni.ignored", "ostatni.ignored/ostatni.ignored")]
    assert ops(plan, blocked=False) == []


def test_sidecar_of_file_from_subfolder_not_orphan(tree):
    root = tree({"v.mp4.xmp": "", "Video/": {"v.mp4": ""}})
    assert ops(cleanup.plan(root, {"Video": "presunout"})) == [
        ("move", "Video/v.mp4", "v.mp4"), ("delete", "Video", None)]
    # Bez přesunu podsložky je sidecar osiřelý.
    assert ops(cleanup.plan(root)) == [
        ("move", "v.mp4.xmp", "ostatni.ignored/v.mp4.xmp")]


def test_unsupported_file_from_subfolder_stays_for_next_plan(tree):
    root = tree({"Docs/": {"a.pdf": ""}})
    assert ops(cleanup.plan(root, {"Docs": "presunout"})) == [
        ("move", "Docs/a.pdf", "a.pdf"), ("delete", "Docs", None)]


def test_execute_other(tree):
    root = tree({"zprava.pdf": "obsah", "x.jpg.xmp": "<x/>",
                 "ostatni.ignored/": {"x.jpg.xmp": "jiný"}})
    result = cleanup.execute(root)
    assert [(o["z"], o["stav"]) for o in result["operace"]] == [
        ("zprava.pdf", "hotovo"), ("x.jpg.xmp", "blokovano")]
    assert (root / "ostatni.ignored" / "zprava.pdf").read_text() == "obsah"
    assert (root / "ostatni.ignored" / "x.jpg.xmp").read_text() == "jiný"
    assert (root / "x.jpg.xmp").read_text() == "<x/>"


def test_execute_other_creates_dir(tree):
    root = tree({"b.doc": "x"})
    cleanup.execute(root)
    assert (root / "ostatni.ignored" / "b.doc").is_file()
    assert not (root / "b.doc").exists()
