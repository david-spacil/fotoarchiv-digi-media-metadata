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
