"""Tests for release.py's publish step (VIR-008).

Unlike test_release_pipeline.py, these use git: throwaway repositories in a temporary
directory -- a development repository, and a bare stand-in for the public one that starts
out carrying development material, as the real public repository did before its first
publish. No network, no real machine state.
"""
import importlib.util
import os
import re
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("release_publish", os.path.join(_HERE, "release.py"))
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)

_IDENTITY = {"GIT_AUTHOR_NAME": "Release Test", "GIT_AUTHOR_EMAIL": "release@example.invalid",
             "GIT_COMMITTER_NAME": "Release Test", "GIT_COMMITTER_EMAIL": "release@example.invalid"}
#: Written out, not derived from rp.PUBLIC_TREE: a fixture built from the code under test
#: would agree with any change to it. One file per public entry, per VIR-008.
PUBLIC_FILES = (".claude-plugin/f.txt", ".gitattributes", ".github/f.txt", ".gitignore",
                "LICENSE", "README.md", "RELEASE-NOTES.md", "docs/MIGRATION-1.4.md",
                "plugins/f.txt")
PRIVATE = ("docs/plans/x.md", "Virtuoso/workspace-layout.json", "Project Documentation/a.md")


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True,
                          text=True).stdout.strip()


def _write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _new_repo(path, files, text):
    _git(path.parent, "init", "-q", str(path))
    _git(path, "symbolic-ref", "HEAD", "refs/heads/main")
    for rel in files:
        _write(path, rel, text)
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "fixture")


@pytest.fixture
def repos(tmp_path, monkeypatch):
    for key, value in _IDENTITY.items():
        monkeypatch.setenv(key, value)
    public = tmp_path / "public.git"
    _git(tmp_path, "init", "-q", "--bare", str(public))
    _git(public, "symbolic-ref", "HEAD", "refs/heads/main")
    seed = tmp_path / "seed"
    _new_repo(seed, list(PUBLIC_FILES) + ["docs/plans/x.md"], "old\n")
    _git(seed, "push", "-q", str(public), "main")
    dev = tmp_path / "dev"
    _new_repo(dev, list(PUBLIC_FILES) + list(PRIVATE), "new\n")
    _git(dev, "remote", "add", "origin", str(tmp_path / "dev-origin.git"))
    monkeypatch.setattr(rp, "REPO", str(dev))
    monkeypatch.setenv(rp.PUBLIC_REMOTE_ENV, str(public))
    return dev, public


def test_public_tree_is_the_specified_set():
    assert set(rp.PUBLIC_TREE) == {".claude-plugin", ".gitattributes", ".github", ".gitignore",
                                   "LICENSE", "README.md", "RELEASE-NOTES.md",
                                   "docs/MIGRATION-1.4.md", "plugins"}


def test_public_tree_keeps_only_release_paths(repos):
    paths = {path for _mode, _sha, path in rp.public_tree_files("HEAD")}
    assert paths == set(PUBLIC_FILES)
    assert not paths & set(PRIVATE)


def test_public_tree_refuses_a_missing_public_path(repos):
    dev, _public = repos
    _git(dev, "rm", "-q", "docs/MIGRATION-1.4.md")
    _git(dev, "commit", "-q", "-m", "drop the migration guide")
    with pytest.raises(rp.Gate, match="docs/MIGRATION-1.4.md"):
        rp.public_tree_files("HEAD")


def test_publish_commits_the_release_tree_once_and_tags_it(repos):
    _dev, public = repos
    before = _git(public, "rev-parse", "main")
    commit = rp.publish_release("9.9.9", "test")
    assert _git(public, "rev-parse", "main") == commit != before
    assert _git(public, "rev-parse", "main~1") == before
    published = set(_git(public, "ls-tree", "-r", "--name-only", "main").splitlines())
    assert published == set(PUBLIC_FILES)
    assert _git(public, "rev-parse", "refs/tags/v9.9.9") == commit


def test_publishing_again_is_a_no_op(repos):
    _dev, public = repos
    first = rp.publish_release("9.9.9")
    assert rp.publish_release("9.9.9") == first
    assert _git(public, "rev-parse", "main") == first
    assert _git(public, "rev-parse", "refs/tags/v9.9.9") == first


def test_publish_refuses_a_tag_pointing_elsewhere(repos):
    _dev, public = repos
    before = _git(public, "rev-parse", "main")
    _git(public, "tag", "v9.9.9", before)
    with pytest.raises(rp.Gate, match="never moved"):
        rp.publish_release("9.9.9")
    assert _git(public, "rev-parse", "main") == before


def test_publish_refuses_when_origin_is_the_public_repository(repos):
    dev, public = repos
    _git(dev, "remote", "set-url", "origin", str(public))
    with pytest.raises(rp.Gate, match="origin is the public repository"):
        rp.publish_release("9.9.9")


def test_preview_pushes_nothing(repos, capsys):
    _dev, public = repos
    before = _git(public, "rev-parse", "main")
    assert rp.publish_release(None, preview=True) is None
    assert _git(public, "rev-parse", "main") == before
    assert _git(public, "tag") == ""
    out = capsys.readouterr().out
    assert "D docs/plans/x.md" in out
    assert "Virtuoso/workspace-layout.json" not in out


def test_readme_links_resolve_inside_the_public_tree():
    with open(os.path.join(rp.REPO, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    links = [link.split("#", 1)[0] for link in re.findall(r"\]\(([^)\s]+)\)", readme)]
    local = [link[2:] if link.startswith("./") else link for link in links
             if link and not re.match(r"^[a-z][a-z0-9+.-]*:", link) and not link.startswith("#")]
    outside = [link for link in local
               if not any(link == entry or link.startswith(entry + "/") for entry in rp.PUBLIC_TREE)]
    assert local, "the README links to repository files"
    assert outside == [], "README links outside the public tree: %s" % outside


def test_publish_refuses_when_head_is_not_main(repos):
    dev, public = repos
    before = _git(public, "rev-parse", "main")
    _git(dev, "checkout", "-q", "-b", "feature")
    _write(dev, "plugins/f.txt", "feature\n")
    _git(dev, "commit", "-q", "-am", "feature work")
    with pytest.raises(rp.Gate, match="HEAD is not main"):
        rp.publish_release("9.9.9")
    assert _git(public, "rev-parse", "main") == before


def test_remote_spellings_of_one_repository_compare_equal():
    public = rp._normalized_remote("https://github.com/gorillabrown/virtuoso")
    for spelling in ("git@github.com:gorillabrown/virtuoso.git",
                     "https://github.com/gorillabrown/virtuoso.git",
                     "https://user:token@github.com/gorillabrown/virtuoso/",
                     "ssh://git@github.com/gorillabrown/virtuoso"):
        assert rp._normalized_remote(spelling) == public, spelling
    assert rp._normalized_remote("https://github.com/gorillabrown/virtuoso-dev") != public
