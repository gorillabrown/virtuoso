"""Project overlays — project-owned additions to shipped skills and agents.

A project that needed a shipped skill or agent to behave differently used to copy
the whole file into its own tree and edit it. The fork then drifted from the
plugin in both directions: the plugin gained rules the fork never saw, the fork
gained rules the plugin never saw, and both loaded at once, so the agent read two
contradictory copies of the same instruction.

An **overlay** replaces that. A project registers one optional ``overlays``
directory; inside it, a file at the *same relative path* as a shipped file carries
only that project's additions. The shipped file stays the plugin's, the overlay
stays the project's, nothing is duplicated, and nothing is forked.

Three properties keep it safe:

* **Read-only.** The role is registered ``mutability: read-only`` with no
  ``allowedWriters``, so the guard that already refuses writes to a read-only role
  refuses these too. No ceremony edits a project's overlays.
* **Case-exact.** Lookup compares every path segment against the names the
  filesystem actually reports, so ``skills/Epic/SKILL.md`` never resolves to
  ``skills/epic/SKILL.md`` on a case-insensitive filesystem and then vanishes on a
  case-sensitive one.
* **Bounded.** An overlay adds to, and on conflict overrides, a shipped
  instruction — but it may not loosen a rule in :data:`SAFETY_FLOOR`. Anyone who
  can write the project folder can write an overlay; without that floor, that is
  also permission to switch off the plugin's git and write-permission guards.

Nothing in this module writes, creates, or heals anything.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from .registry import Finding

#: The registry role that declares where a project keeps its overlays. Optional:
#: absent is a normal, fully-supported state, never a defect.
OVERLAY_ROLE = "overlays"

#: The shipped subtrees an overlay may mirror. An overlay file outside these is
#: reported, never silently applied — the mirror path is the whole addressing
#: scheme, so an unaddressable file is a mistake worth naming.
MIRROR_ROOTS = ("skills", "agents", "references")

#: Shipped files inside a mirror root that still may not be overlaid.
#:
#: ``registry-contract.md`` defines what an overlay is and what it may do. A
#: project able to overlay it could rewrite the rules governing its own overlay,
#: including the safety floor below — the contract would become something the
#: thing it governs can edit. Excluding it is a bootstrap argument, not a
#: judgement about the file's content, and it is the only such exclusion: every
#: other shipped reference is a project's to extend.
NON_OVERLAYABLE = frozenset({"references/registry-contract.md"})

#: Directory and file names never treated as overlay content.
_IGNORED_NAMES = frozenset({".git", "__pycache__", ".pytest_cache", ".DS_Store", "Thumbs.db"})

#: Shared-contract rules an overlay may extend or tighten but never loosen.
#: Every entry names a guard whose removal would hand the project folder's write
#: permission to the plugin's own safety machinery.
SAFETY_FLOOR = (
    "registry-resolution",   # resolve through the registry; never hardcode or guess a path
    "read-only-preflight",   # session start and "where am I" checks write nothing
    "write-permission",      # write only where allowedWriters names you
    "git-safety",            # inspect first, stage exact paths, no destructive flags
    "provenance",            # every derived figure cites provider, source, snapshot time
    "issue-contract",        # every stop, hold, block, or elevation becomes an issue
)

#: The marker CI scans for. Present in every shipped skill and agent body; the
#: scan enumerates those folders from disk, so a new skill cannot ship without it.
#:
#: v2 generalized the clause from "this file's overlay" to "the overlay of any
#: shipped file you read". A reference is never read on its own — a skill follows
#: a pointer to it — so under v1 nothing told that skill to check the reference's
#: overlay, and a project's rubric extensions would have been silently ignored.
CLAUSE_MARKER = "<!-- virtuoso-overlay-clause v2 -->"

#: The canonical clause, verbatim, in every shipped skill and agent. This module
#: is its single home: `validate.py` and the test suite compare shipped bodies
#: against this string rather than against a second copy that could drift.
OVERLAY_CLAUSE = """%s
**Project overlay.** If the registry declares an `overlays` role, read the overlay mirroring
every shipped file you read beneath it — this file at its own path (`skills/<skill>/SKILL.md`,
`agents/<Agent>.md`) and any `references/<file>.md` this one sends you to — and apply each on
top of the file it mirrors. Resolve them with the registry helper's `overlays` subcommand;
never fork or edit a shipped file to carry a project's rules. An overlay is additive and
wins on conflict, with one exception: it may not loosen a shared-contract safety rule
(registry resolution, read-only preflight, write permission, git safety, provenance, the
issue contract), and `references/registry-contract.md` may not be overlaid at all. No
`overlays` role, an absent overlays directory, and no matching overlay file all mean the
same thing — proceed on the shipped file alone.""" % CLAUSE_MARKER


# --- case-exact resolution ----------------------------------------------------


def case_exact_join(root: str, relative: str) -> str:
    """The absolute path of ``relative`` beneath ``root``, or ``""``.

    Every segment must match a name the filesystem actually reports. ``os.path``
    existence checks inherit the filesystem's case folding, so on Windows and on a
    default macOS volume they answer *yes* for a path whose case is wrong — and the
    same registry then resolves to nothing on Linux or on CI. Comparing against
    :func:`os.scandir` output makes the answer identical everywhere.

    Returns ``""`` for an absent segment, a case-only mismatch, an absolute or
    empty ``relative``, or any traversal segment.
    """
    if not isinstance(relative, str) or not relative.strip():
        return ""
    normalized = relative.replace("\\", "/").strip().strip("/")
    if not normalized or os.path.isabs(relative.strip()):
        return ""
    current = os.path.abspath(root)
    for segment in normalized.split("/"):
        if not segment or segment in (".", ".."):
            return ""
        try:
            names = {entry.name for entry in os.scandir(current)}
        except OSError:
            return ""
        if segment not in names:
            return ""
        current = os.path.join(current, segment)
    return current


def mirror_path(relative: str) -> str:
    """Normalize a shipped file's path to the posix form overlays are keyed by.

    Returns ``""`` when the path is unusable as a mirror key: absolute, empty, or
    containing a traversal segment.
    """
    if not isinstance(relative, str):
        return ""
    normalized = relative.replace("\\", "/").strip().strip("/")
    if not normalized or os.path.isabs(relative.strip()):
        return ""
    segments = [s for s in normalized.split("/") if s]
    if not segments or any(s in (".", "..") for s in segments):
        return ""
    return "/".join(segments)


def in_mirror_root(relative: str) -> bool:
    """Whether a mirror path addresses one of the shipped subtrees at all.

    Structural only. A path can be in a mirror root and still not be overlayable —
    see :func:`is_overlayable`. The two are kept apart so a project overlaying the
    registry contract is told *why*, rather than told its file mirrors nothing.
    """
    normalized = mirror_path(relative)
    if not normalized:
        return False
    head = normalized.split("/", 1)[0]
    return head in MIRROR_ROOTS


def is_overlayable(relative: str) -> bool:
    """Whether a shipped file at this mirror path may carry an overlay."""
    normalized = mirror_path(relative)
    return bool(normalized) and in_mirror_root(normalized) \
        and normalized not in NON_OVERLAYABLE


# --- resolution against a registry --------------------------------------------


def overlay_root(reg) -> str:
    """The absolute overlays directory for ``reg``, or ``""`` when unregistered.

    An overlays role registered as an external identifier is not a directory this
    plugin can read, so it resolves to ``""`` and is reported by :func:`audit`.
    """
    spec = reg.roles.get(OVERLAY_ROLE)
    if spec is None or spec.is_external or not spec.path:
        return ""
    return os.path.join(reg.root, *spec.path.split("/"))


@dataclass
class Overlay:
    """One resolved overlay and the shipped file it mirrors."""

    mirror: str                    # posix path shared by the shipped file and the overlay
    path: str = ""                 # absolute overlay file, "" when there is none
    plugin_path: str = ""          # absolute shipped file, "" when there is none

    @property
    def present(self) -> bool:
        return bool(self.path)

    @property
    def mirrors_shipped_file(self) -> bool:
        return bool(self.plugin_path)

    def as_dict(self) -> dict:
        return {"mirror": self.mirror, "path": self.path, "pluginPath": self.plugin_path,
                "present": self.present, "mirrorsShippedFile": self.mirrors_shipped_file}


@dataclass
class OverlayStatus:
    """Everything a caller needs to state a result — including that there is none."""

    registered: bool = False
    root: str = ""
    root_present: bool = False
    external: str = ""
    overlays: list[Overlay] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def applied(self) -> list[Overlay]:
        """Overlays that both exist and mirror a shipped file."""
        return [o for o in self.overlays if o.present and o.mirrors_shipped_file]

    @property
    def state(self) -> str:
        """The result, without the label. Always states something: an unregistered
        project reports ``not registered`` rather than nothing, because no output is
        indistinguishable from an all-clear."""
        if not self.registered:
            return "not registered"
        if self.external:
            return "registered externally (%s); not readable as files" % self.external
        if not self.root_present:
            return "registered but absent (%s)" % self.root
        problems = sum(1 for f in self.findings if f.severity in ("error", "warning"))
        suffix = "; %d finding(s)" % problems if problems else ""
        count = len(self.applied)
        if not count:
            return "registered, none present (%s)%s" % (self.root, suffix)
        return "%d applied (%s)%s" % (count, self.root, suffix)

    def line(self) -> str:
        """The labelled one-line result, as preflight and the CLI print it."""
        return "overlays: %s" % self.state

    def as_dict(self) -> dict:
        return {
            "registered": self.registered,
            "root": self.root,
            "rootPresent": self.root_present,
            "external": self.external,
            "safetyFloor": list(SAFETY_FLOOR),
            "overlays": [o.as_dict() for o in self.overlays],
            "findings": [f.as_dict() for f in self.findings],
            "line": self.line(),
        }


def find(reg, plugin_root: str, relative: str) -> Overlay | None:
    """The overlay mirroring ``relative``, or ``None`` when there is not one.

    ``None`` covers every "carry on with the shipped file" case — no role, no
    directory, no matching file — so a caller never has to distinguish them to
    decide what to do next.
    """
    mirror = mirror_path(relative)
    if not mirror or not is_overlayable(mirror):
        return None
    root = overlay_root(reg)
    if not root:
        return None
    resolved = case_exact_join(root, mirror)
    if not resolved or not os.path.isfile(resolved):
        return None
    return Overlay(mirror=mirror, path=resolved,
                   plugin_path=case_exact_join(plugin_root, mirror))


def discover(root: str) -> list[str]:
    """Every overlay file beneath ``root``, as sorted posix mirror paths."""
    found: list[str] = []
    if not root or not os.path.isdir(root):
        return found
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _IGNORED_NAMES
                             and not d.startswith("."))
        for name in sorted(filenames):
            if name in _IGNORED_NAMES or name.startswith("."):
                continue
            relative = os.path.relpath(os.path.join(dirpath, name), root)
            normalized = mirror_path(relative)
            if normalized:
                found.append(normalized)
    return sorted(found)


def _shipped_index(plugin_root: str) -> dict[str, str]:
    """Case-folded mirror path -> the case-exact shipped path, for the overlayable
    subtrees only. Used to tell "no such shipped file" from "the right file, spelled
    with the wrong case"."""
    index: dict[str, str] = {}
    for top in MIRROR_ROOTS:
        base = os.path.join(plugin_root, top)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in _IGNORED_NAMES]
            for name in filenames:
                if name in _IGNORED_NAMES:
                    continue
                relative = os.path.relpath(os.path.join(dirpath, name), plugin_root)
                normalized = mirror_path(relative)
                if normalized:
                    index[normalized.lower()] = normalized
    return index


def audit(reg, plugin_root: str) -> OverlayStatus:
    """Resolve and audit every overlay. Read-only; never creates the directory.

    Findings are informational or warnings and never errors: an overlay problem
    must not turn a working registry into one that needs repair, because repair has
    nothing to propose for a file the project owns.
    """
    status = OverlayStatus()
    spec = reg.roles.get(OVERLAY_ROLE)
    if spec is None:
        return status

    status.registered = True
    if spec.is_external:
        status.external = spec.external
        status.findings.append(Finding(
            "overlays-external", "warning",
            "role %r is registered as the external identifier %r; overlays are read as files, "
            "so nothing is applied. Register a directory inside the project instead."
            % (OVERLAY_ROLE, spec.external), role=OVERLAY_ROLE))
        return status

    status.root = overlay_root(reg)
    if spec.provider not in ("directory", "none"):
        status.findings.append(Finding(
            "overlays-not-a-directory", "warning",
            "role %r declares provider %r; overlays are a directory of files, so register it "
            "with provider 'directory'." % (OVERLAY_ROLE, spec.provider), role=OVERLAY_ROLE))
    if spec.mutability not in ("read-only", "immutable"):
        status.findings.append(Finding(
            "overlays-writable", "warning",
            "role %r declares mutability %r; overlays are the project's own files and the "
            "plugin never writes them. Register it read-only."
            % (OVERLAY_ROLE, spec.mutability), role=OVERLAY_ROLE))
    if spec.allowed_writers:
        status.findings.append(Finding(
            "overlays-has-writers", "warning",
            "role %r names allowedWriters %s; no ceremony writes overlays. Remove them."
            % (OVERLAY_ROLE, ", ".join(spec.allowed_writers)), role=OVERLAY_ROLE))

    status.root_present = bool(status.root) and os.path.isdir(status.root)
    if not status.root_present:
        status.findings.append(Finding(
            "overlays-absent", "info",
            "role %r is registered at %s, which does not exist. Nothing is applied; create the "
            "directory when the project has an overlay to put in it."
            % (OVERLAY_ROLE, spec.path), role=OVERLAY_ROLE))
        return status

    shipped = _shipped_index(plugin_root)
    for mirror in discover(status.root):
        resolved = case_exact_join(status.root, mirror)
        exact = shipped.get(mirror.lower(), "")
        applies = exact == mirror and is_overlayable(mirror)
        plugin_path = case_exact_join(plugin_root, mirror) if applies else ""
        status.overlays.append(Overlay(mirror=mirror, path=resolved, plugin_path=plugin_path))

        if not in_mirror_root(mirror):
            status.findings.append(Finding(
                "overlay-outside-mirror", "warning",
                "overlay %s is not under %s, so no shipped file can address it. Nothing is "
                "applied from it." % (mirror, " or ".join(MIRROR_ROOTS)), role=OVERLAY_ROLE))
            continue
        if not is_overlayable(mirror):
            status.findings.append(Finding(
                "overlay-not-overlayable", "warning",
                "overlay %s mirrors a shipped file that may not be overlaid: it defines what "
                "an overlay may do, so overlaying it would let a project rewrite the rules "
                "governing its own overlay. Nothing is applied from it." % mirror,
                role=OVERLAY_ROLE))
            continue
        if exact and exact != mirror:
            status.findings.append(Finding(
                "overlay-case-mismatch", "warning",
                "overlay %s differs only in case from the shipped file %s. It applies on a "
                "case-insensitive filesystem and silently does nothing elsewhere; rename it to "
                "%s." % (mirror, exact, exact), role=OVERLAY_ROLE))
        elif not exact:
            status.findings.append(Finding(
                "overlay-orphan", "warning",
                "overlay %s mirrors no shipped file. It is never applied — the shipped file may "
                "have been renamed or removed." % mirror, role=OVERLAY_ROLE))
    return status
