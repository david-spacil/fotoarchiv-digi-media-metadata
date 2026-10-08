import subprocess

import pytest

from fotoarchiv import version


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@example.org")
    git(root, "config", "user.name", "Test")
    (root / "a.txt").write_text("a")
    git(root, "add", "a.txt")
    git(root, "commit", "-qm", "první")
    git(root, "tag", "v0.2.0")
    return root


def test_tag(repo, tmp_path):
    assert version.app_version(repo, tmp_path / "VERZE") == "v0.2.0"


def test_commit_after_tag_and_dirty(repo, tmp_path):
    (repo / "a.txt").write_text("b")
    git(repo, "commit", "-qam", "druhý")
    v = version.app_version(repo, tmp_path / "VERZE")
    assert v.startswith("v0.2.0-1-g") and not v.endswith("-dirty")
    (repo / "a.txt").write_text("c")
    assert version.app_version(repo, tmp_path / "VERZE") == v + "-dirty"


def test_file_without_git(tmp_path):
    f = tmp_path / "VERZE"
    f.write_text("v0.3.0\n")
    assert version.app_version(tmp_path, f) == "v0.3.0"


def test_git_wins_over_file(repo, tmp_path):
    f = tmp_path / "VERZE"
    f.write_text("v9.9.9\n")
    assert version.app_version(repo, f) == "v0.2.0"


@pytest.mark.parametrize("content", [None, "", "\n"])
def test_unknown(tmp_path, content):
    f = tmp_path / "VERZE"
    if content is not None:
        f.write_text(content)
    assert version.app_version(tmp_path, f) is None


def test_broken_git_falls_back_to_file(tmp_path):
    (tmp_path / ".git").write_text("gitdir: /neexistuje\n")
    f = tmp_path / "VERZE"
    f.write_text("v0.3.0")
    assert version.app_version(tmp_path, f) == "v0.3.0"
