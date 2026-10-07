import hashlib
import importlib.util
import os
from pathlib import Path

import pytest

from .conftest import snapshot

_spec = importlib.util.spec_from_file_location(
    "pretridit", Path(__file__).parent.parent / "scripts" / "pretridit.py")
pretridit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pretridit)


def sha_of(root):
    out = {}
    for rel in pretridit.walk(root):
        out[rel] = hashlib.sha256((root / rel).read_bytes()).hexdigest()
    return out


def all_sha(root):
    """Hashe všech souborů včetně duplicit (pro kontrolu multisetu)."""
    out = {}
    for top, _, files in os.walk(root):
        for name in files:
            if name.lower() != "thumbs.db":
                p = Path(top) / name
                out[str(p.relative_to(root))] = hashlib.sha256(
                    p.read_bytes()).hexdigest()
    return out


def plan(root, mapa, archiv_sha=None):
    rows, shared = pretridit.make_plan(root, sha_of(root), mapa, archiv_sha)
    return {(r[0], r[1], r[2]) for r in rows}, rows, shared


def as_dicts(rows):
    return [dict(zip(pretridit.PLAN_FIELDS, map(str, r))) for r in rows]


@pytest.fixture
def pretrid(tree):
    return tree({
        "DOD 2016/": {"DOD 11.11/": {"a.jpg": "A", "b.jpg": "B"},
                      "fb/": {"a.jpg": "A"}},
        "_personalia/": {"Fotografie/": {
            "DOD 2016/": {"DOD 11.11/": {"a.jpg": "A", "b.jpg": "B2",
                                         "c.jpg": "C", "Thumbs.db": "x"}},
            "Ze života/": {"z.jpg": "Z"}}},
        "Jubilea/": {"Stuchlík 70/": {"s.jpg": "S"}},
    })


MAPA = [("_personalia/Fotografie/DOD 2016", "DOD 2016"),
        ("Jubilea/Stuchlík 70", "Stuchlík 70")]


def test_plan_merges_dedups_and_renames(pretrid):
    ops, _, shared = plan(pretrid, MAPA)
    P = "_personalia/Fotografie/DOD 2016/DOD 11.11"
    assert ops == {
        # Kopie v nepřesouvané složce má přednost, mělčí cesta před fb/.
        ("duplicita", f"{P}/a.jpg", f"_duplicity.ignored/{P}/a.jpg"),
        ("duplicita", "DOD 2016/fb/a.jpg",
         "_duplicity.ignored/DOD 2016/fb/a.jpg"),
        ("prejmenovat", f"{P}/b.jpg", "DOD 2016/DOD 11.11/b_2.jpg"),
        ("presun", f"{P}/c.jpg", "DOD 2016/DOD 11.11/c.jpg"),
        ("presun", "Jubilea/Stuchlík 70/s.jpg", "Stuchlík 70/s.jpg"),
    }
    assert shared == []


def test_plan_changes_nothing(pretrid):
    before = snapshot(pretrid)
    plan(pretrid, MAPA)
    assert snapshot(pretrid) == before


def test_archive_duplicates_move_all_copies(tree):
    root = tree({"DOD 2015/": {"a.jpg": "A", "n.jpg": "N"},
                 "x/": {"a.jpg": "A"}})
    archiv = {"2015-11-06 DOD 2015/a.jpg":
              hashlib.sha256(b"A").hexdigest()}
    ops, _, shared = plan(root, [("x", "DOD 2015")], archiv)
    assert {o[1] for o in ops if o[0] == "duplicita"} == {
        "DOD 2015/a.jpg", "x/a.jpg"}
    assert ("presun", "x/a.jpg", "DOD 2015/a.jpg") not in ops


def test_shared_content_across_roots_is_reported_only(tree):
    root = tree({"A/": {"f.jpg": "F"}, "B/": {"g.jpg": "F"}})
    ops, _, shared = plan(root, [])
    assert ops == set()
    assert [r for _, r in shared] == [["A", "B"]]


def test_missing_hash_refuses(tree):
    root = tree({"A/": {"f.jpg": "F"}})
    with pytest.raises(SystemExit):
        pretridit.make_plan(root, {}, [])


def test_execute_keeps_content_and_undo_restores(pretrid, tmp_path_factory):
    before_snap = snapshot(pretrid)
    before = all_sha(pretrid)
    _, rows, _ = plan(pretrid, MAPA)
    log = tmp_path_factory.mktemp("log") / "log.csv"
    assert pretridit.execute(pretrid, as_dicts(rows), log) == len(rows)

    after = all_sha(pretrid)
    assert pretridit.compare(before, after) == ({}, {})
    assert (pretrid / "DOD 2016/DOD 11.11/b_2.jpg").read_text() == "B2"
    assert (pretrid / "_duplicity.ignored/DOD 2016/fb/a.jpg").exists()
    # Prázdné zdroje zmizí, Thumbs.db složku drží.
    assert not (pretrid / "Jubilea").exists()
    assert (pretrid / "_personalia/Fotografie/DOD 2016/DOD 11.11/Thumbs.db"
            ).exists()

    pretridit.undo(pretrid, log)
    assert {k: v[0] for k, v in snapshot(pretrid).items()} == {
        k: v[0] for k, v in before_snap.items()}


def test_execute_never_overwrites(pretrid, tmp_path_factory):
    _, rows, _ = plan(pretrid, MAPA)
    (pretrid / "Stuchlík 70").mkdir()
    (pretrid / "Stuchlík 70/s.jpg").write_text("jiný")
    rows = [r for r in as_dicts(rows) if r["cil"] == "Stuchlík 70/s.jpg"]
    with pytest.raises(SystemExit):
        pretridit.execute(pretrid, rows,
                          tmp_path_factory.mktemp("log") / "log.csv")
    assert (pretrid / "Stuchlík 70/s.jpg").read_text() == "jiný"
    assert (pretrid / "Jubilea/Stuchlík 70/s.jpg").read_text() == "S"


def test_execute_refuses_changed_size(pretrid, tmp_path_factory):
    _, rows, _ = plan(pretrid, MAPA)
    (pretrid / "Jubilea/Stuchlík 70/s.jpg").write_text("SSS")
    with pytest.raises(SystemExit):
        pretridit.execute(pretrid, as_dicts(rows),
                          tmp_path_factory.mktemp("log") / "log.csv")
