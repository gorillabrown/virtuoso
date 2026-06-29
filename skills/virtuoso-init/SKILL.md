---
name: virtuoso-init
description: >
  Initialize or repair the Virtuoso workspace for a project. Use when setting up the
  virtuoso plugin in a new project, when a governance skill reports a missing workspace,
  or when the user says "virtuoso init", "set up virtuoso", "create the roadmap workspace",
  or "initialize virtuoso". Creates a Virtuoso/ directory at the project root with the
  roadmap, sprint queue, lessons catalog, workflow reference, and the review/close-out/audit
  folders. Idempotent — only creates what is missing, never overwrites.
---

# Virtuoso Init

Bootstrap (or heal) the per-project `Virtuoso/` workspace that the governance skills
read and write.

**Run:**

    python "${CLAUDE_PLUGIN_ROOT}/scripts/virtuoso_preflight.py" --root . --mode create

Then report to the user what was created vs. what already existed (the script prints
this), and where the workspace lives. The workspace contains:

- `Roadmap.md` — the canonical roadmap (seed; flesh out via /roadmap-review)
- `sprint-queue.xlsx` — Dashboard + Catalog (from the bundled template; ships with a few
  clearly-labeled example rows that /roadmap-review replaces)
- `SpecRetro.Lessons_Learned.md` — running lessons catalog
- `WORKFLOW_REFERENCE.md` — index mapping legacy section numbers to skills
- `roadmap-reviews/` (+ `checkins/`), `Close-Outs/`, `audits/`

The script never overwrites existing files, so it is safe to re-run any time. If
`${CLAUDE_PLUGIN_ROOT}` is not available in the shell, the plugin's `scripts/` directory
holds `virtuoso_preflight.py` — run it from there with the same arguments.
