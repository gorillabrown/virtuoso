"""Idempotent bootstrap / heal / adopt of a per-project Virtuoso workspace.

Modes:
  create  build/heal the selected workspace layout, write the marker, report.
  detect  act only if <root>/Virtuoso (or its marker) already exists, or if root is a
          brand-new empty-dir project (auto-scaffolds then); else report status only.
  adopt   non-destructively bring an *established* project under Virtuoso management:
          if a Virtuoso/ marker exists -> heal; else if the project already has a
          documentation tree (Project Documentation/ or 2. Project Documentation/ with a
          governance/operational subdir or a discoverable roadmap) -> lay down only a thin
          control dir (marker + workspace-layout.json + vendored scripts) whose manifest
          POINTS AT the existing roadmap/sprint-queue. Nothing is moved, nothing is
          duplicated, and no parallel Roadmap.md is seeded. A bare project writes nothing
          and is routed to /virtuoso-init by the caller.

Layouts:
  plugin-only  keep project documentation outside Virtuoso/ under Project Documentation/.
  auto         reuse the recorded layout, or default to plugin-only for new workspaces.

New projects:
  detect (the SessionStart hook path) auto-scaffolds the standard plugin-only workspace when
  the target root is a brand-new project directory -- no entries at all, or only a `.git`
  entry. A non-empty, unmarkered directory stays fully inert under detect either way.

Integrity:
  --check-roadmap PATH   sanity-check a roadmap before a heavyweight rewrite. Exits 0 (ok),
                         2 (warn: empty / oversize), or 3 (fail: null bytes / not UTF-8 /
                         missing). Prints a `roadmap-integrity: ...` line.

Always records the plugin root to ``<home>/.virtuoso/plugin-root`` so skill bodies
can locate bundled scripts without relying on ${CLAUDE_PLUGIN_ROOT} (which does not
resolve inside skill/command markdown — only in hooks/MCP). It also vendors the
bundled scripts into ``Virtuoso/scripts/`` so skills can call them workspace-relative.

User content (Roadmap.md, sprint-queue.xlsx, lessons) is never overwritten; an existing
roadmap under any name is discovered and pointed at rather than re-seeded. Usage:

    python virtuoso_preflight.py --root <dir> [--mode create|detect|adopt]
        [--layout auto|plugin-only] [--quiet]
    python virtuoso_preflight.py --check-roadmap <path>
"""
import argparse
import json
import os
import re
import shutil
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Bundled scripts vendored into the workspace so skills invoke them workspace-relative.
VENDOR_SCRIPTS = [
    os.path.join(PLUGIN_ROOT, "skills", "roadmap-review", "scripts", "recalc.py"),
    os.path.join(PLUGIN_ROOT, "skills", "pointer-closeout", "scripts", "prepare_closeout_files.py"),
]
TEMPLATE_XLSX = os.path.join(
    PLUGIN_ROOT, "skills", "roadmap-review", "assets", "sprint-queue.template.xlsx"
)
WORKFLOW_REF_TEMPLATE = os.path.join(PLUGIN_ROOT, "assets", "WORKFLOW_REFERENCE.template.md")

LAYOUTS = ("auto", "plugin-only")
DOC_ROOT_CANDIDATES = ("Project Documentation", "2. Project Documentation")
DOC_SUBDIRS = {
    "governance": "1 governance",
    "operational": "2 operational",
    "temp": "3 temp",
    "outside_audits": "4 Outside Audits",
    "reference": "5 Reference",
}

# A roadmap larger than this is suspicious for an archive-forward document and earns a
# WARN from the integrity guard (GoG's corrupt 627 KB roadmap trips this).
ROADMAP_OVERSIZE_BYTES = 512 * 1024

# Structural markers that distinguish a live roadmap from an arbitrary *roadmap*.md file.
_ROADMAP_MARKERS = (
    b"Completed Work Summary",
    b"Active & Remaining Sprint",
    b"Finish Line",
    b"roadmap_doc:",
    b"finish_line:",
)
# Directory segments (relative to the documentation root) that mark archived / non-canonical
# copies; discovery excludes roadmaps/queues living under them from being treated as live.
_ARCHIVE_SEGMENTS = (
    "roadmap-reviews", "checkins", "close-outs", "archive", "archives", "0 archive", "audits",
    "3 temp", "4 outside audits", "5 reference",
)
# An untouched virtuoso-init seed carries this exact line in its head; matching the whole
# "**Last updated:**" line (not just the parenthetical) avoids demoting a real roadmap that
# merely quotes the phrase in prose.
_SEED_SENTINEL = "**Last updated:** (initialized by virtuoso-init)"
# Backup/snapshot markers, matched as whole tokens bounded by separators so legitimate
# codenames like "Gold", "Cold", "Threshold", "Scaffold" are NOT mistaken for an "old" backup.
_BACKUP_NAME_TOKENS = ("backup", "snapshot", "copy", "bak", "old")
_BACKUP_NAME_RE = re.compile(
    r"(?:^|[ _\-.()])(?:" + "|".join(_BACKUP_NAME_TOKENS) + r")(?:[ _\-.()]|$)"
)

ROADMAP_SEED = """# Project Roadmap

**Last updated:** (initialized by virtuoso-init)

## How This Document Is Maintained
Archive-forward: the active section holds dispatch-ready full specs for the next 5
sprints, stubs beyond, and one line per completed sprint in the Completed Work
Summary. Full content migrates to a dated archive at close-out.

## Finish Line — Target
(define via /roadmap-review)

## Completed Work Summary
| Sprint | Session | Result | Close-Out |
|--------|---------|--------|-----------|

## Active & Remaining Sprint Skeletons

### Standing Rules All Skeletons Inherit

## Notes

<!-- Frontmatter:
loe_unit: t-shirt
finish_line: ""
roadmap_doc: Roadmap.md
sprint_queue_doc: sprint-queue.xlsx
-->
"""

LESSONS_SEED = "# Spec Retrospective — Lessons Learned\n\n(append SRL-NNN entries here)\n"

WORKFLOW_REF_FALLBACK = (
    "# Workflow Reference\n\n"
    "Legacy WORKFLOW_REFERENCE.md content now lives in the plugin's skills:\n"
    "§4 (effort levels) -> the `effort-levels` skill; "
    "§16 (3rd-party audit) -> the `3rd-party-audit` skill.\n"
)

# The governance registry: the project-root authority every skill reads first to resolve
# where each governance document lives. Regenerated (idempotently) on every create/adopt/heal.
GOVERNANCE_README = "Virtuoso.Governance.Readme.md"

# (machine key -> human label) for the registry table, and (machine key -> _workspace_paths
# key) so the same resolved paths back both the readme and the manifest.
GOVERNANCE_ROLES = [
    ("roadmap", "Roadmap"),
    ("sprintCatalog", "Sprint catalog (CSV — source of truth)"),
    ("sprintQueue", "Sprint queue (xlsx — optional generated report)"),
    ("lessons", "Lessons / retrospective"),
    ("closeOuts", "Close-outs (directory)"),
    ("issues", "Issues (directory)"),
    ("roadmapReviews", "Roadmap reviews (directory)"),
    ("outsideAudits", "Outside audits (directory)"),
    ("reference", "Reference (directory)"),
]
_ROLE_PATHKEY = {
    "roadmap": "roadmap", "sprintCatalog": "sprint_catalog", "sprintQueue": "sprint_queue",
    "lessons": "lessons", "closeOuts": "close_outs", "issues": "issues",
    "roadmapReviews": "roadmap_reviews", "outsideAudits": "outside_audits",
    "reference": "reference",
}
# The manifest tracks a handful of structural keys that have no GOVERNANCE_ROLES/readme row
# (they're locations, not documents skills resolve by role). Combined with _ROLE_PATHKEY this
# is the full set of registry keys the plugin already understands -- anything else found in a
# parsed registry is a project-custom role (R2).
_MANIFEST_ONLY_PATHKEY = {
    "governance": "governance", "operational": "operational", "temp": "temp",
    "workflowReference": "workflow_reference", "scripts": "scripts",
    "governanceReadme": "governance_readme",
}
_KNOWN_PATHKEY = dict(_ROLE_PATHKEY)
_KNOWN_PATHKEY.update(_MANIFEST_ONLY_PATHKEY)

GOVERNANCE_README_TEMPLATE = """# Virtuoso Governance Registry

**This file is the authority.** It is the single source of truth for where this project's
governance documents live. Every Virtuoso skill (`/roadmap-review`, `/roadmap-status`,
`/next-pointer`, `/pointer-closeout`, `/mid-dispatch-decision`, `/3rd-party-audit`) resolves
the roadmap, sprint catalog, lessons log, close-outs, issues, and review artifacts through the
registry below — and **never creates a parallel or competing document for a role already
registered here.**

Register the project's real files wherever they actually live (e.g. `docs/governance/ROADMAP.md`).
When a document already exists, this registry points at it; nothing is copied, moved, or seeded
beside it. `Virtuoso/workspace-layout.json` is the machine-readable mirror of the same paths.

## Required documents

| Role | Path | Status |
|------|------|--------|
{table}

## Rules for skills

1. **Resolve every governance document through this registry** before reading or writing.
2. **Never create a new document for a role already registered** — open and edit the
   registered file in place.
3. If a required role is `⬜ not present` and the work needs it, **register the project's
   existing file** (preferred) or create one **and register it here** — never leave a rival
   unregistered or seed an empty template beside a real document.
4. If the registry and the files on disk diverge, **fix the registry** (repoint the path to
   the existing document) — do not fork a rival.

<!-- virtuoso-governance-registry
{machine}
-->
"""

# Machine block: a fenced comment holding one "key: relative/path" line per role, verbatim-
# parseable so a corrupt/missing manifest can be reconstructed from it (R2 last criterion).
_MACHINE_BLOCK_RE = re.compile(r"<!--\s*virtuoso-governance-registry\s*\n(.*?)\n-->", re.DOTALL)
_MACHINE_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.+)$")
# camelCase word boundary, used to derive a human label for an unrecognized registry key.
_CAMEL_BOUNDARY_RE = re.compile(r"(?<!^)(?=[A-Z])")


def _home():
    return os.environ.get("VIRTUOSO_HOME") or os.path.expanduser("~")


def record_root():
    """Record the plugin root so skill bodies can locate bundled scripts. Non-fatal."""
    try:
        d = os.path.join(_home(), ".virtuoso")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "plugin-root"), "w", encoding="utf-8") as f:
            f.write(PLUGIN_ROOT + "\n")
    except OSError:
        pass


def _say(quiet, msg):
    if not quiet:
        print(msg)


def _is_project(root):
    v = os.path.join(root, "Virtuoso")
    return os.path.isdir(v) or os.path.isfile(os.path.join(v, ".virtuoso"))


def _layout_manifest(root):
    return os.path.join(root, "Virtuoso", "workspace-layout.json")


def _read_manifest(root):
    try:
        with open(_layout_manifest(root), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _read_recorded_layout(root):
    """A manifest recording anything other than "plugin-only" -- including a legacy
    "canonical" value from before canonical layout was removed, or any other unrecognized
    value -- is treated as unset and falls back to the plugin-only default (_resolve_layout).
    Registry-authoritative: content stays wherever it's registered; nothing migrates."""
    layout = _read_manifest(root).get("layout")
    return layout if layout == "plugin-only" else None


def _read_adopted(root):
    """True when the recorded workspace was laid down by a thin adopt (heal stays thin)."""
    return bool(_read_manifest(root).get("adopted"))


def _read_registry_from_readme(root):
    """Parse the virtuoso-governance-registry machine block out of the governance readme.
    Returns {key: relative path} or None when the readme is absent or has no parseable block."""
    try:
        with open(os.path.join(root, GOVERNANCE_README), "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    m = _MACHINE_BLOCK_RE.search(text)
    if not m:
        return None
    overlay = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        lm = _MACHINE_LINE_RE.match(line)
        if lm:
            overlay[lm.group(1)] = lm.group(2).strip()
    return overlay or None


def _assert_registry_mirror(root):
    """Post-write invariant (SK-01): after any run that regenerates the registry, the governance
    readme's machine block must parse to exactly the manifest's path mapping for every known
    governance role. Compares _read_registry_from_readme's parsed overlay against
    workspace-layout.json's "paths", filtered to the roles _ROLE_PATHKEY maps -- manifest-only
    structural keys (governance/operational/temp/...) and project-custom roles (R2) are out of
    scope for this specific check. On any mismatch, raises with BOTH mappings so the divergence
    is diagnosable -- this never silently writes a "repaired" second pass."""
    manifest_paths = _read_manifest(root).get("paths")
    if not isinstance(manifest_paths, dict):
        manifest_paths = {}
    expected = {k: v for k, v in manifest_paths.items() if k in _ROLE_PATHKEY}
    if not expected:
        return  # nothing this check can verify (e.g. manifest carries no known roles yet)
    readme_overlay = _read_registry_from_readme(root) or {}
    mismatched = [k for k, v in expected.items() if readme_overlay.get(k) != v]
    if mismatched:
        readme_side = {k: readme_overlay.get(k) for k in sorted(expected)}
        manifest_side = {k: expected[k] for k in sorted(expected)}
        raise RuntimeError(
            "registry mirror invariant violated: readme machine block does not match "
            "manifest paths for role(s) %s\n  readme:   %s\n  manifest: %s"
            % (sorted(mismatched), readme_side, manifest_side)
        )


def _read_registry_overlay(root):
    """Registry-authoritative resolution order (R2): parse workspace-layout.json's "paths"
    dict as the base overlay, then per-key merge (SK-02 / R10) -- for any KNOWN governance role
    (_KNOWN_PATHKEY) that the manifest overlay is missing (e.g. roadmapReviews before its first
    post-migration write, or any future role added to the schema), consult the governance
    readme's machine block before falling back to a computed default. The manifest wins
    outright once it carries a key; before a key migrates into the manifest schema, the readme
    is its only carrier and must not be clobbered by the next regeneration. Falls back to the
    readme's overlay wholesale when the manifest has no "paths" at all (e.g. reconstruction
    after the manifest is deleted). Returns {key: relative path string} covering both known
    roles and unrecognized project-custom keys, or None when neither source has anything."""
    manifest_paths = _read_manifest(root).get("paths")
    manifest_overlay = {}
    if isinstance(manifest_paths, dict):
        manifest_overlay = {k: v for k, v in manifest_paths.items() if isinstance(v, str)}
    readme_overlay = _read_registry_from_readme(root)
    if not manifest_overlay:
        return readme_overlay
    if readme_overlay:
        merged = dict(manifest_overlay)
        for key, rel in readme_overlay.items():
            if key in _KNOWN_PATHKEY and key not in merged:
                merged[key] = rel
        return merged
    return manifest_overlay


def _apply_registry_overlay(root, paths, overlay):
    """Override computed-default paths with the registry's curated values (R2). A known key
    (readme role or manifest-structural key) overrides the matching paths[...] entry outright
    -- registered-but-missing-on-disk paths are kept as-is, never re-guessed (R4). Anything
    else is an unrecognized project-custom role, returned separately (in the overlay's own
    order) so callers can round-trip it verbatim into both regenerated outputs."""
    custom = {}
    if not overlay:
        return custom
    for key, rel in overlay.items():
        pathkey = _KNOWN_PATHKEY.get(key)
        if pathkey:
            paths[pathkey] = os.path.join(root, rel)
        else:
            custom[key] = rel
    return custom


def _derive_label(key, abs_path):
    """Human label for an unrecognized (project-custom) registry key, used for its readme row
    (R2: "readme rows with a derived label"): split camelCase into words, sentence-case them,
    and mark directories -- "roadmapArchives" -> "Roadmap archives (directory)",
    "epics" -> "Epics"."""
    spaced = _CAMEL_BOUNDARY_RE.sub(" ", key)
    label = spaced[:1].upper() + spaced[1:].lower()
    if os.path.isdir(abs_path):
        label += " (directory)"
    return label


def _resolve_layout(root, requested):
    if requested != "auto":
        return requested
    return _read_recorded_layout(root) or "plugin-only"


def _established_doc_root(root):
    """The pre-existing documentation root, if any (prefers the canonical-name candidate)."""
    for name in DOC_ROOT_CANDIDATES:
        path = os.path.join(root, name)
        if os.path.isdir(path):
            return path
    return None


def _project_doc_root(root):
    return _established_doc_root(root) or os.path.join(root, "Project Documentation")


def _is_adoptable(root):
    """An un-markered project with a discoverable live roadmap (in a Project Documentation
    tree, a docs/ tree, or at the root), which we can adopt in place. A project with no live
    roadmap routes to /virtuoso-init (which seeds one) rather than adopting and pointing the
    manifest at a file that does not exist."""
    if _is_project(root):
        return False
    return _discover_roadmap_anywhere(root) is not None


def _is_new_project_root(root):
    """True when `root` is a brand-new project directory: no entries at all, or only a `.git`
    entry (a freshly-initialized repo with no other content yet). There is nothing here detect
    could clobber, so a new project auto-scaffolds the standard plugin-only workspace even from
    detect (the SessionStart hook path) -- a non-empty, unmarkered directory stays fully inert
    under detect either way."""
    try:
        entries = set(os.listdir(root))
    except OSError:
        return False
    return entries <= {".git"}


def _walk_docs(doc_root):
    if not doc_root or not os.path.isdir(doc_root):
        return
    for dirpath, _dirs, files in os.walk(doc_root):
        yield dirpath, files


def _is_archived(path, doc_root):
    """True when path lives under an archive / non-canonical subdir of doc_root (checked on
    the path RELATIVE to doc_root, so a project that merely happens to sit under a directory
    named e.g. 'archive' is not misclassified)."""
    rel = os.path.relpath(path, doc_root).replace("\\", "/").lower()
    return any(seg in _ARCHIVE_SEGMENTS for seg in rel.split("/")[:-1])


def _looks_like_seed(path):
    """True for an untouched virtuoso-init roadmap seed (sentinel still in its head)."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return _SEED_SENTINEL in f.read(2048)
    except OSError:
        return False


def _has_backup_name(path):
    # Drop only the final extension so "Roadmap.bak.md" -> "roadmap.bak" still matches "bak".
    stem = os.path.basename(path).lower().rsplit(".", 1)[0]
    return bool(_BACKUP_NAME_RE.search(stem))


def _roadmap_score(p):
    """Rank a roadmap candidate: real roadmaps (structural markers, recently edited) outrank
    a fresh virtuoso-init seed and backup/snapshot copies; ties break on recency then size."""
    try:
        with open(p, "rb") as f:
            head = f.read(16384)
    except OSError:
        head = b""
    structural = sum(1 for m in _ROADMAP_MARKERS if m in head)
    try:
        mtime = os.path.getmtime(p)
    except OSError:
        mtime = 0
    try:
        size = os.path.getsize(p)
    except OSError:
        size = 0
    return (
        0 if _looks_like_seed(p) else 1,   # fresh seed placeholder sinks below any real roadmap
        0 if _has_backup_name(p) else 1,   # OLD/backup/copy snapshots sink
        structural,                         # real roadmaps carry structural markers
        mtime,                              # most recently edited wins
        size,                               # final tiebreak
    )


def _roadmap_candidates(base, recursive=True):
    """Absolute paths of *roadmap*.md files under base — walked recursively, or (when
    recursive=False) only the files sitting directly in base (used for a shallow root scan so
    we never walk an entire repository looking for a root-level ROADMAP.md)."""
    if not base or not os.path.isdir(base):
        return []
    if recursive:
        pairs = list(_walk_docs(base))
    else:
        pairs = [(base, [f for f in os.listdir(base)
                         if os.path.isfile(os.path.join(base, f))])]
    return [
        os.path.join(dirpath, fn)
        for dirpath, files in pairs
        for fn in files
        if fn.lower().endswith(".md") and "roadmap" in fn.lower()
    ]


def _discover_roadmap(doc_root):
    """Find the project's LIVE roadmap under doc_root (any *roadmap*.md name). Archived copies
    (under roadmap-reviews/, 3 temp/, etc.) are excluded outright; an untouched virtuoso-init
    seed and backup/snapshot copies are demoted below any real roadmap; ties break on recency
    then size. Returns an absolute path or None when no live roadmap exists."""
    live = [p for p in _roadmap_candidates(doc_root, recursive=True)
            if not _is_archived(p, doc_root)]
    if not live:
        return None
    live.sort(key=_roadmap_score, reverse=True)
    return live[0]


def _discover_roadmap_anywhere(root):
    """Find the project's live roadmap across common layouts, not just a Project Documentation
    tree: an established doc-root candidate (recursive), a docs/ or docs/governance tree
    (recursive), and root-level *roadmap*.md files (shallow). This lets an established project
    whose governance lives outside a Project Documentation folder — e.g. a root ROADMAP.md plus
    docs/governance/ — be adopted in place and registered, instead of being seeded over with a
    parallel empty template. Returns an absolute path or None."""
    cands = []
    est = _established_doc_root(root)
    if est:
        cands += _roadmap_candidates(est, recursive=True)
    for extra in ("docs", os.path.join("docs", "governance")):
        cands += _roadmap_candidates(os.path.join(root, extra), recursive=True)
    cands += _roadmap_candidates(root, recursive=False)
    seen, live = set(), []
    for p in cands:
        ap = os.path.abspath(p)
        if ap in seen:
            continue
        seen.add(ap)
        if not _is_archived(p, root):
            live.append(p)
    if not live:
        return None
    live.sort(key=_roadmap_score, reverse=True)
    return live[0]


def _discover_sprint_queue(doc_root):
    """Find the project's LIVE sprint queue (any *sprint*queue*.xlsx). Archived copies are
    excluded; prefers 2 operational, then recency, then size. Returns a path or None."""
    cands = [
        os.path.join(dirpath, fn)
        for dirpath, files in _walk_docs(doc_root)
        for fn in files
        if fn.lower().endswith(".xlsx") and "sprint" in fn.lower() and "queue" in fn.lower()
    ]
    live = [p for p in cands if not _is_archived(p, doc_root)]
    if not live:
        return None

    def score(p):
        rel = os.path.relpath(p, doc_root).replace("\\", "/").lower()
        try:
            mtime = os.path.getmtime(p)
        except OSError:
            mtime = 0
        try:
            size = os.path.getsize(p)
        except OSError:
            size = 0
        return (
            0 if _has_backup_name(p) else 1,
            1 if "2 operational" in rel else 0,
            mtime,
            size,
        )

    live.sort(key=score, reverse=True)
    return live[0]


def _workspace_paths(root):
    v = os.path.join(root, "Virtuoso")
    docs = _project_doc_root(root)
    governance = os.path.join(docs, DOC_SUBDIRS["governance"])
    operational = os.path.join(docs, DOC_SUBDIRS["operational"])
    temp = os.path.join(docs, DOC_SUBDIRS["temp"])
    outside_audits = os.path.join(docs, DOC_SUBDIRS["outside_audits"])
    reference = os.path.join(docs, DOC_SUBDIRS["reference"])
    return {
        "workspace": v,
        "docs": docs,
        "governance": governance,
        "operational": operational,
        "temp": temp,
        "outside_audits": outside_audits,
        "reference": reference,
        "roadmap_reviews": os.path.join(operational, "roadmap-reviews"),
        "roadmap_checkins": os.path.join(operational, "roadmap-reviews", "checkins"),
        "close_outs": os.path.join(operational, "Close-Outs"),
        "issues": os.path.join(operational, "Issues"),
        "scripts": os.path.join(v, "scripts"),
        "roadmap": os.path.join(governance, "Roadmap.md"),
        "lessons": os.path.join(governance, "SpecRetro.Lessons_Learned.md"),
        "workflow_reference": os.path.join(reference, "WORKFLOW_REFERENCE.md"),
        "sprint_queue": os.path.join(operational, "sprint-queue.xlsx"),
        "sprint_catalog": os.path.join(operational, "sprint-catalog.csv"),
        "governance_readme": os.path.join(root, GOVERNANCE_README),
    }


def _apply_discovery(paths, overlay=None):
    """Repoint roadmap/sprint_queue at an existing document when one is discoverable,
    so the conventional seed is never written beside a roadmap that already exists.
    A role the registry already has (R2) is never handed to discovery -- a structurally-
    richer archive must never outrank a curated registration. Returns (roadmap_found,
    queue_found), where "found" also covers "already registered"."""
    overlay = overlay or {}
    roadmap_registered = "roadmap" in overlay
    queue_registered = "sprintQueue" in overlay
    roadmap = None if roadmap_registered else _discover_roadmap(paths["docs"])
    queue = None if queue_registered else _discover_sprint_queue(paths["docs"])
    if roadmap:
        paths["roadmap"] = roadmap
    if queue:
        paths["sprint_queue"] = queue
    return (roadmap_registered or bool(roadmap)), (queue_registered or bool(queue))


def _ensure_dir(path, created):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
        created.append(path)


def _ensure_file(path, content, created):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        created.append(path)


def _ensure_copy(src, dst, created):
    """Copy only if the destination is absent (preserves user content)."""
    if not os.path.exists(dst) and os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        created.append(dst)


def _refresh_copy(src, dst, created):
    """Copy plugin-managed files, overwriting only when content differs. Comparison normalizes
    \\r\\n -> \\n on both sides first (R5), so a destination that differs from the plugin's
    copy only by line-ending convention (e.g. a CRLF-committed vendored script vs the plugin's
    LF source) is left alone -- never treated as drift."""
    if not os.path.exists(src):
        return
    if os.path.exists(dst):
        try:
            with open(src, "rb") as a, open(dst, "rb") as b:
                a_data, b_data = a.read(), b.read()
            if a_data == b_data or a_data.replace(b"\r\n", b"\n") == b_data.replace(b"\r\n", b"\n"):
                return
        except OSError:
            pass
        shutil.copyfile(src, dst)
        created.append(dst + " (refreshed)")
    else:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        created.append(dst)


def _refresh_text(path, content, created):
    current = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            current = f.read()
    except OSError:
        pass
    if current == content:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    created.append(path + (" (refreshed)" if current is not None else ""))


def _rel(root, path):
    return os.path.relpath(path, root).replace("\\", "/")


def _write_layout_manifest(root, layout, paths, created, custom_paths=None, adopted=False):
    # SK-02 / R10: an existing manifest's documentationRoot is preserved verbatim rather than
    # recomputed on every regeneration. _project_doc_root's discovery pass falls back to the
    # plugin's own default candidate name whenever a project's real doc root isn't one of
    # DOC_ROOT_CANDIDATES, which would otherwise silently clobber a curated custom value.
    existing_doc_root = _read_manifest(root).get("documentationRoot")
    documentation_root = (
        existing_doc_root if isinstance(existing_doc_root, str) and existing_doc_root
        else _rel(root, paths["docs"])
    )
    data = {
        "layout": layout,
        "adopted": bool(adopted),
        "documentationRoot": documentation_root,
        "paths": {
            "governance": _rel(root, paths["governance"]),
            "operational": _rel(root, paths["operational"]),
            "temp": _rel(root, paths["temp"]),
            "outsideAudits": _rel(root, paths["outside_audits"]),
            "reference": _rel(root, paths["reference"]),
            "roadmap": _rel(root, paths["roadmap"]),
            "sprintQueue": _rel(root, paths["sprint_queue"]),
            "sprintCatalog": _rel(root, paths["sprint_catalog"]),
            "lessons": _rel(root, paths["lessons"]),
            "workflowReference": _rel(root, paths["workflow_reference"]),
            "closeOuts": _rel(root, paths["close_outs"]),
            "issues": _rel(root, paths["issues"]),
            "roadmapReviews": _rel(root, paths["roadmap_reviews"]),
            "scripts": _rel(root, paths["scripts"]),
            "governanceReadme": _rel(root, paths["governance_readme"]),
        },
    }
    # R2: round-trip project-custom registry keys verbatim, after the known roles.
    for key, rel in (custom_paths or {}).items():
        data["paths"][key] = rel
    _refresh_text(_layout_manifest(root), json.dumps(data, indent=2) + "\n", created)


def _write_governance_readme(root, paths, created, custom_paths=None):
    """Render the project-root governance registry — the authority skills read first. Lists
    each required document role and its resolved path, marking present vs. absent. Content is
    deterministic (no timestamp) so re-runs stay idempotent. Project-custom registry keys
    (R2) are appended after the known roles, with a derived label."""
    rows, machine = [], []
    for key, label in GOVERNANCE_ROLES:
        ap = paths[_ROLE_PATHKEY[key]]
        rel = _rel(root, ap)
        status = "✅ registered" if os.path.exists(ap) else "⬜ not present"
        rows.append("| %s | `%s` | %s |" % (label, rel, status))
        machine.append("%s: %s" % (key, rel))
    for key, rel in (custom_paths or {}).items():
        ap = os.path.join(root, rel)
        status = "✅ registered" if os.path.exists(ap) else "⬜ not present"
        label = _derive_label(key, ap)
        rows.append("| %s | `%s` | %s |" % (label, rel, status))
        machine.append("%s: %s" % (key, rel))
    body = GOVERNANCE_README_TEMPLATE.format(table="\n".join(rows), machine="\n".join(machine))
    _refresh_text(paths["governance_readme"], body, created)


def _vendor_scripts(paths, created):
    for src in VENDOR_SCRIPTS:
        _refresh_copy(src, os.path.join(paths["scripts"], os.path.basename(src)), created)


def _build_full(root, layout, created, allow_seed=True):
    """Build/heal the complete documentation tree for the chosen layout. `allow_seed=False`
    (heal/adopt, R3) skips writing template content for any role the registry doesn't already
    cover -- seeding a fresh document is a `create`-mode-only act; heal/adopt just leaves a
    genuinely missing role reported as "not present" (R4) instead of guessing at it."""
    paths = _workspace_paths(root)

    # Registry-authoritative overlay (R2) resolves FIRST, before anything else touches disk --
    # a curated registry's paths (known roles and project-custom ones alike) win over freshly
    # computed defaults for every downstream step: the scaffolding loop and discovery.
    overlay = _read_registry_overlay(root)
    custom_paths = _apply_registry_overlay(root, paths, overlay)

    # Directory scaffolding loop must run on the overlay-resolved paths, or a directory role
    # registered at a non-default path still gets a phantom empty directory conjured at the
    # unused computed-default location.
    for d in [
        paths["workspace"],
        paths["scripts"],
        paths["governance"],
        paths["operational"],
        paths["temp"],
        paths["outside_audits"],
        paths["reference"],
        paths["roadmap_reviews"],
        paths["roadmap_checkins"],
        paths["close_outs"],
        paths["issues"],
    ]:
        _ensure_dir(d, created)

    # Repoint at an existing roadmap/queue (under any name) before seeding, so we never
    # write a parallel Roadmap.md beside a roadmap the project already maintains. A role the
    # overlay already covers is never handed to discovery.
    _apply_discovery(paths, overlay)

    _ensure_file(os.path.join(paths["workspace"], ".virtuoso"), "virtuoso-workspace\n", created)
    if allow_seed:
        if not overlay or "roadmap" not in overlay:
            _ensure_file(paths["roadmap"], ROADMAP_SEED, created)
        if not overlay or "lessons" not in overlay:
            _ensure_file(paths["lessons"], LESSONS_SEED, created)
        if not overlay or "workflowReference" not in overlay:
            if os.path.exists(WORKFLOW_REF_TEMPLATE):
                _ensure_copy(WORKFLOW_REF_TEMPLATE, paths["workflow_reference"], created)
            else:
                _ensure_file(paths["workflow_reference"], WORKFLOW_REF_FALLBACK, created)
        # User data — never clobber:
        if not overlay or "sprintQueue" not in overlay:
            _ensure_copy(TEMPLATE_XLSX, paths["sprint_queue"], created)
    _vendor_scripts(paths, created)
    _write_governance_readme(root, paths, created, custom_paths)
    _write_layout_manifest(root, layout, paths, created, custom_paths, adopted=False)
    _assert_registry_mirror(root)
    return paths


def _anchor_adopted_paths(paths, home):
    """For a project adopted outside a Project Documentation tree, anchor the non-roadmap role
    paths to the discovered roadmap's own directory (the governance home) instead of the
    plugin default — so no registered path points into a Project Documentation tree that does
    not exist. An existing lessons/retro file already sitting in that home is registered as-is;
    otherwise a sensible default basename is anchored there (marked "not present", never
    created)."""
    for key, base in (
        ("lessons", "SpecRetro.Lessons_Learned.md"),
        ("sprint_catalog", "sprint-catalog.csv"),
        ("close_outs", "Close-Outs"),
        ("issues", "Issues"),
        ("roadmap_reviews", "roadmap-reviews"),
        ("outside_audits", "Outside Audits"),
        ("reference", "Reference"),
    ):
        paths[key] = os.path.join(home, base)
    if not os.path.exists(paths["sprint_queue"]):
        paths["sprint_queue"] = os.path.join(home, "sprint-queue.xlsx")
    if os.path.isdir(home):
        for fn in sorted(os.listdir(home)):
            low = fn.lower()
            full = os.path.join(home, fn)
            if os.path.isfile(full) and low.endswith(".md") and ("lesson" in low or "retro" in low):
                paths["lessons"] = full
                break


def _build_thin(root, created):
    """Adopt an established, un-markered project: write only the Virtuoso/ control dir whose
    manifest points at the discovered existing roadmap/queue. No doc tree is scaffolded and
    no roadmap is seeded."""
    paths = _workspace_paths(root)
    overlay = _read_registry_overlay(root)
    custom_paths = _apply_registry_overlay(root, paths, overlay)
    found_rm, _found_q = _apply_discovery(paths, overlay)
    if not found_rm:
        # The project keeps its roadmap outside a Project Documentation tree (root ROADMAP.md,
        # docs/governance, …). Point the registry at the real file rather than a phantom path,
        # and anchor the other roles to that same governance home.
        rm = _discover_roadmap_anywhere(root)
        if rm:
            paths["roadmap"] = rm
            paths["docs"] = os.path.dirname(rm)
            q = _discover_sprint_queue(os.path.dirname(rm))
            if q:
                paths["sprint_queue"] = q
            _anchor_adopted_paths(paths, os.path.dirname(rm))
    _ensure_dir(paths["workspace"], created)
    _ensure_dir(paths["scripts"], created)
    _ensure_file(os.path.join(paths["workspace"], ".virtuoso"), "virtuoso-workspace\n", created)
    _vendor_scripts(paths, created)
    _write_governance_readme(root, paths, created, custom_paths)
    _write_layout_manifest(root, "plugin-only", paths, created, custom_paths, adopted=True)
    _assert_registry_mirror(root)
    return paths


def _heal(root, created):
    """Re-run the appropriate builder for a marker-present project (thin stays thin). Mutates
    `created` in place; callers must not rely on the return value for that (R1) -- heal/adopt
    never seeds (R3: allow_seed=False), so on an already-curated, complete project this is a
    true no-op."""
    if _read_adopted(root):
        return _build_thin(root, created)
    return _build_full(root, _resolve_layout(root, "auto"), created, allow_seed=False)


def _report(created, root, layout, quiet):
    if created:
        _say(quiet, "virtuoso: layout=%s; created/updated %d item(s):" % (layout, len(created)))
        for c in created:
            base = c.split(" (refreshed)")[0]
            suffix = " (refreshed)" if c.endswith("(refreshed)") else ""
            _say(quiet, "  + " + os.path.relpath(base, root) + suffix)
    else:
        _say(quiet, "virtuoso: layout=%s; workspace already complete — nothing to do." % layout)


def preflight(root, mode="create", quiet=False, layout="auto"):
    # Checked before record_root()'s own write touches `root` -- relevant when VIRTUOSO_HOME is
    # sandboxed to `root` itself (tests do this); in real usage record_root() writes under the
    # user's actual home directory, never under `root`, so this ordering doesn't matter there.
    is_new_root = _is_new_project_root(root)
    record_root()  # always — the plugin-root bridge for skill bodies

    if mode == "adopt":
        return adopt(root, quiet)

    if mode == "detect":
        if _is_project(root):
            # R1: `created` must be the mutated list, never _heal()'s return value (that's the
            # builder's `paths` dict, not a change log -- assigning it here silently corrupted
            # both the report below and this function's return value).
            created = []
            _heal(root, created)
            _say(quiet, "virtuoso-status: ready")
            _report(created, root, _resolve_layout(root, "auto"), quiet)
            return created
        if _is_adoptable(root):
            _say(quiet, "virtuoso-status: adoptable")
            _say(quiet, "virtuoso: an established documentation tree exists here but has no "
                        "Virtuoso/ marker - run with --mode adopt (or /virtuoso-init).")
            return []
        if is_new_root:
            # A brand-new project (nothing here to clobber) auto-scaffolds even from detect.
            layout = _resolve_layout(root, "auto")
            created = []
            _build_full(root, layout, created, allow_seed=True)
            _say(quiet, "virtuoso-status: created")
            _report(created, root, layout, quiet)
            return created
        _say(quiet, "virtuoso-status: none")
        _say(quiet, "virtuoso: no Virtuoso/ workspace here — skipping "
                    "(run /virtuoso-init to create one).")
        return []

    # mode == "create"
    layout = _resolve_layout(root, layout)
    created = []
    _build_full(root, layout, created, allow_seed=True)
    _report(created, root, layout, quiet)
    return created


def adopt(root, quiet=False):
    """Non-destructively bring a project under Virtuoso management (see module docstring)."""
    record_root()
    created = []
    if _is_project(root):
        _heal(root, created)
        _say(quiet, "virtuoso-status: ready")
        _report(created, root, _resolve_layout(root, "auto"), quiet)
        return created
    if _is_adoptable(root):
        paths = _build_thin(root, created)
        roadmap_rel = _rel(root, paths["roadmap"]) if os.path.exists(paths["roadmap"]) else ""
        _say(quiet, "virtuoso-status: adopted roadmap=%s" % roadmap_rel)
        _say(quiet, "virtuoso: adopted the existing documentation tree in place - wrote the "
                    "Virtuoso/ control marker pointing at your existing roadmap; nothing was "
                    "moved or duplicated.")
        _report(created, root, "plugin-only (adopted)", quiet)
        return created
    _say(quiet, "virtuoso-status: none")
    _say(quiet, "virtuoso: no Virtuoso/ workspace and no established documentation tree here - "
                "run /virtuoso-init to create one.")
    return []


def check_roadmap(path):
    """Integrity guard for a roadmap about to be rewritten. Returns an exit code:
    0 ok, 2 warn (empty / oversize), 3 fail (missing / null bytes / not UTF-8)."""
    if not path or not os.path.isfile(path):
        print("roadmap-integrity: fail (missing: %s)" % path)
        return 3
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as exc:
        print("roadmap-integrity: fail (unreadable: %s)" % exc)
        return 3

    size = len(data)
    fail, warn = [], []
    if b"\x00" in data:
        fail.append("null-bytes")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        fail.append("not-utf-8")
    if not data.strip():
        warn.append("empty")
    if size > ROADMAP_OVERSIZE_BYTES:
        warn.append("oversize:%d-bytes(>%d)" % (size, ROADMAP_OVERSIZE_BYTES))

    if fail:
        print("roadmap-integrity: fail (%s) size=%d" % (", ".join(fail + warn), size))
        return 3
    if warn:
        print("roadmap-integrity: warn (%s) size=%d" % (", ".join(warn), size))
        return 2
    print("roadmap-integrity: ok size=%d" % size)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--mode", choices=["create", "detect", "adopt"], default="create")
    ap.add_argument("--layout", choices=LAYOUTS, default="auto")
    ap.add_argument("--check-roadmap", dest="check_roadmap", default=None,
                    help="Integrity-check a roadmap file and exit (0 ok / 2 warn / 3 fail).")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    if a.check_roadmap is not None:
        sys.exit(check_roadmap(a.check_roadmap))
    preflight(a.root, a.mode, a.quiet, a.layout)


if __name__ == "__main__":
    main()
