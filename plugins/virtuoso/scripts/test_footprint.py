"""The footprint tool (VIR-054): audit, classify, remove and extract on real git trees.

Every test injects its scan places (drive root, %TEMP%, parent folder, temp role)
under ``tmp_path``, so none reads this machine's real drive root or temp folder.
"""
import os
import subprocess
import sys
import time

import pytest

from conftest import snapshot_tree
from tools.governance import footprint as fp
from tools.governance.errors import GovernanceError

GIT_IDENTITY = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}


def git(cwd, *args):
    proc = subprocess.run(["git", "-c", "init.defaultBranch=main", "-c", "core.autocrlf=false",
                           *args], cwd=str(cwd), capture_output=True, text=True,
                          env=dict(os.environ, **GIT_IDENTITY))
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def commit(cwd, name, text="x\n"):
    (cwd / name).write_text(text, encoding="utf-8")
    git(cwd, "add", name)
    git(cwd, "commit", "-q", "-m", "add " + name)
    return git(cwd, "rev-parse", "HEAD")


@pytest.fixture
def places(tmp_path):
    """A primary repository on main under a parent folder, with an empty drive root,
    temp folder and temp role beside it."""
    parent, drive, temp = tmp_path / "projects", tmp_path / "drive", tmp_path / "tmp"
    for folder in (parent, drive, temp):
        folder.mkdir()
    primary = parent / "primary"
    primary.mkdir()
    git(primary, "init", "-q")
    commit(primary, "a.txt")
    temp_role = primary / "scratch-role"
    temp_role.mkdir()
    (primary / ".gitignore").write_text("scratch-role/\n", encoding="utf-8")
    git(primary, "add", ".gitignore")
    git(primary, "commit", "-q", "-m", "ignore the temp role")
    return {"primary": primary, "parent": parent, "drive": drive, "temp": temp,
            "temp_role": temp_role, "evidence": primary / "evidence"}


def context(places, live=frozenset()):
    return fp.make_context(str(places["primary"]), temp_role=str(places["temp_role"]),
                           evidence_dirs=[str(places["evidence"])], live_items=set(live),
                           drive_root=str(places["drive"]), temp_dir=str(places["temp"]),
                           parent_dir=str(places["parent"]))


def entry(report, path):
    wanted = os.path.normcase(os.path.realpath(str(path)))
    for cand in report["candidates"]:
        if os.path.normcase(os.path.realpath(cand["path"])) == wanted:
            return cand
    raise AssertionError("%s not among %s" % (path, [c["path"] for c in report["candidates"]]))


def worktree(places, name, branch, start="main"):
    path = places["parent"] / name
    git(places["primary"], "worktree", "add", "-q", "-b", branch, str(path), start)
    return path


def basetemp(folder):
    folder.mkdir()
    for name in ("test_alpha0", "test_beta12", "test_gamma_case3"):
        (folder / name).mkdir()
        (folder / name / "f.txt").write_text("x", encoding="utf-8")
    return folder


def test_the_audit_writes_nothing(places):
    worktree(places, "wt-merged", "merged")
    dirty = worktree(places, "wt-dirty", "dirty")
    (dirty / "new.txt").write_text("uncommitted", encoding="utf-8")
    basetemp(places["drive"] / "bt")
    (places["temp_role"] / "notes").mkdir()
    root = places["primary"].parent.parent
    before = snapshot_tree(root)
    status = git(places["primary"], "status", "--porcelain")
    report = fp.audit(context(places))
    assert len(report["candidates"]) == 4
    assert report["freeBytes"] > 0
    assert snapshot_tree(root) == before
    assert git(places["primary"], "status", "--porcelain") == status


def test_a_clean_merged_worktree_is_redundant(places):
    path = worktree(places, "wt-merged", "merged")
    cand = entry(fp.audit(context(places)), path)
    assert (cand["kind"], cand["class"]) == ("worktree", "redundant")
    assert cand["reason"] == "clean, and main contains its HEAD"


def test_uncommitted_files_make_a_tree_unique(places):
    path = worktree(places, "wt-dirty", "dirty")
    (path / "new.txt").write_text("uncommitted", encoding="utf-8")
    cand = entry(fp.audit(context(places)), path)
    assert cand["class"] == "unique"
    assert cand["reason"] == "1 uncommitted path(s)"


def test_an_unmerged_commit_makes_a_clone_unique(places):
    clone = places["drive"] / "old-clone"
    git(places["parent"], "clone", "-q", str(places["primary"]), str(clone))
    sha = commit(clone, "only-here.txt")
    cand = entry(fp.audit(context(places)), clone)
    assert (cand["kind"], cand["class"]) == ("clone", "unique")
    assert cand["reason"] == "1 commit(s) that no branch or remote ref of the primary contains"
    assert cand["uniqueCommits"] == [sha]


def test_a_worktree_on_a_live_items_branch_is_in_flight(places):
    path = worktree(places, "wt-live", "VIR-900-retry")
    cand = entry(fp.audit(context(places, live={"VIR-900"})), path)
    assert cand["class"] == "in-flight"
    assert cand["reason"] == "branch VIR-900-retry belongs to VIR-900, which is not terminal"
    unread = fp.make_context(str(places["primary"]), temp_role=str(places["temp_role"]),
                             live_items=None, drive_root=None, temp_dir=None,
                             parent_dir=str(places["parent"]))
    assert entry(fp.audit(unread), path)["class"] == "in-flight"


def test_an_epic_packet_is_evidence(places):
    packet = places["temp_role"] / "2026-10-24-cost-guards"
    packet.mkdir()
    (packet / "charter.md").write_text("# Charter\n", encoding="utf-8")
    cand = entry(fp.audit(context(places)), packet)
    assert (cand["kind"], cand["class"]) == ("scratch", "evidence")
    assert cand["reason"] == "an epic packet (holds charter.md)"
    assert cand["next"].startswith("owner only: ")


def test_a_pytest_basetemp_is_regenerable(places):
    folder = basetemp(places["temp"] / "vbt")
    not_one = places["temp"] / "photos"
    not_one.mkdir()
    (not_one / "test_one1").mkdir()
    (not_one / "holiday").mkdir()
    (not_one / "family").mkdir()
    suite = places["temp"] / "suite-bt"     # this repository's shape: a home folder per test
    suite.mkdir()
    for name in ("test_alpha0", "test_beta1", "virtuoso-home0", "virtuoso-home1",
                 "virtuoso-home2"):
        (suite / name).mkdir()
    git(suite / "test_alpha0", "init", "-q", "repo")    # tests build repositories; still pytest's
    report = fp.audit(context(places))
    cand = entry(report, folder)
    assert (cand["kind"], cand["class"]) == ("basetemp", "regenerable")
    assert cand["reason"] == "a pytest basetemp (per-test folders)"
    assert cand["size"] == 3
    assert entry(report, suite)["class"] == "regenerable"
    with pytest.raises(AssertionError):
        entry(report, not_one)


def test_remove_refuses_unique_in_flight_and_evidence(places):
    dirty = worktree(places, "wt-dirty", "dirty")
    (dirty / "new.txt").write_text("uncommitted", encoding="utf-8")
    live = worktree(places, "wt-live", "VIR-900")
    packet = places["temp_role"] / "packet"
    packet.mkdir()
    (packet / "charter.md").write_text("# Charter\n", encoding="utf-8")
    hidden = basetemp(places["temp"] / "bt-with-repo")    # a numbered folder that is a repo
    git(places["parent"], "clone", "-q", str(places["primary"]), str(hidden / "work3"))
    ctx = context(places, live={"VIR-900"})
    for path, cls in ((dirty, "unique"), (live, "in-flight"), (packet, "evidence"),
                      (hidden, "unique")):
        with pytest.raises(GovernanceError) as refused:
            fp.remove(ctx, str(path), apply=True)
        assert "refused to remove" in str(refused.value)
        assert "it is %s" % cls in str(refused.value)
        assert path.exists()


def _junction(link, target):
    proc = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                          capture_output=True, text=True)
    return proc.returncode == 0


def test_remove_unlinks_links_before_deleting_and_never_follows_them(places, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("keep me", encoding="utf-8")
    folder = basetemp(places["drive"] / "bt")
    tree = worktree(places, "wt-merged", "merged")       # links in an ignored folder of it
    (tree / "scratch-role").mkdir()
    expected, skipped = 0, []
    try:
        os.symlink(str(outside), str(folder / "test_alpha0" / "sym"), target_is_directory=True)
        os.symlink(str(outside), str(tree / "scratch-role" / "sym"), target_is_directory=True)
        expected += 1
    except (OSError, NotImplementedError) as exc:
        skipped.append("symlink: %s" % exc)
    if sys.platform == "win32":
        if _junction(folder / "test_beta12" / "junction", outside) and \
                _junction(tree / "scratch-role" / "junction", outside):
            expected += 1
        else:
            skipped.append("junction: mklink /J failed on this runner")
    if not expected:
        pytest.skip("no link could be created here: %s" % "; ".join(skipped))
    ctx = context(places)
    for target in (folder, tree):
        result = fp.remove(ctx, str(target), apply=True)
        assert result["applied"] is True
        assert result["linksRemoved"] == expected, target
        assert not target.exists()
        assert sentinel.read_text(encoding="utf-8") == "keep me", target
        assert result["freeAfter"] > 0 and result["freeBefore"] > 0


def test_remove_needs_apply(places):
    path = worktree(places, "wt-merged", "merged")
    folder = basetemp(places["temp"] / "bt")
    ctx = context(places)
    for target in (path, folder):
        preview = fp.remove(ctx, str(target))
        assert preview["applied"] is False
        assert preview["note"] == "preview only: add --apply to remove"
        assert target.exists()
    done = fp.remove(ctx, str(path), apply=True)
    assert done["method"] == ("untracked links removed first, then git worktree remove and "
                              "git worktree prune")
    assert not path.exists()
    assert str(path).replace("\\", "/") not in git(places["primary"], "worktree", "list")
    loose = places["temp_role"] / "notes.txt"             # a file, not a folder
    loose.write_text("scratch", encoding="utf-8")
    assert fp.remove(ctx, str(loose))["applied"] is False and loose.exists()
    assert fp.remove(ctx, str(loose), apply=True)["linksRemoved"] == 0
    assert not loose.exists()


def test_extract_writes_each_unique_commit_as_a_patch(places):
    path = worktree(places, "wt-work", "work")
    first, second = commit(path, "one.txt"), commit(path, "two.txt")
    git(path, "checkout", "-q", "-b", "side", first)          # a unique merge commit too
    commit(path, "side.txt")
    git(path, "checkout", "-q", "work")
    git(path, "merge", "-q", "--no-ff", "-m", "merge side", "side")
    git(path, "branch", "-q", "-D", "side")
    merge = git(path, "rev-parse", "HEAD")
    (path / "a.txt").write_text("changed\n", encoding="utf-8")
    (path / "new.txt").write_text("only on disk\n", encoding="utf-8")
    ctx = context(places)
    preview = fp.extract(ctx, str(path))
    assert preview["applied"] is False and preview["commits"][0] == first   # parents first
    assert preview["commits"][-1] == merge and second in preview["commits"]
    assert preview["merges"] == [merge] and preview["untracked"] == 1
    target = places["temp_role"] / "footprint-extract" / ("wt-work-" + merge[:10])
    assert not target.exists()
    done = fp.extract(ctx, str(path), apply=True)
    patches = sorted(p.name for p in target.glob("*.patch"))
    assert patches[0] == "0001-add-one.txt.patch" and len(patches) == 3   # no merge patch
    assert sorted(p[5:] for p in patches[1:]) == ["add-side.txt.patch", "add-two.txt.patch"]
    assert "From %s" % first in (target / patches[0]).read_text(encoding="utf-8")
    assert "+changed" in (target / "uncommitted.diff").read_text(encoding="utf-8")
    assert "+only on disk" in (target / "untracked.diff").read_text(encoding="utf-8")
    assert merge in git(places["primary"], "bundle", "list-heads", str(target / "unique.bundle"))
    assert done["uncommitted"] == 2
    assert entry(fp.audit(ctx), target.parent)["class"] == "evidence"


def test_dispatch_scope_lists_only_the_runs_own_folders(places):
    basetemp(places["temp"] / "old-bt")
    time.sleep(1.1)                       # commit times are whole seconds
    commit(places["primary"], "base.txt")  # the run's merge base, after old-bt
    worktree(places, "wt-other", "VIR-800")
    own = worktree(places, "wt-own", "VIR-900")
    worktree(places, "wt-own-2", "VIR-900-fix")
    basetemp(places["temp"] / "new-bt")
    time.sleep(1.1)
    commit(own, "work.txt")                    # merged: the merge base is now the branch tip
    git(places["primary"], "merge", "-q", "--ff-only", "VIR-900")
    report = fp.audit(context(places), dispatch="VIR-900")
    listed = {os.path.basename(c["path"]) for c in report["candidates"]}
    assert listed == {"wt-own", "wt-own-2", "new-bt"}
    assert report["dispatch"] == "VIR-900"
