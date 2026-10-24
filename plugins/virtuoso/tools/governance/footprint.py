"""Disk footprint: find, size and classify what dispatches leave behind (VIR-054).

Read-only by default. :func:`audit` lists every candidate and writes nothing.
:func:`remove` and :func:`extract` preview unless ``apply=True``.

Candidates come from exactly three one-level places (``MAX_DEPTH``) and the
repository's own worktree list; nothing scans a drive recursively:

``worktree``  every worktree ``git worktree list --porcelain`` names, the primary excluded
``clone``     a git work tree one level under the drive root or the project's parent
              folder whose root commit equals this repository's
``scratch``   a child of the registered ``temp`` role
``basetemp``  a folder one level under the drive root, ``%TEMP%`` or the project's
              parent folder, most of whose children are pytest per-test folders

Classes, first match wins: ``in-flight``, ``evidence``, ``unique``, ``redundant``,
``regenerable``. A folder the audit cannot read is ``unreadable``. Only
``redundant`` and ``regenerable`` can be removed; a git tree that matches neither
``unique`` nor ``redundant`` is kept as ``unique``.
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

from . import textio
from .errors import GovernanceError

MAX_DEPTH = 1
#: pytest's per-test folder names (``test_name0``, ``test_name_param_12``).
BASETEMP_CHILD = re.compile(r"^test_.+\d+$")
BASETEMP_MIN_MATCHES = 2
#: Any other folder ``tmp_path_factory.mktemp`` numbers (``virtuoso-home0``).
PYTEST_NUMBERED = re.compile(r"^[A-Za-z][\w.-]*\d+$")
FILE_ATTRIBUTE_REPARSE_POINT = 0x400

IN_FLIGHT, EVIDENCE, UNIQUE, REDUNDANT, REGENERABLE, UNREADABLE = (
    "in-flight", "evidence", "unique", "redundant", "regenerable", "unreadable")
REMOVABLE = (REDUNDANT, REGENERABLE)

#: What a folder may hold and still be regenerable.
REGENERABLE_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
                     "node_modules", "build", "dist", ".tox", ".nox"}
EXTRACT_FOLDER = "footprint-extract"

#: No optional locks, no lazy fetch from a partial clone's promisor, no credential prompt.
GIT_ENV = {"GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}


def _git(cwd: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "--no-optional-locks", *args], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=dict(os.environ, **GIT_ENV))


def _out(cwd: str, *args: str) -> str | None:
    try:
        proc = _git(cwd, *args)
    except OSError:
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def _norm(path: str) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def _inside(path: str, parent: str | None) -> bool:
    if not parent:
        return False
    path, parent = _norm(path), _norm(parent)
    return path == parent or path.startswith(parent.rstrip(os.sep) + os.sep)


def is_link(path: str) -> bool:
    """A symlink, or a Windows junction or other reparse point. Never follows it."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT)


def _size(path: str) -> tuple[int, bool]:
    """``(bytes, complete)``: lstat sizes, links counted as themselves, never followed."""
    total, complete = 0, True
    try:
        st = os.lstat(path)
    except OSError:
        return 0, False
    if not stat.S_ISDIR(st.st_mode) or is_link(path):
        return st.st_size, True
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        est = entry.stat(follow_symlinks=False)
                    except OSError:
                        complete = False
                        continue
                    if entry.is_dir(follow_symlinks=False) and not is_link(entry.path):
                        stack.append(entry.path)
                    else:
                        total += est.st_size
        except OSError:
            complete = False
    return total, complete


def _children(path: str) -> list[str] | None:
    try:
        return sorted(os.listdir(path))
    except OSError:
        return None


def _is_git_tree(path: str) -> bool:
    return os.path.exists(os.path.join(path, ".git")) and not is_link(path)


# --- context ----------------------------------------------------------------------------


@dataclass
class Context:
    """Everything the audit reads, injectable so a test never touches the real drive."""
    root: str                                   # the project (registry) root
    primary: str = ""                           # the primary worktree of root's repository
    default_branch: str = ""
    drive_root: str | None = None
    temp_dir: str | None = None
    parent_dir: str | None = None
    temp_role: str | None = None
    evidence_dirs: list[str] = field(default_factory=list)
    epics_dir: str | None = None
    #: Ids of register items that are not terminal; None when the register was unreadable.
    live_items: set[str] | None = None
    notes: list[str] = field(default_factory=list)

    def places(self) -> dict:
        return {"driveRoot": self.drive_root, "temp": self.temp_dir,
                "parent": self.parent_dir, "tempRole": self.temp_role}


def default_branch(primary: str, policy_branch: str = "") -> str:
    """The default branch, offline: policy, then the remote's HEAD, then the primary
    tree's branch. Never assumes ``main`` and never contacts a remote."""
    if policy_branch:
        return policy_branch
    for remote in (_out(primary, "remote") or "").split():
        head = _out(primary, "symbolic-ref", "--quiet", "--short", "refs/remotes/%s/HEAD" % remote)
        if head:
            return head.split("/", 1)[-1]
    return _out(primary, "branch", "--show-current") or ""


def make_context(root: str, *, temp_role: str | None = None, evidence_dirs=(),
                 epics_dir: str | None = None, live_items: set[str] | None = None,
                 policy_branch: str = "", drive_root: str | None = "",
                 temp_dir: str | None = "", parent_dir: str | None = "") -> Context:
    """Build a context for ``root``. An empty string for a place means "this machine's";
    ``None`` leaves that place out."""
    root = os.path.abspath(root)
    primary = root
    listing = _out(root, "worktree", "list", "--porcelain")
    if listing:
        first = listing.splitlines()[0]
        if first.startswith("worktree "):
            primary = os.path.abspath(first.split(" ", 1)[1])
    if drive_root == "":
        drive_root = os.path.splitdrive(primary)[0] + os.sep if os.name == "nt" else os.sep
    if temp_dir == "":
        temp_dir = tempfile.gettempdir()
    if parent_dir == "":
        parent_dir = os.path.dirname(primary)
    return Context(root=root, primary=primary,
                   default_branch=default_branch(primary, policy_branch),
                   drive_root=drive_root, temp_dir=temp_dir, parent_dir=parent_dir,
                   temp_role=temp_role, evidence_dirs=[d for d in evidence_dirs if d],
                   epics_dir=epics_dir, live_items=live_items)


# --- git facts --------------------------------------------------------------------------


def _worktrees(ctx: Context) -> list[dict]:
    listing = _out(ctx.primary, "worktree", "list", "--porcelain") or ""
    trees, current = [], None
    for line in listing.splitlines():
        if line.startswith("worktree "):
            current = {"path": os.path.abspath(line.split(" ", 1)[1]), "branch": "", "head": ""}
            trees.append(current)
        elif current is not None and line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1].removeprefix("refs/heads/")
        elif current is not None and line.startswith("HEAD "):
            current["head"] = line.split(" ", 1)[1]
    return trees[1:]                              # the primary is never a candidate


def _root_commits(path: str) -> set[str]:
    return set((_out(path, "rev-list", "--max-parents=0", "HEAD") or "").split())


def _primary_tips(ctx: Context, exclude_branch: str = "") -> list[str]:
    """Commit ids at every branch and remote ref of the primary, minus one branch."""
    listing = _out(ctx.primary, "for-each-ref", "--format=%(objectname) %(refname)",
                   "refs/heads", "refs/remotes") or ""
    skip = "refs/heads/" + exclude_branch if exclude_branch else None
    return sorted({line.split(" ", 1)[0] for line in listing.splitlines()
                   if line and line.split(" ", 1)[1] != skip})


def _primary_contains(ctx: Context, sha: str, exclude_branch: str = "") -> bool:
    if _out(ctx.primary, "cat-file", "-e", sha + "^{commit}") is None:
        return False
    refs = (_out(ctx.primary, "for-each-ref", "--contains", sha, "--format=%(refname)",
                 "refs/heads", "refs/remotes") or "").split()
    skip = "refs/heads/" + exclude_branch if exclude_branch else None
    return any(ref != skip for ref in refs)


def unique_commits(ctx: Context, tree: str, own_branch: str = "", clone: bool = False) -> list[str]:
    """Commits on ``tree``'s HEAD (and, for a clone, its branches) that no branch or
    remote ref of the primary repository contains, oldest first. A worktree's own
    branch does not count as containing its work."""
    heads = ["HEAD"] + (["--branches"] if clone else [])
    tips = _exclusion_tips(ctx, tree, own_branch, clone)
    listing = _out(tree, "rev-list", "--topo-order", "--reverse", *heads, "--not", *tips) \
        if tips else _out(tree, "rev-list", "--topo-order", "--reverse", *heads)
    shas = (listing or "").split()
    if clone:                                     # the primary may hold them under a tip the clone lacks
        shas = [s for s in shas if not _primary_contains(ctx, s)]
    return shas


def _exclusion_tips(ctx: Context, tree: str, own_branch: str, clone: bool) -> list[str]:
    """The primary's ref tips that ``tree`` knows: what its unique work is measured against."""
    tips = _primary_tips(ctx, own_branch)
    if clone and tips:                            # a clone may lack some of the primary's tips
        known = _git_batch_check(tree, tips)
        tips = [t for t in tips if t in known]
    return tips


def _git_batch_check(tree: str, shas: list[str]) -> set[str]:
    try:
        proc = subprocess.run(["git", "--no-optional-locks", "cat-file", "--batch-check"],
                              cwd=tree, input="\n".join(shas) + "\n", capture_output=True,
                              text=True, encoding="utf-8", env=dict(os.environ, **GIT_ENV))
    except OSError:
        return set()
    return {line.split()[0] for line in proc.stdout.splitlines()
            if line and not line.endswith("missing")}


def _dirty(tree: str) -> list[str] | None:
    try:
        proc = _git(tree, "status", "--porcelain")
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return [line for line in proc.stdout.splitlines() if line.strip()]


def _merged(ctx: Context, sha: str) -> bool:
    if not ctx.default_branch or not sha:
        return False
    for ref in ("refs/heads/" + ctx.default_branch, ctx.default_branch):
        if _out(ctx.primary, "rev-parse", "--verify", "--quiet", ref) is not None:
            return _git(ctx.primary, "merge-base", "--is-ancestor", sha, ref).returncode == 0
    return False


# --- candidates -------------------------------------------------------------------------


@dataclass
class Candidate:
    path: str
    kind: str
    size: int = 0
    cls: str = ""
    reason: str = ""
    branch: str = ""
    head: str = ""
    unique: list[str] = field(default_factory=list)
    next: str = ""

    def as_dict(self) -> dict:
        data = {"path": self.path, "kind": self.kind, "size": self.size,
                "class": self.cls, "reason": self.reason}
        if self.branch:
            data["branch"] = self.branch
        if self.head:
            data["head"] = self.head
        if self.unique:
            data["uniqueCommits"] = list(self.unique)
        if self.next:
            data["next"] = self.next
        return data


def _looks_like_basetemp(path: str) -> bool:
    """At least ``BASETEMP_MIN_MATCHES`` per-test folders, and pytest's own children
    (per-test folders, its ``<name>current`` links, numbered ``mktemp`` folders such as
    a conftest's ``home0``) are more than half. Owner decision, VIR-054: a literal
    per-test majority missed every basetemp of this repository's own suite."""
    names = _children(path)
    if not names:
        return False
    hits = sum(1 for n in names if BASETEMP_CHILD.match(n))
    pytest_own = sum(1 for n in names if BASETEMP_CHILD.match(n) or PYTEST_NUMBERED.match(n)
                     or (n.endswith("current") and is_link(os.path.join(path, n))))
    return hits >= BASETEMP_MIN_MATCHES and pytest_own * 2 > len(names)


def _one_level(place: str | None, unread: list[str]) -> list[str]:
    if not place:
        return []
    names = _children(place)
    if names is None:
        unread.append(place)
        return []
    return [os.path.join(place, n) for n in names
            if os.path.isdir(os.path.join(place, n)) and not is_link(os.path.join(place, n))]


def discover(ctx: Context) -> list[Candidate]:
    """Every candidate, deduplicated by real path (a worktree is never also a clone).
    A scan place or folder it cannot list is named in ``ctx.notes``; it never fails."""
    found: dict[str, Candidate] = {}
    skip = {_norm(ctx.primary), _norm(ctx.root)}
    unread: list[str] = []

    def add(path: str, kind: str, **extra) -> None:
        key = _norm(path)
        if key in skip or key in found:
            return
        found[key] = Candidate(path=os.path.abspath(path), kind=kind, **extra)

    for tree in _worktrees(ctx):
        add(tree["path"], "worktree", branch=tree["branch"], head=tree["head"])
    roots = _root_commits(ctx.primary)
    for place in (ctx.drive_root, ctx.parent_dir):
        for path in _one_level(place, unread):
            if _is_git_tree(path) and roots and _root_commits(path) & roots:
                add(path, "clone", head=_out(path, "rev-parse", "HEAD") or "",
                    branch=_out(path, "branch", "--show-current") or "")
    if ctx.temp_role and os.path.isdir(ctx.temp_role):
        names = _children(ctx.temp_role)
        if names is None:
            unread.append(ctx.temp_role)
        for name in names or []:
            add(os.path.join(ctx.temp_role, name), "scratch")
    for place in (ctx.drive_root, ctx.temp_dir, ctx.parent_dir):
        for path in _one_level(place, []):        # the clone pass named unreadable places
            if _children(path) is None:
                unread.append(path)
            elif _looks_like_basetemp(path):
                add(path, "basetemp")
    unread = sorted(set(unread))
    if unread:
        ctx.notes.append("%d folder(s) could not be read and were not checked: %s%s" % (
            len(unread), ", ".join(unread[:5]), ", ..." if len(unread) > 5 else ""))
    return list(found.values())


def _nested_git(path: str) -> str | None:
    """The first ``.git`` below ``path``, links never followed."""
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if entry.name == ".git":
                        return current
                    if entry.is_dir(follow_symlinks=False) and not is_link(entry.path):
                        stack.append(entry.path)
        except OSError:
            continue
    return None


def _only_regenerable(path: str) -> bool:
    names = _children(path)
    if not names:
        return False
    for name in names:
        full = os.path.join(path, name)
        if name in REGENERABLE_NAMES:
            continue
        if os.path.isdir(full) and os.path.isfile(os.path.join(full, "pyvenv.cfg")):
            continue
        return False
    return True


def _item_for_branch(ctx: Context, branch: str) -> str | None:
    for item in sorted(ctx.live_items or ()):
        if branch == item or branch.startswith(item + "-"):
            return item
    return None


def classify(ctx: Context, cand: Candidate) -> Candidate:
    """Set ``cls`` and ``reason``. First match wins; reads only."""
    path = cand.path
    if not os.path.lexists(path):
        cand.cls, cand.reason = UNREADABLE, "the folder is missing"
        if cand.kind == "worktree":
            cand.reason += "; `git worktree prune` clears the registration"
        return cand
    git_tree = cand.kind in ("worktree", "clone") or (os.path.isdir(path) and _is_git_tree(path))

    # in-flight
    if cand.kind == "worktree" and cand.branch and cand.branch != ctx.default_branch:
        if ctx.live_items is None:
            cand.cls = IN_FLIGHT
            cand.reason = ("the work register could not be read, so branch %s may belong "
                           "to a live item" % cand.branch)
            return cand
        item = _item_for_branch(ctx, cand.branch)
        if item:
            cand.cls, cand.reason = IN_FLIGHT, "branch %s belongs to %s, which is not terminal" % (
                cand.branch, item)
            return cand

    # evidence
    for directory in ctx.evidence_dirs:
        if _inside(path, directory):
            cand.cls, cand.reason = EVIDENCE, "inside the registered evidence folder %s" % directory
            return cand
    if ctx.epics_dir and _inside(path, ctx.epics_dir):
        cand.cls, cand.reason = EVIDENCE, "inside the registered epics folder"
        return cand
    if os.path.isfile(os.path.join(path, "charter.md")):
        cand.cls, cand.reason = EVIDENCE, "an epic packet (holds charter.md)"
        return cand
    if cand.kind == "scratch" and os.path.basename(path) == EXTRACT_FOLDER:
        cand.cls, cand.reason = EVIDENCE, "patches extracted by the footprint tool"
        return cand

    # unique and redundant: git trees
    if git_tree:
        dirty = _dirty(path)
        if dirty is None:
            cand.cls, cand.reason = UNREADABLE, "git could not read the tree"
            return cand
        if dirty:
            cand.cls, cand.reason = UNIQUE, "%d uncommitted path(s)" % len(dirty)
            return cand
        stashes = (_out(path, "stash", "list") or "").splitlines() if cand.kind == "clone" else []
        if stashes:                               # a worktree shares the primary's stash
            cand.cls, cand.reason = UNIQUE, "%d stash entr(ies)" % len(stashes)
            return cand
        head =_out(path, "rev-parse", "HEAD") or ""
        cand.head = cand.head or head
        own = cand.branch if cand.kind == "worktree" else ""
        cand.unique = unique_commits(ctx, path, own, clone=cand.kind != "worktree")
        if cand.unique:
            cand.cls = UNIQUE
            cand.reason = "%d commit(s) that no branch or remote ref of the primary contains" % (
                len(cand.unique))
            return cand
        if _merged(ctx, head):
            cand.cls, cand.reason = REDUNDANT, "clean, and %s contains its HEAD" % ctx.default_branch
            return cand
        cand.cls = UNIQUE
        cand.reason = "clean, but %s does not contain its HEAD" % (ctx.default_branch or
                                                                   "the default branch")
        return cand

    if cand.kind in ("scratch", "basetemp") and os.path.isdir(path):
        # A numbered folder beside the per-test ones can be someone's repository; the
        # repositories tests build inside their own per-test folders are the suite's.
        nested = _nested_git(path) if cand.kind == "scratch" else next(
            (found for name in _children(path) or []
             if not BASETEMP_CHILD.match(name) and not is_link(os.path.join(path, name))
             and os.path.isdir(os.path.join(path, name))
             for found in [_nested_git(os.path.join(path, name))] if found), None)
        if nested:
            cand.cls, cand.reason = UNIQUE, "holds a git tree at %s" % nested
            return cand
    if cand.kind == "scratch" and os.path.isdir(path):
        tracked = _out(ctx.root, "ls-files", "--", path)
        if tracked:
            cand.cls, cand.reason = UNIQUE, "tracked in the repository; remove it with a commit"
            return cand

    # regenerable
    if cand.kind == "basetemp":
        cand.cls, cand.reason = REGENERABLE, "a pytest basetemp (per-test folders)"
    elif cand.kind == "scratch":
        cand.cls, cand.reason = REGENERABLE, "scratch in the temp role with no git tree"
    elif os.path.isdir(path) and _only_regenerable(path):
        cand.cls, cand.reason = REGENERABLE, "holds only venvs, caches or build output"
    else:
        cand.cls, cand.reason = UNIQUE, "matches no removable class"
    return cand


def _owner_command(path: str) -> str:
    quoted = path.replace("'", "''")
    if os.name == "nt":
        return "Remove-Item -LiteralPath '%s' -Recurse -Force" % quoted
    return "rm -rf -- '%s'" % path.replace("'", "'\\''")


def _next_step(ctx: Context, cand: Candidate) -> str:
    extract = "virtuoso_registry --root . footprint --extract \"%s\" --apply" % cand.path
    if cand.cls == UNIQUE and (cand.kind in ("worktree", "clone") or _is_git_tree(cand.path)):
        return "owner: extract first (%s), then decide" % extract
    if cand.cls == EVIDENCE:
        first = ("%s; then " % extract) if _is_git_tree(cand.path) else ""
        return "owner only: %s%s" % (first, _owner_command(cand.path))
    if cand.cls in REMOVABLE:
        return "virtuoso_registry --root . footprint --remove \"%s\" --apply" % cand.path
    return ""


def free_bytes(path: str) -> int:
    probe = path
    while probe and not os.path.exists(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    return shutil.disk_usage(probe or ".").free


# --- dispatch scope ---------------------------------------------------------------------


def _created(path: str) -> float:
    st = os.lstat(path)
    birth = getattr(st, "st_birthtime", None)
    if birth:
        return birth
    return st.st_ctime if os.name == "nt" else st.st_mtime


def _in_dispatch(ctx: Context, cand: Candidate, item: str, since: float | None) -> bool:
    if cand.kind == "worktree":
        return cand.branch == item or cand.branch.startswith(item + "-")
    if cand.kind in ("basetemp", "scratch") and since is not None:
        try:
            return _created(cand.path) >= since
        except OSError:
            return False
    return False


def _branch_base_time(ctx: Context, item: str) -> float | None:
    """When the run's branch was made: its reflog's first entry, which survives the
    merge (after it, the merge base is the branch tip); else the merge base."""
    if _out(ctx.primary, "rev-parse", "--verify", "--quiet", "refs/heads/" + item) is None:
        return None
    reflog = (_out(ctx.primary, "log", "-g", "--format=%ct", "refs/heads/" + item) or "").split()
    if reflog:
        return float(reflog[-1])
    base = _out(ctx.primary, "merge-base", ctx.default_branch or "HEAD", item)
    stamp = _out(ctx.primary, "show", "-s", "--format=%ct", base) if base else None
    return float(stamp) if stamp else None


# --- the operations ---------------------------------------------------------------------


def audit(ctx: Context, dispatch: str | None = None) -> dict:
    """Every candidate with its kind, size, class and reason, and the free space.
    Writes nothing."""
    candidates = discover(ctx)
    notes = list(ctx.notes)
    if dispatch:
        since = _branch_base_time(ctx, dispatch)
        if since is None:
            notes.append("branch %s not found: basetemp and scratch folders are not "
                         "time-scoped, so none are listed" % dispatch)
        candidates = [c for c in candidates if _in_dispatch(ctx, c, dispatch, since)]
    for cand in candidates:
        classify(ctx, cand)
        cand.size, complete = _size(cand.path)
        if not complete and cand.cls in REMOVABLE:
            cand.cls, cand.reason = UNREADABLE, "part of the folder could not be read"
        cand.next = _next_step(ctx, cand)
    order = {IN_FLIGHT: 0, EVIDENCE: 1, UNIQUE: 2, REDUNDANT: 3, REGENERABLE: 4, UNREADABLE: 5}
    candidates.sort(key=lambda c: (order.get(c.cls, 9), c.path.lower()))
    disk = shutil.disk_usage(ctx.primary)
    return {"candidates": [c.as_dict() for c in candidates],
            "freeBytes": disk.free, "totalBytes": disk.total,
            "places": ctx.places(), "defaultBranch": ctx.default_branch,
            "dispatch": dispatch or None, "notes": notes,
            "liveItemsRead": ctx.live_items is not None}


def _find(ctx: Context, path: str) -> Candidate:
    key = _norm(path)
    for cand in discover(ctx):
        if _norm(cand.path) == key:
            return classify(ctx, cand)
    raise GovernanceError("footprint: %s is not a footprint candidate (a worktree, a clone, "
                          "a temp-role child or a pytest basetemp); nothing removed" % path)


def _unlink_links(path: str, keep: frozenset = frozenset()) -> int:
    """Remove every link under ``path`` without following it, except the normalized
    paths in ``keep`` (a worktree's tracked symlinks, which git removes as links).
    Returns how many."""
    removed = 0
    if is_link(path):
        _drop_link(path)
        return 1
    if not os.path.isdir(path):
        return 0
    stack = [path]
    while stack:
        current = stack.pop()
        with os.scandir(current) as entries:
            entries = list(entries)
        for entry in entries:
            if is_link(entry.path):
                if os.path.normcase(os.path.abspath(entry.path)) in keep:
                    continue
                _drop_link(entry.path)
                removed += 1
            elif entry.is_dir(follow_symlinks=False):
                stack.append(entry.path)
    return removed


def _tracked_links(tree: str) -> frozenset:
    """A worktree's tracked symlinks (mode 120000), as normalized absolute paths."""
    listing = _out(tree, "ls-files", "-s") or ""
    return frozenset(os.path.normcase(os.path.abspath(os.path.join(tree, line.split("\t", 1)[1])))
                     for line in listing.splitlines()
                     if line.startswith("120000 ") and "\t" in line)


def _drop_link(path: str) -> None:
    """Unlink a symlink or junction itself; its target is never touched."""
    try:
        os.unlink(path)
    except (IsADirectoryError, PermissionError, OSError):
        os.rmdir(path)                    # a directory symlink or junction on Windows


def _writable_retry(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _rmtree(path: str) -> None:
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_writable_retry)
    else:                                 # pragma: no cover - older interpreters
        shutil.rmtree(path, onerror=_writable_retry)


def remove(ctx: Context, path: str, apply: bool = False) -> dict:
    """Preview, or with ``apply`` perform, the removal of one candidate. Refuses every
    class but ``redundant`` and ``regenerable``, whatever the flags."""
    cand = _find(ctx, path)
    if cand.cls not in REMOVABLE:
        raise GovernanceError("footprint: refused to remove %s: it is %s (%s)%s" % (
            cand.path, cand.cls, cand.reason,
            "; %s" % _next_step(ctx, cand) if _next_step(ctx, cand) else ""))
    method = ("untracked links removed first, then git worktree remove and git worktree prune"
              if cand.kind == "worktree" else "links removed first, then a recursive delete")
    before = free_bytes(cand.path)
    result = {"path": cand.path, "kind": cand.kind, "class": cand.cls,
              "reason": cand.reason, "method": method, "applied": False,
              "freeBefore": before}
    if not apply:
        result["note"] = "preview only: add --apply to remove"
        return result
    try:
        if cand.kind == "worktree":
            # An ignored junction is invisible to `status` and git's delete would follow
            # it; tracked symlinks stay, so the tree stays clean for `worktree remove`.
            result["linksRemoved"] = _unlink_links(cand.path, _tracked_links(cand.path))
            for args in (("worktree", "remove", cand.path), ("worktree", "prune")):
                proc = _git(ctx.primary, *args)
                if proc.returncode != 0:
                    raise GovernanceError("footprint: git %s refused: %s" % (
                        " ".join(args[:2]), (proc.stderr or proc.stdout).strip()))
        else:
            result["linksRemoved"] = _unlink_links(cand.path)
            if os.path.lexists(cand.path):
                if os.path.isdir(cand.path) and not is_link(cand.path):
                    _rmtree(cand.path)
                else:
                    os.unlink(cand.path)
    except OSError as exc:
        raise GovernanceError("footprint: removing %s stopped part-way: %s" % (
            cand.path, exc)) from exc
    result["applied"] = True
    result["freeAfter"] = free_bytes(cand.path)
    return result


def _git_bytes(cwd: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "--no-optional-locks", *args], cwd=cwd, capture_output=True,
                          env=dict(os.environ, **GIT_ENV))


def extract(ctx: Context, path: str, apply: bool = False) -> dict:
    """Save a git tree's unique work under ``<temp role>/footprint-extract/<name>-<head>/``:
    ``unique.bundle`` (every unique commit, merges included, restorable with
    ``git fetch``), one ``git format-patch`` file per non-merge unique commit,
    ``uncommitted.diff`` for tracked changes and ``untracked.diff`` holding the
    untracked files' contents."""
    if not ctx.temp_role:
        raise GovernanceError("footprint: --extract writes under the `temp` role, which is "
                              "not registered")
    cand = _find(ctx, path)
    if not os.path.isdir(cand.path) or not _is_git_tree(cand.path):
        raise GovernanceError("footprint: %s is not a git tree; nothing to extract" % cand.path)
    own = cand.branch if cand.kind == "worktree" else ""
    clone = cand.kind != "worktree"
    shas = unique_commits(ctx, cand.path, own, clone=clone)
    merges = set((_out(cand.path, "rev-list", "--merges", "--no-walk", *shas) or "").split()) \
        if shas else set()
    dirty = _dirty(cand.path) or []
    untracked = [p for p in (_out(cand.path, "ls-files", "-o", "--exclude-standard", "-z") or "")
                 .split("\0") if p]
    head = _out(cand.path, "rev-parse", "HEAD") or ""
    target = os.path.join(ctx.temp_role, EXTRACT_FOLDER, "%s-%s" % (
        os.path.basename(cand.path.rstrip("\\/")), head[:10] or "nohead"))
    result = {"path": cand.path, "target": target, "commits": shas,
              "merges": sorted(merges), "uncommitted": len(dirty),
              "untracked": len(untracked), "applied": False, "files": []}
    if not apply:
        result["note"] = "preview only: add --apply to write the patches"
        return result
    note = os.path.join(target, "EXTRACTED.txt")     # creates the folder, and says from where
    textio.write_if_changed(note, "from: %s\nhead: %s\ncommits: %d (merges: %d)\n"
                            "uncommitted paths: %d\nuntracked files: %d\n" % (
                                cand.path, head, len(shas), len(merges), len(dirty),
                                len(untracked)))
    result["files"].append(note)
    if shas:
        bundle = os.path.join(target, "unique.bundle")
        heads = ["HEAD"] + (["--branches"] if clone else [])
        tips = _exclusion_tips(ctx, cand.path, own, clone)
        proc = _git(cand.path, "bundle", "create", bundle, *heads,
                    *(["--not", *tips] if tips else []))
        if proc.returncode != 0:
            raise GovernanceError("footprint: git bundle create failed: %s" % proc.stderr.strip())
        result["files"].append(bundle)
    number = 0
    for sha in shas:
        if sha in merges:                         # format-patch has no form for a merge
            continue
        number += 1
        proc = _git(cand.path, "format-patch", "-1", sha, "-o", target,
                    "--start-number", str(number))
        if proc.returncode != 0:
            raise GovernanceError("footprint: git format-patch %s failed: %s" % (
                sha, proc.stderr.strip()))
        result["files"].extend(line.strip() for line in proc.stdout.splitlines() if line.strip())
    if any(not line.startswith("??") for line in dirty):
        out = os.path.join(target, "uncommitted.diff")
        with open(out, "wb") as handle:              # the patch's own bytes, line endings kept
            handle.write(_git_bytes(cand.path, "diff", "HEAD", "--binary").stdout)
        result["files"].append(out)
    if untracked:
        out = os.path.join(target, "untracked.diff")
        with open(out, "wb") as handle:
            for rel in untracked:                 # exit 1 means "differs", which is the point
                handle.write(_git_bytes(cand.path, "diff", "--no-index", "--binary", "--",
                                        "/dev/null", rel).stdout)
        result["files"].append(out)
    result["applied"] = True
    return result
