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

    python "$(cat ~/.virtuoso/plugin-root 2>/dev/null)/scripts/virtuoso_preflight.py" --root . --mode create

Then report to the user what was created vs. what already existed (the script prints
this), and where the workspace lives. The workspace contains:

- `Roadmap.md` — the canonical roadmap (seed; flesh out via /roadmap-review)
- `sprint-queue.xlsx` — Dashboard + Catalog (from the bundled template; ships with a few
  clearly-labeled example rows that /roadmap-review replaces)
- `SpecRetro.Lessons_Learned.md` — running lessons catalog
- `WORKFLOW_REFERENCE.md` — index mapping legacy section numbers to skills
- `roadmap-reviews/` (+ `checkins/`), `Close-Outs/`, `audits/`

The script never overwrites existing files, so it is safe to re-run any time. The path
comes from `~/.virtuoso/plugin-root`, a bridge file the plugin's session-start hook records
every session (skill bodies cannot read `${CLAUDE_PLUGIN_ROOT}`). If that file is missing,
create the `Virtuoso/` workspace by hand (dirs `roadmap-reviews/`, `Close-Outs/`, `audits/`,
`scripts/`; a `.virtuoso` marker; seed `Roadmap.md` and `SpecRetro.Lessons_Learned.md`) — the
spreadsheet and scripts then populate on the next session, when the hook runs preflight.
