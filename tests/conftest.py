import os

import pytest


def make_tree(root, spec):
    """Vytvoří strom: {"soubor": "obsah", "slozka/": {...}}."""
    for name, value in spec.items():
        if name.endswith("/"):
            path = root / name[:-1]
            path.mkdir()
            make_tree(path, value)
        else:
            (root / name).write_text(value)


def snapshot(root):
    """Stav stromu (cesty, velikosti, mtime) pro ověření, že se nezměnil."""
    result = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            st = os.stat(os.path.join(dirpath, name))
            rel = os.path.relpath(os.path.join(dirpath, name), root)
            result[rel] = (st.st_size, st.st_mtime_ns)
    return result


@pytest.fixture
def tree(tmp_path):
    def build(spec):
        make_tree(tmp_path, spec)
        return tmp_path
    return build
