"""Read-only repository inspection (items 66-73, 97).

Everything here runs git in **read-only, lock-free** mode. Nothing in this module
mutates a repository, and nothing assumes ``main`` or ``origin``:

* the default branch is detected, with the project's ``policy.git.defaultBranch``
  taking precedence when set;
* the remote is detected, and **no remote is a supported, ordinary state**;
* worktrees are enumerated, so a dirty primary tree can be told apart from a
  clean dedicated execution worktree;
* dirty paths are split into the scoped set for the work at hand and unrelated
  paths, which are reported and left alone;
* a stale index lock is *reported*, never removed.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field

#: Read-only invocation: no optional locks, so inspection never blocks or
#: competes with a concurrent git process.
GIT_ENV = {"GIT_OPTIONAL_LOCKS": "0"}
GIT_BASE = ["git", "--no-optional-locks"]


def _run(root: str, *args: str, strip: bool = True) -> tuple[int, str]:
    """Run a read-only git command. ``strip=False`` is mandatory for
    ``status --porcelain``: its status field is two columns wide and its first
    line starts with a space when only the worktree is dirty, so stripping the
    whole blob silently eats a character off the first path."""
    try:
        completed = subprocess.run(
            GIT_BASE + list(args), cwd=root, capture_output=True, text=True,
            env=dict(os.environ, **GIT_ENV))
    except OSError as exc:
        return 127, str(exc)
    out = completed.stdout or ""
    return completed.returncode, out.strip() if strip else out


@dataclass
class RepoState:
    root: str
    is_repository: bool = False
    remotes: list[str] = field(default_factory=list)
    remote: str = ""
    remote_source: str = ""       # policy | upstream | sole | none | ambiguous
    default_branch: str = ""
    default_branch_source: str = ""   # policy | remote-head | remote-show | current | unknown
    current_branch: str = ""
    detached: bool = False
    head: str = ""
    dirty: list[str] = field(default_factory=list)
    staged: list[str] = field(default_factory=list)
    worktrees: list[str] = field(default_factory=list)
    is_primary_worktree: bool = True
    ahead: int | None = None
    behind: int | None = None
    index_lock_present: bool = False

    @property
    def has_remote(self) -> bool:
        return bool(self.remote)

    def scope(self, expected: list[str]) -> tuple[list[str], list[str]]:
        """Split the dirty set into ``(scoped, unrelated)`` against ``expected``.

        Unrelated paths are for reporting only. Nothing stashes, resets, or cleans
        them, and their presence never invalidates work happening in a separate,
        clean worktree.
        """
        wanted = {p.replace("\\", "/") for p in expected}
        scoped = [p for p in self.dirty if p in wanted]
        unrelated = [p for p in self.dirty if p not in wanted]
        return scoped, unrelated

    def as_dict(self) -> dict:
        return {
            "isRepository": self.is_repository,
            "remotes": list(self.remotes),
            "remote": self.remote,
            "remoteSource": self.remote_source,
            "defaultBranch": self.default_branch,
            "defaultBranchSource": self.default_branch_source,
            "currentBranch": self.current_branch,
            "detached": self.detached,
            "head": self.head,
            "dirty": list(self.dirty),
            "staged": list(self.staged),
            "worktrees": list(self.worktrees),
            "isPrimaryWorktree": self.is_primary_worktree,
            "ahead": self.ahead,
            "behind": self.behind,
            "indexLockPresent": self.index_lock_present,
        }


def _porcelain(root: str) -> tuple[list[str], list[str]]:
    code, out = _run(root, "status", "--porcelain", strip=False)
    if code != 0:
        return [], []
    dirty, staged = [], []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        index_status, worktree_status, path = line[0], line[1], line[3:].strip()
        if " -> " in path:                     # a rename records both sides
            path = path.split(" -> ", 1)[1]
        path = path.strip('"')
        dirty.append(path)
        if index_status not in (" ", "?"):
            staged.append(path)
    return dirty, staged


def detect_remote(root: str, policy_remote: str = "") -> tuple[str, list[str], str]:
    """``(remote, all_remotes, source)``. Never assumes ``origin``."""
    code, out = _run(root, "remote")
    remotes = [line.strip() for line in out.splitlines() if line.strip()] if code == 0 else []
    if policy_remote:
        return policy_remote, remotes, "policy"
    if not remotes:
        return "", remotes, "none"
    code, upstream = _run(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if code == 0 and "/" in upstream:
        candidate = upstream.split("/", 1)[0]
        if candidate in remotes:
            return candidate, remotes, "upstream"
    if len(remotes) == 1:
        return remotes[0], remotes, "sole"
    return "", remotes, "ambiguous"


def detect_default_branch(root: str, remote: str, policy_branch: str = "") -> tuple[str, str]:
    """``(branch, source)``. Never assumes ``main``."""
    if policy_branch:
        return policy_branch, "policy"
    if remote:
        code, out = _run(root, "symbolic-ref", "--quiet", "--short",
                         "refs/remotes/%s/HEAD" % remote)
        if code == 0 and out:
            return out.split("/", 1)[-1], "remote-head"
        code, out = _run(root, "remote", "show", remote)
        if code == 0:
            for line in out.splitlines():
                if "HEAD branch:" in line:
                    return line.split("HEAD branch:", 1)[1].strip(), "remote-show"
    code, out = _run(root, "branch", "--show-current")
    if code == 0 and out:
        return out, "current"
    return "", "unknown"


def inspect(root: str, git_policy: dict | None = None) -> RepoState:
    """Inspect ``root``. Read-only; safe to run at any time, in any state."""
    root = os.path.abspath(root)
    policy = git_policy or {}
    state = RepoState(root=root)

    code, out = _run(root, "rev-parse", "--is-inside-work-tree")
    state.is_repository = code == 0 and out == "true"
    if not state.is_repository:
        return state

    state.remote, state.remotes, state.remote_source = detect_remote(
        root, str(policy.get("remote") or ""))
    state.default_branch, state.default_branch_source = detect_default_branch(
        root, state.remote, str(policy.get("defaultBranch") or ""))

    code, out = _run(root, "branch", "--show-current")
    state.current_branch = out if code == 0 else ""
    state.detached = state.is_repository and not state.current_branch

    code, out = _run(root, "rev-parse", "HEAD")
    state.head = out if code == 0 else ""

    state.dirty, state.staged = _porcelain(root)

    code, out = _run(root, "worktree", "list", "--porcelain")
    if code == 0:
        state.worktrees = [line.split(" ", 1)[1] for line in out.splitlines()
                           if line.startswith("worktree ")]
    if state.worktrees:
        state.is_primary_worktree = os.path.realpath(state.worktrees[0]) == os.path.realpath(root)

    if state.remote and state.current_branch:
        code, out = _run(root, "rev-list", "--left-right", "--count",
                         "%s...%s/%s" % (state.current_branch, state.remote,
                                         state.current_branch))
        if code == 0 and out:
            parts = out.split()
            if len(parts) == 2 and all(p.isdigit() for p in parts):
                state.ahead, state.behind = int(parts[0]), int(parts[1])

    code, out = _run(root, "rev-parse", "--git-dir")
    git_dir = os.path.join(root, out) if code == 0 and not os.path.isabs(out) else out
    state.index_lock_present = bool(git_dir) and os.path.exists(
        os.path.join(git_dir, "index.lock"))

    return state


def readiness(state: RepoState, expected: list[str], git_policy: dict | None = None) -> dict:
    """The repository-readiness finding the ceremonies report (item 39)."""
    policy = git_policy or {}
    scoped, unrelated = state.scope(expected)
    problems = []
    if not state.is_repository:
        problems.append("not a git repository")
    if state.index_lock_present:
        problems.append("an index lock is present — check for a running git process; "
                        "this is reported, never removed automatically")
    if policy.get("requireRemote") and not state.has_remote:
        problems.append("policy.git.requireRemote is set but this repository has no remote")
    if state.remote_source == "ambiguous":
        problems.append("several remotes exist and none is the upstream; set "
                        "policy.git.remote")
    if state.default_branch_source == "unknown":
        problems.append("the default branch could not be detected; set "
                        "policy.git.defaultBranch")
    return {
        "result": "PASS" if not problems else "GAP",
        "problems": problems,
        "scopedDirty": scoped,
        "unrelatedDirty": unrelated,
        "detached": state.detached,
        "hasRemote": state.has_remote,
        "worktrees": len(state.worktrees),
        "isPrimaryWorktree": state.is_primary_worktree,
        "ahead": state.ahead,
        "behind": state.behind,
    }
