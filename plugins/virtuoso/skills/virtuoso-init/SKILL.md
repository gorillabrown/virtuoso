---
name: virtuoso-init
description: >
  Initialize or repair the Virtuoso workspace for a project. Use when setting up the
  virtuoso plugin in a new project, when a governance skill reports a missing workspace,
  or when the user says "virtuoso init", "set up virtuoso", "create the roadmap workspace",
  or "initialize virtuoso". Offers a layout choice, creates the selected documentation
  tree plus the Virtuoso plugin workspace, and never overwrites user content.
---

# Virtuoso Init

Bootstrap (or heal) the per-project Virtuoso workspace that the governance skills
read and write.

## Layout Choice

Before running the script, ask the user which layout they want:

1. **Plugin-only Virtuoso folder** — keep project documentation in the project root under
   `Project Documentation/`; `Virtuoso/` only holds plugin-managed files such as the marker,
   layout manifest, and vendored scripts. This is the default and lowest-risk option.
2. **Canonical Virtuoso layout** — move documentation into
   `Virtuoso/Project Documentation/`, with existing documentation migrated non-destructively
   when the destination is free.

If the user does not choose, use option 1.

**Run option 1:**

    python "$(cat ~/.virtuoso/plugin-root 2>/dev/null)/scripts/virtuoso_preflight.py" --root . --mode create --layout plugin-only

**Run option 2:**

    python "$(cat ~/.virtuoso/plugin-root 2>/dev/null)/scripts/virtuoso_preflight.py" --root . --mode create --layout canonical

Then report to the user what was created vs. what already existed (the script prints
this), which layout was selected, and where the workspace lives.

The script writes `Virtuoso/workspace-layout.json`; use that manifest as the source of
truth for paths in later skills. The documentation tree contains:

- `Roadmap.md` — the canonical roadmap (seed; flesh out via /roadmap-review)
- `sprint-queue.xlsx` — Dashboard + Catalog (from the bundled template; ships with a few
  clearly-labeled example rows that /roadmap-review replaces)
- `SpecRetro.Lessons_Learned.md` — running lessons catalog
- `WORKFLOW_REFERENCE.md` — index mapping legacy section numbers to skills
- `roadmap-reviews/` (+ `checkins/`), `Close-Outs/`, `Issues/`
- `4 Outside Audits/` for external audit packages and reports

The script never overwrites existing files, so it is safe to re-run any time. The path
comes from `~/.virtuoso/plugin-root`, a bridge file the plugin's session-start hook records
every session (skill bodies cannot read `${CLAUDE_PLUGIN_ROOT}`). If that file is missing,
create `Virtuoso/.virtuoso`, `Virtuoso/scripts/`, `Virtuoso/workspace-layout.json`, and the
chosen `Project Documentation/` tree by hand — the spreadsheet and scripts then populate on
the next session, when the hook runs preflight.
