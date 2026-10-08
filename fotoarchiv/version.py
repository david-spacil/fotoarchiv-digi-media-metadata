"""Verze běžící aplikace (issue #12).

V pracovní kopii z gitu (`git describe`), v Docker image ze souboru
`VERZE`, který zapíše build (image `.git` nemá). Zjišťuje se jednou při
startu, aby po `git pull` neukazovala kód, který ještě neběží.
"""
import subprocess
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
FILE = PACKAGE / "VERZE"


def from_git(root):
    """`git describe` v pracovní kopii `root`, jinak None."""
    if not (root / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "describe", "--tags", "--always",
             "--dirty"],
            capture_output=True, text=True, timeout=5, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def from_file(path):
    """Verze zapsaná při buildu image, jinak None."""
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def app_version(root=PACKAGE.parent, file=FILE):
    """Verze aplikace, nebo None, když ji nejde zjistit."""
    return from_git(root) or from_file(file)
