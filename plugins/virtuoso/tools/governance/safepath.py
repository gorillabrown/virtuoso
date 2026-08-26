"""Path validation for registered governance roles (redesign item 19).

Every registered path is validated *before use*. The rules, in the order a
finding is reported:

* **root escape** — a relative path that resolves outside the project root.
* **unsafe absolute** — an absolute path outside the project root. (An absolute
  path that resolves *inside* the root is normalized to a relative one and
  accepted, because that is unambiguous and harmless.)
* **archive registered as live authority** — a path living under an archive /
  snapshot segment cannot carry ``live`` authority. An explicitly registered,
  append-only ``terminal`` ledger may live under a durable archive segment
  because it is the archive's record, not competing live authority; terminal
  authority remains forbidden under backups, snapshots, and quarantine.
* **role-type mismatch** — a role declared as a directory pointing at a file, or
  a file role pointing at a directory, or a file role whose extension disagrees
  with its declared provider.

Nothing here creates, opens, or heals anything: validation is pure inspection
plus (optionally) an existence probe. A registered path that is *absent* is a
reportable state, never a reason to go looking for a similarly named file
(item 20).
"""
from __future__ import annotations

import os
import posixpath
from dataclasses import dataclass, field

# Directory segments (case-insensitive, matched whole) that mark archived or
# snapshot material. A role with live authority must not point inside one.
ARCHIVE_SEGMENTS = frozenset(
    {
        "archive",
        "archives",
        "0 archive",
        "backup",
        "backups",
        ".virtuoso-backups",
        "quarantine",
        "snapshot",
        "snapshots",
    }
)

# Terminal records may live in a durable archive, but never in transient,
# duplicated, or quarantined storage.
TERMINAL_FORBIDDEN_SEGMENTS = frozenset(
    {"backup", "backups", ".virtuoso-backups", "quarantine", "snapshot", "snapshots"}
)

# Authority levels that must never resolve inside an archive segment.
_ARCHIVE_FORBIDDEN_AUTHORITIES = frozenset({"live"})

_PROVIDER_EXTENSIONS = {
    "csv": {".csv"},
    "markdown": {".md", ".markdown"},
    "xlsx": {".xlsx", ".xlsm"},
    "jsonl": {".jsonl", ".ndjson"},
    "json": {".json"},
}


@dataclass
class PathVerdict:
    """The outcome of validating one registered path."""

    role: str
    raw: str
    normalized: str = ""
    absolute: str = ""
    findings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings


def _to_posix(rel: str) -> str:
    return rel.replace("\\", "/")


def normalize(root: str, raw: str) -> tuple[str, str]:
    """Return ``(relative_posix, absolute)`` for ``raw`` interpreted against ``root``.

    Does not touch the filesystem beyond ``os.path.abspath`` normalization, and
    deliberately does not resolve symlinks — a registry records where a document
    is *registered*, not where a link happens to point today.
    """
    root_abs = os.path.abspath(root)
    candidate = raw.strip()
    if os.path.isabs(candidate) or (len(candidate) > 1 and candidate[1] == ":"):
        absolute = os.path.abspath(candidate)
    else:
        absolute = os.path.abspath(os.path.join(root_abs, candidate))
    rel = os.path.relpath(absolute, root_abs)
    return _to_posix(rel), absolute


def is_inside(root: str, absolute: str) -> bool:
    root_abs = os.path.abspath(root)
    try:
        rel = os.path.relpath(absolute, root_abs)
    except ValueError:
        # Different drives on Windows.
        return False
    return rel == "." or not rel.startswith("..")


def in_named_segment(relative_posix: str, names: frozenset[str]) -> bool:
    segments = [s for s in _to_posix(relative_posix).lower().split("/") if s]
    # The final segment is the document itself; only its ancestors classify it.
    return any(seg in names for seg in segments[:-1])


def in_archive_segment(relative_posix: str) -> bool:
    return in_named_segment(relative_posix, ARCHIVE_SEGMENTS)


def validate_path(
    root: str,
    role: str,
    raw: str,
    *,
    authority: str = "reference",
    expect: str = "any",
    provider: str = "",
    allow_absolute: bool = False,
) -> PathVerdict:
    """Validate one registered path.

    ``expect`` is ``"file"``, ``"directory"``, or ``"any"``. ``provider`` narrows
    the acceptable extensions for a file role. ``allow_absolute`` permits an
    absolute path that resolves outside the root (used only by explicitly
    user-authorized flows, never by the default validator).
    """
    verdict = PathVerdict(role=role, raw=raw)
    if not isinstance(raw, str) or not raw.strip():
        verdict.findings.append("role %r has an empty path" % role)
        return verdict

    rel, absolute = normalize(root, raw)
    verdict.normalized = rel
    verdict.absolute = absolute

    was_absolute = os.path.isabs(raw.strip()) or (len(raw.strip()) > 1 and raw.strip()[1] == ":")
    inside = is_inside(root, absolute)

    if not inside:
        if was_absolute and not allow_absolute:
            verdict.findings.append(
                "role %r registers an absolute path outside the project root: %s" % (role, raw)
            )
        elif not was_absolute:
            verdict.findings.append(
                "role %r escapes the project root: %s (resolves to %s)" % (role, raw, absolute)
            )
        return verdict

    if authority in _ARCHIVE_FORBIDDEN_AUTHORITIES and in_archive_segment(rel):
        verdict.findings.append(
            "role %r claims %s authority but is registered under an archive path: %s"
            % (role, authority, rel)
        )
    if authority == "terminal" and in_named_segment(rel, TERMINAL_FORBIDDEN_SEGMENTS):
        verdict.findings.append(
            "role %r claims terminal authority but is registered under transient storage: %s"
            % (role, rel)
        )

    if os.path.exists(absolute):
        if expect == "file" and os.path.isdir(absolute):
            verdict.findings.append("role %r expects a file but %s is a directory" % (role, rel))
        elif expect == "directory" and os.path.isfile(absolute):
            verdict.findings.append("role %r expects a directory but %s is a file" % (role, rel))

    if expect == "file" and provider in _PROVIDER_EXTENSIONS:
        ext = posixpath.splitext(rel)[1].lower()
        allowed = _PROVIDER_EXTENSIONS[provider]
        if ext and ext not in allowed:
            verdict.findings.append(
                "role %r declares provider %r but is registered at %s (expected one of %s)"
                % (role, provider, rel, ", ".join(sorted(allowed)))
            )

    return verdict
