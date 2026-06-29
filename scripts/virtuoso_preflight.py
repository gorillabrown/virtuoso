"""Idempotent bootstrap / heal of a per-project ``Virtuoso/`` workspace.

Modes:
  create  build/heal the workspace under <root>/Virtuoso, write the marker, report.
  detect  act only if <root>/Virtuoso (or its marker) already exists; else no-op.

Never overwrites existing files. Usage:

    python virtuoso_preflight.py --root <dir> [--mode create|detect] [--quiet]
"""
import argparse
import os
import shutil
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_XLSX = os.path.join(
    PLUGIN_ROOT, "skills", "roadmap-review", "assets", "sprint-queue.template.xlsx"
)
WORKFLOW_REF_TEMPLATE = os.path.join(
    PLUGIN_ROOT, "assets", "WORKFLOW_REFERENCE.template.md"
)

DIRS = [
    "Virtuoso", "Virtuoso/roadmap-reviews", "Virtuoso/roadmap-reviews/checkins",
    "Virtuoso/Close-Outs", "Virtuoso/audits",
]

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


def _say(quiet, msg):
    if not quiet:
        print(msg)


def _is_project(root):
    v = os.path.join(root, "Virtuoso")
    return os.path.isdir(v) or os.path.isfile(os.path.join(v, ".virtuoso"))


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
    if not os.path.exists(dst) and os.path.exists(src):
        shutil.copyfile(src, dst)
        created.append(dst)


def preflight(root, mode="create", quiet=False):
    if mode == "detect" and not _is_project(root):
        _say(quiet, "virtuoso: no Virtuoso/ workspace here — skipping "
                    "(run /virtuoso-init to create one).")
        return []
    created = []
    for d in DIRS:
        _ensure_dir(os.path.join(root, d), created)
    v = os.path.join(root, "Virtuoso")
    _ensure_file(os.path.join(v, ".virtuoso"), "virtuoso-workspace\n", created)
    _ensure_file(os.path.join(v, "Roadmap.md"), ROADMAP_SEED, created)
    _ensure_file(os.path.join(v, "SpecRetro.Lessons_Learned.md"), LESSONS_SEED, created)
    if os.path.exists(WORKFLOW_REF_TEMPLATE):
        _ensure_copy(WORKFLOW_REF_TEMPLATE, os.path.join(v, "WORKFLOW_REFERENCE.md"), created)
    else:
        _ensure_file(os.path.join(v, "WORKFLOW_REFERENCE.md"), WORKFLOW_REF_FALLBACK, created)
    _ensure_copy(TEMPLATE_XLSX, os.path.join(v, "sprint-queue.xlsx"), created)

    if created:
        _say(quiet, "virtuoso: created %d item(s):" % len(created))
        for c in created:
            _say(quiet, "  + " + os.path.relpath(c, root))
    else:
        _say(quiet, "virtuoso: workspace already complete — nothing to do.")
    return created


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--mode", choices=["create", "detect"], default="create")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    preflight(a.root, a.mode, a.quiet)


if __name__ == "__main__":
    main()
