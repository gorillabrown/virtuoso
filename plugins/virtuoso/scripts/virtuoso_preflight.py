"""Idempotent bootstrap / heal of a per-project Virtuoso workspace.

Modes:
  create  build/heal the selected workspace layout, write the marker, report.
  detect  act only if <root>/Virtuoso (or its marker) already exists; else no-op.

Layouts:
  plugin-only  keep project documentation outside Virtuoso/ under Project Documentation/.
  canonical    keep project documentation under Virtuoso/Project Documentation/.
  auto         reuse the recorded layout, or default to plugin-only for new workspaces.

Always records the plugin root to ``<home>/.virtuoso/plugin-root`` so skill bodies
can locate bundled scripts without relying on ${CLAUDE_PLUGIN_ROOT} (which does not
resolve inside skill/command markdown — only in hooks/MCP). It also vendors the
bundled scripts into ``Virtuoso/scripts/`` so skills can call them workspace-relative.

User content (Roadmap.md, sprint-queue.xlsx, lessons) is never overwritten; bundled
scripts are refreshed to track the installed plugin version. Usage:

    python virtuoso_preflight.py --root <dir> [--mode create|detect]
        [--layout auto|plugin-only|canonical] [--quiet]
"""
import argparse
import json
import os
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

LAYOUTS = ("auto", "plugin-only", "canonical")
DOC_ROOT_CANDIDATES = ("Project Documentation", "2. Project Documentation")
DOC_SUBDIRS = {
    "governance": "1 governance",
    "operational": "2 operational",
    "temp": "3 temp",
    "outside_audits": "4 Outside Audits",
    "reference": "5 Reference",
}

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


def _read_recorded_layout(root):
    try:
        with open(_layout_manifest(root), "r", encoding="utf-8") as f:
            layout = json.load(f).get("layout")
        if layout in ("plugin-only", "canonical"):
            return layout
    except (OSError, ValueError, TypeError):
        pass
    return None


def _resolve_layout(root, requested):
    if requested != "auto":
        return requested
    return _read_recorded_layout(root) or "plugin-only"


def _project_doc_root(root):
    for name in DOC_ROOT_CANDIDATES:
        path = os.path.join(root, name)
        if os.path.isdir(path):
            return path
    return os.path.join(root, "Project Documentation")


def _workspace_paths(root, layout):
    v = os.path.join(root, "Virtuoso")
    docs = os.path.join(v, "Project Documentation") if layout == "canonical" else _project_doc_root(root)
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
    }


def _ensure_dir(path, created):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
        created.append(path)


def _ensure_file(path, content, created):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        created.append(path)


def _ensure_copy(src, dst, created):
    """Copy only if the destination is absent (preserves user content)."""
    if not os.path.exists(dst) and os.path.exists(src):
        shutil.copyfile(src, dst)
        created.append(dst)


def _move_missing(src, dst, created):
    """Move src to dst only when dst is absent. Existing destinations always win."""
    if not os.path.exists(src) or os.path.exists(dst):
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    created.append(dst + " (migrated)")


def _merge_dir_missing(src, dst, created):
    """Move missing children from src into dst without overwriting conflicts."""
    if not os.path.isdir(src):
        return
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        if os.path.isdir(s) and os.path.isdir(d):
            _merge_dir_missing(s, d, created)
        elif not os.path.exists(d):
            shutil.move(s, d)
            created.append(d + " (migrated)")


def _refresh_copy(src, dst, created):
    """Copy plugin-managed files, overwriting only when content differs."""
    if not os.path.exists(src):
        return
    if os.path.exists(dst):
        try:
            with open(src, "rb") as a, open(dst, "rb") as b:
                if a.read() == b.read():
                    return
        except OSError:
            pass
        shutil.copyfile(src, dst)
        created.append(dst + " (refreshed)")
    else:
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


def _write_layout_manifest(root, layout, paths, created):
    data = {
        "layout": layout,
        "documentationRoot": _rel(root, paths["docs"]),
        "paths": {
            "governance": _rel(root, paths["governance"]),
            "operational": _rel(root, paths["operational"]),
            "temp": _rel(root, paths["temp"]),
            "outsideAudits": _rel(root, paths["outside_audits"]),
            "reference": _rel(root, paths["reference"]),
            "roadmap": _rel(root, paths["roadmap"]),
            "sprintQueue": _rel(root, paths["sprint_queue"]),
            "lessons": _rel(root, paths["lessons"]),
            "workflowReference": _rel(root, paths["workflow_reference"]),
            "closeOuts": _rel(root, paths["close_outs"]),
            "issues": _rel(root, paths["issues"]),
            "scripts": _rel(root, paths["scripts"]),
        },
    }
    _refresh_text(_layout_manifest(root), json.dumps(data, indent=2) + "\n", created)


def _migrate_to_canonical(root, paths, created):
    """Move legacy/root documentation into the canonical tree when destinations are free."""
    v = paths["workspace"]
    for doc_root in [os.path.join(root, name) for name in DOC_ROOT_CANDIDATES]:
        if os.path.abspath(doc_root) == os.path.abspath(paths["docs"]):
            continue
        _merge_dir_missing(os.path.join(doc_root, DOC_SUBDIRS["governance"]), paths["governance"], created)
        _merge_dir_missing(os.path.join(doc_root, DOC_SUBDIRS["operational"]), paths["operational"], created)
        _merge_dir_missing(os.path.join(doc_root, DOC_SUBDIRS["temp"]), paths["temp"], created)
        _merge_dir_missing(os.path.join(doc_root, DOC_SUBDIRS["outside_audits"]), paths["outside_audits"], created)
        _merge_dir_missing(os.path.join(doc_root, DOC_SUBDIRS["reference"]), paths["reference"], created)

    _move_missing(os.path.join(root, "Roadmap.md"), paths["roadmap"], created)
    _move_missing(os.path.join(root, "SpecRetro.Lessons_Learned.md"), paths["lessons"], created)
    _move_missing(os.path.join(root, "sprint-queue.xlsx"), paths["sprint_queue"], created)
    _move_missing(os.path.join(root, "WORKFLOW_REFERENCE.md"), paths["workflow_reference"], created)

    _move_missing(os.path.join(v, "Roadmap.md"), paths["roadmap"], created)
    _move_missing(os.path.join(v, "SpecRetro.Lessons_Learned.md"), paths["lessons"], created)
    _move_missing(os.path.join(v, "sprint-queue.xlsx"), paths["sprint_queue"], created)
    _move_missing(os.path.join(v, "WORKFLOW_REFERENCE.md"), paths["workflow_reference"], created)
    _merge_dir_missing(os.path.join(v, "roadmap-reviews"), paths["roadmap_reviews"], created)
    _merge_dir_missing(os.path.join(v, "Close-Outs"), paths["close_outs"], created)
    _merge_dir_missing(os.path.join(v, "Issues"), paths["issues"], created)
    _merge_dir_missing(os.path.join(v, "audits"), paths["outside_audits"], created)


def preflight(root, mode="create", quiet=False, layout="auto"):
    record_root()  # always — the plugin-root bridge for skill bodies
    if mode == "detect" and not _is_project(root):
        _say(quiet, "virtuoso: no Virtuoso/ workspace here — skipping "
                    "(run /virtuoso-init to create one).")
        return []
    layout = _resolve_layout(root, layout)
    paths = _workspace_paths(root, layout)
    created = []
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

    if layout == "canonical":
        _migrate_to_canonical(root, paths, created)

    _ensure_file(os.path.join(paths["workspace"], ".virtuoso"), "virtuoso-workspace\n", created)
    _ensure_file(paths["roadmap"], ROADMAP_SEED, created)
    _ensure_file(paths["lessons"], LESSONS_SEED, created)
    if os.path.exists(WORKFLOW_REF_TEMPLATE):
        _ensure_copy(WORKFLOW_REF_TEMPLATE, paths["workflow_reference"], created)
    else:
        _ensure_file(paths["workflow_reference"], WORKFLOW_REF_FALLBACK, created)
    # User data — never clobber:
    _ensure_copy(TEMPLATE_XLSX, paths["sprint_queue"], created)
    # Plugin-managed scripts — vendor into the workspace for workspace-relative calls:
    for src in VENDOR_SCRIPTS:
        _refresh_copy(src, os.path.join(paths["scripts"], os.path.basename(src)), created)
    _write_layout_manifest(root, layout, paths, created)

    if created:
        _say(quiet, "virtuoso: layout=%s; created/updated %d item(s):" % (layout, len(created)))
        for c in created:
            _say(quiet, "  + " + os.path.relpath(c.split(" (refreshed)")[0], root)
                 + (" (refreshed)" if c.endswith("(refreshed)") else "")
                 + (" (migrated)" if c.endswith("(migrated)") else ""))
    else:
        _say(quiet, "virtuoso: layout=%s; workspace already complete — nothing to do." % layout)
    return created


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--mode", choices=["create", "detect"], default="create")
    ap.add_argument("--layout", choices=LAYOUTS, default="auto")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    preflight(a.root, a.mode, a.quiet, a.layout)


if __name__ == "__main__":
    main()
