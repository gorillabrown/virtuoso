"""Test configuration.

Pins the import root so `tools.*` resolves regardless of where pytest is invoked
from, and isolates every test from this machine's real Virtuoso state: the
install record and the launchers live under ``VIRTUOSO_HOME``, and no test may
touch the developer's own ``~/.virtuoso``.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

PLUGIN_ROOT = str(Path(__file__).resolve().parent)


@pytest.fixture(autouse=True)
def isolated_home(tmp_path_factory, monkeypatch):
    """Every test gets its own VIRTUOSO_HOME, outside any project root under test, and
    empty host folders, so no test reads this machine's real transcripts."""
    home = tmp_path_factory.mktemp("virtuoso-home")
    monkeypatch.setenv("VIRTUOSO_HOME", str(home))
    monkeypatch.delenv("VIRTUOSO_PLUGIN_ROOT", raising=False)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(home / "host-a"))
    monkeypatch.setenv("CODEX_HOME", str(home / "host-b"))
    return home


@pytest.fixture
def project(tmp_path):
    """An empty project root."""
    root = tmp_path / "project"
    root.mkdir()
    return root


def skill_text(skill_dir):
    """A skill's full text: its SKILL.md followed by every file in its references/.

    A skill is its folder, not one file. Long skills keep their core flow in SKILL.md
    and hand off to references/ (Antigravity loads only the first 24,000 bytes of a
    SKILL.md body), so a rule a test pins may live in either place.
    """
    skill_dir = Path(skill_dir)
    parts = [(skill_dir / "SKILL.md").read_text(encoding="utf-8")]
    refs = skill_dir / "references"
    if refs.is_dir():
        parts += [p.read_text(encoding="utf-8") for p in sorted(refs.glob("*.md"))]
    return "\n".join(parts)


def snapshot_tree(root):
    """{relative path: raw bytes} for every file under ``root``.

    Used by the byte-for-byte preservation tests: comparing two snapshots proves
    both that nothing changed *and* that nothing new appeared.
    """
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__",)]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace("\\", "/")
            with open(full, "rb") as handle:
                out[rel] = handle.read()
    return out
