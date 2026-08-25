"""Repository-state coverage (items 66-73, 97).

Every state the audit called out: unrelated dirty files, existing staging,
detached HEAD, no remote, a renamed default branch, multiple worktrees, and
local commits ahead of the remote. Nothing here mutates a repository through the
plugin; the module under test is read-only by construction.
"""
from __future__ import annotations

import os
import subprocess

import pytest

from tools.governance import repostate


def git(root, *args, check=True):
    completed = subprocess.run(["git", "-C", str(root), *args],
                               capture_output=True, text=True)
    if check and completed.returncode != 0:
        raise AssertionError("git %s failed: %s" % (" ".join(args), completed.stderr))
    return completed.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    git(root, "config", "commit.gpgsign", "false")
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    git(root, "add", "README.md")
    git(root, "commit", "-qm", "initial")
    return root


@pytest.fixture
def repo_with_remote(tmp_path, repo):
    origin = tmp_path / "upstream.git"
    git(repo, "init", "--bare", "-q", str(origin))
    # Deliberately NOT named "origin": nothing may assume that name.
    git(repo, "remote", "add", "upstream", str(origin))
    branch = git(repo, "branch", "--show-current")
    git(repo, "push", "-q", "-u", "upstream", branch)
    return repo


# --- detection, not assumption -------------------------------------------------


def test_a_repository_with_no_remote_is_a_normal_state(repo):
    state = repostate.inspect(str(repo))
    assert state.is_repository is True
    assert state.has_remote is False
    assert state.remote_source == "none"
    finding = repostate.readiness(state, [])
    assert finding["result"] == "PASS", finding["problems"]


def test_require_remote_turns_a_missing_remote_into_a_finding(repo):
    state = repostate.inspect(str(repo))
    finding = repostate.readiness(state, [], {"requireRemote": True})
    assert finding["result"] == "GAP"
    assert any("requireRemote" in p for p in finding["problems"])


def test_the_remote_is_detected_not_assumed(repo_with_remote):
    state = repostate.inspect(str(repo_with_remote))
    assert state.remote == "upstream"
    assert state.remote != "origin"
    assert state.remote_source in ("upstream", "sole")


def test_several_remotes_with_no_upstream_is_reported_not_guessed(tmp_path, repo):
    git(repo, "remote", "add", "one", str(tmp_path / "one.git"))
    git(repo, "remote", "add", "two", str(tmp_path / "two.git"))
    state = repostate.inspect(str(repo))
    assert state.remote == ""
    assert state.remote_source == "ambiguous"
    finding = repostate.readiness(state, [])
    assert any("policy.git.remote" in p for p in finding["problems"])


def test_policy_overrides_detection(repo_with_remote):
    state = repostate.inspect(str(repo_with_remote),
                              {"remote": "upstream", "defaultBranch": "trunk"})
    assert state.remote_source == "policy"
    assert state.default_branch == "trunk"
    assert state.default_branch_source == "policy"


def test_a_renamed_default_branch_is_detected(repo):
    git(repo, "branch", "-m", "trunk")
    state = repostate.inspect(str(repo))
    assert state.current_branch == "trunk"
    assert state.default_branch == "trunk"
    assert state.default_branch != "main"


# --- working-tree scope --------------------------------------------------------


def test_unrelated_dirty_paths_are_reported_and_left_alone(repo):
    (repo / "scoped.txt").write_text("mine\n", encoding="utf-8")
    (repo / "unrelated.txt").write_text("someone else's\n", encoding="utf-8")
    state = repostate.inspect(str(repo))
    scoped, unrelated = state.scope(["scoped.txt"])
    assert scoped == ["scoped.txt"]
    assert unrelated == ["unrelated.txt"]
    # Reading never changes anything.
    assert (repo / "unrelated.txt").read_text(encoding="utf-8") == "someone else's\n"
    finding = repostate.readiness(state, ["scoped.txt"])
    assert finding["unrelatedDirty"] == ["unrelated.txt"]
    assert finding["result"] == "PASS"   # unrelated work is not a blocker by itself


def test_existing_staging_is_visible(repo):
    (repo / "staged.txt").write_text("x\n", encoding="utf-8")
    git(repo, "add", "staged.txt")
    (repo / "worktree-only.txt").write_text("y\n", encoding="utf-8")
    state = repostate.inspect(str(repo))
    assert "staged.txt" in state.staged
    assert "worktree-only.txt" in state.dirty
    assert "worktree-only.txt" not in state.staged


def test_a_leading_space_in_porcelain_does_not_eat_the_path(repo):
    """A worktree-only change prints ` M path`; the parser must not strip the blob."""
    dotted = repo / ".hidden-config.json"
    dotted.write_text("{}\n", encoding="utf-8")
    git(repo, "add", str(dotted))
    git(repo, "commit", "-qm", "add hidden")
    dotted.write_text("{ }\n", encoding="utf-8")
    state = repostate.inspect(str(repo))
    assert ".hidden-config.json" in state.dirty


# --- HEAD states ---------------------------------------------------------------


def test_detached_head_is_reported(repo):
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", head)
    state = repostate.inspect(str(repo))
    assert state.detached is True
    assert state.current_branch == ""


def test_local_commits_ahead_of_the_remote(repo_with_remote):
    (repo_with_remote / "new.txt").write_text("x\n", encoding="utf-8")
    git(repo_with_remote, "add", "new.txt")
    git(repo_with_remote, "commit", "-qm", "local work")
    state = repostate.inspect(str(repo_with_remote))
    assert state.ahead == 1
    assert state.behind == 0


# --- worktrees -----------------------------------------------------------------


def test_multiple_worktrees_are_enumerated(tmp_path, repo):
    other = tmp_path / "execution"
    git(repo, "worktree", "add", "-q", "-b", "work-item-1", str(other))

    primary = repostate.inspect(str(repo))
    assert len(primary.worktrees) == 2
    assert primary.is_primary_worktree is True

    execution = repostate.inspect(str(other))
    assert len(execution.worktrees) == 2
    assert execution.is_primary_worktree is False
    assert execution.current_branch == "work-item-1"


def test_a_dirty_primary_tree_does_not_invalidate_a_clean_execution_worktree(tmp_path, repo):
    """Item 72: report the unrelated dirty path; do not gate isolated work on it."""
    other = tmp_path / "execution"
    git(repo, "worktree", "add", "-q", "-b", "work-item-1", str(other))
    (repo / "unrelated.txt").write_text("someone else's\n", encoding="utf-8")

    primary = repostate.inspect(str(repo))
    assert "unrelated.txt" in primary.dirty

    execution = repostate.inspect(str(other))
    assert execution.dirty == []
    finding = repostate.readiness(execution, [])
    assert finding["result"] == "PASS"
    assert finding["unrelatedDirty"] == []


# --- locks ---------------------------------------------------------------------


def test_an_index_lock_is_reported_never_removed(repo):
    lock = repo / ".git" / "index.lock"
    lock.write_text("", encoding="utf-8")
    state = repostate.inspect(str(repo))
    assert state.index_lock_present is True
    finding = repostate.readiness(state, [])
    assert any("never removed automatically" in p for p in finding["problems"])
    assert lock.exists(), "inspection must never delete a lock file"


def test_policy_refuses_automatic_lock_deletion():
    from tools.governance import policy as policy_mod
    assert policy_mod.load({}).get("git.staleLock") == "report"
    assert policy_mod.load({"git": {"staleLock": "auto-delete"}}).validate()


# --- a non-repository ----------------------------------------------------------


def test_a_directory_that_is_not_a_repository(tmp_path):
    state = repostate.inspect(str(tmp_path / "nowhere-near-git"))
    assert state.is_repository is False
    finding = repostate.readiness(state, [])
    assert finding["result"] == "GAP"


# --- policy ladder -------------------------------------------------------------


@pytest.mark.parametrize("policy,stage,commit,push", [
    ("read-only", False, False, False),
    ("prepare-no-stage", False, False, False),
    ("explicit-path-stage", True, False, False),
    ("explicit-path-commit", True, True, False),
    ("push", True, True, True),
])
def test_the_git_policy_ladder(policy, stage, commit, push):
    from tools.governance import policy as policy_mod
    loaded = policy_mod.load({"git": {"policy": policy}})
    assert loaded.may_stage is stage
    assert loaded.may_commit is commit
    assert loaded.may_push is push


def test_an_unknown_git_policy_is_rejected():
    from tools.governance import policy as policy_mod
    assert policy_mod.load({"git": {"policy": "yolo"}}).validate()
