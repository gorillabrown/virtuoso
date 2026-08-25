"""Read-only discovery of an established project's governance documents.

Used by ``adopt`` and ``create`` only — never by ``check`` (item 2), and never
for a role that is already registered (item 20: a registered target that is
temporarily absent is *reported*, not re-pointed at a lookalike).

Discovery reads; it never writes, moves, or seeds. Every candidate it returns
carries the reason it was chosen so adoption can tell the user exactly what it
registered and why.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .safepath import ARCHIVE_SEGMENTS

#: Documentation-root directory names commonly used by established projects.
DOC_ROOT_CANDIDATES = ("Project Documentation", "2. Project Documentation", "docs", "doc")

#: Structural markers that distinguish a live roadmap from an arbitrary file
#: whose name merely contains "roadmap".
_ROADMAP_MARKERS = (
    b"Completed Work Summary",
    b"Active & Remaining",
    b"Finish Line",
    b"roadmap_doc:",
    b"finish_line:",
)

_BACKUP_TOKENS = ("backup", "snapshot", "copy", "bak", "old", "previous")
_BACKUP_RE = re.compile(r"(?:^|[ _\-.()])(?:" + "|".join(_BACKUP_TOKENS) + r")(?:[ _\-.()]|$)")

#: A freshly seeded, never-edited roadmap carries this line verbatim.
SEED_SENTINEL = "**Last updated:** (seeded by virtuoso create)"


@dataclass
class Candidate:
    path: str            # absolute
    relative: str        # project-relative, posix
    reason: str


def _rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace("\\", "/")


def _is_archived(root: str, path: str) -> bool:
    rel = _rel(root, path).lower()
    return any(seg in ARCHIVE_SEGMENTS for seg in rel.split("/")[:-1])


def _has_backup_name(path: str) -> bool:
    stem = os.path.basename(path).lower().rsplit(".", 1)[0]
    return bool(_BACKUP_RE.search(stem))


def _looks_like_seed(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            return SEED_SENTINEL in handle.read(2048)
    except OSError:
        return False


def _score(path: str) -> tuple:
    try:
        with open(path, "rb") as handle:
            head = handle.read(16384)
    except OSError:
        head = b""
    structural = sum(1 for marker in _ROADMAP_MARKERS if marker in head)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = 0
    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0
    return (
        0 if _looks_like_seed(path) else 1,
        0 if _has_backup_name(path) else 1,
        structural,
        mtime,
        size,
    )


def doc_root(root: str) -> str | None:
    for name in DOC_ROOT_CANDIDATES:
        path = os.path.join(root, name)
        if os.path.isdir(path):
            return path
    return None


def _files(base: str, *, recursive: bool, predicate) -> list[str]:
    if not base or not os.path.isdir(base):
        return []
    found = []
    if recursive:
        for dirpath, dirs, names in os.walk(base):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")]
            for name in names:
                if predicate(name):
                    found.append(os.path.join(dirpath, name))
    else:
        for name in os.listdir(base):
            full = os.path.join(base, name)
            if os.path.isfile(full) and predicate(name):
                found.append(full)
    return found


def find_roadmap(root: str) -> Candidate | None:
    """The project's live roadmap, wherever it lives. Archived copies are excluded;
    seeds and backup snapshots sink below any real roadmap."""
    def is_roadmap(name: str) -> bool:
        low = name.lower()
        return low.endswith((".md", ".markdown")) and "roadmap" in low

    candidates: list[str] = []
    established = doc_root(root)
    if established:
        candidates += _files(established, recursive=True, predicate=is_roadmap)
    for extra in ("docs", os.path.join("docs", "governance")):
        candidates += _files(os.path.join(root, extra), recursive=True, predicate=is_roadmap)
    candidates += _files(root, recursive=False, predicate=is_roadmap)

    seen, live = set(), []
    for path in candidates:
        absolute = os.path.abspath(path)
        if absolute in seen:
            continue
        seen.add(absolute)
        if not _is_archived(root, absolute):
            live.append(absolute)
    if not live:
        return None
    live.sort(key=_score, reverse=True)
    best = live[0]
    reason = "highest-scoring live roadmap of %d candidate(s)" % len(live)
    return Candidate(path=best, relative=_rel(root, best), reason=reason)


def find_work_register(root: str) -> Candidate | None:
    """A local work register: a CSV whose name suggests a catalog/queue/backlog."""
    def is_register(name: str) -> bool:
        low = name.lower()
        return low.endswith(".csv") and any(
            token in low for token in ("catalog", "catalogue", "queue", "backlog", "register",
                                       "sprints", "work-items", "workitems")
        )

    base = doc_root(root) or root
    candidates = [p for p in _files(base, recursive=True, predicate=is_register)
                  if not _is_archived(root, p)]
    candidates += [p for p in _files(root, recursive=False, predicate=is_register)
                   if not _is_archived(root, p)]
    if not candidates:
        return None
    candidates.sort(key=_score, reverse=True)
    best = os.path.abspath(candidates[0])
    return Candidate(path=best, relative=_rel(root, best),
                     reason="local CSV work register discovered during adoption")


def find_workbook(root: str) -> Candidate | None:
    def is_workbook(name: str) -> bool:
        low = name.lower()
        return low.endswith((".xlsx", ".xlsm")) and ("queue" in low or "sprint" in low)

    base = doc_root(root) or root
    candidates = [p for p in _files(base, recursive=True, predicate=is_workbook)
                  if not _is_archived(root, p)]
    if not candidates:
        return None
    candidates.sort(key=_score, reverse=True)
    best = os.path.abspath(candidates[0])
    return Candidate(path=best, relative=_rel(root, best),
                     reason="generated workbook discovered during adoption")


def find_lessons(root: str, near: str | None = None) -> Candidate | None:
    def is_lessons(name: str) -> bool:
        low = name.lower()
        return low.endswith(".md") and ("lesson" in low or "retro" in low)

    bases = [b for b in (near, doc_root(root), root) if b]
    for base in bases:
        found = [p for p in _files(base, recursive=(base != root), predicate=is_lessons)
                 if not _is_archived(root, p)]
        if found:
            found.sort(key=_score, reverse=True)
            best = os.path.abspath(found[0])
            return Candidate(path=best, relative=_rel(root, best),
                             reason="retrospective document discovered during adoption")
    return None


def is_empty_project(root: str) -> bool:
    """A brand-new project directory: nothing at all, or only a ``.git`` entry."""
    try:
        return set(os.listdir(root)) <= {".git"}
    except OSError:
        return False


def is_adoptable(root: str) -> bool:
    """An unregistered project with a discoverable live roadmap."""
    return find_roadmap(root) is not None
