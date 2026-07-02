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

## Already have a roadmap? (adoption)

If the project **already maintains an established documentation tree** — a
`Project Documentation/` or `2. Project Documentation/` directory with a `1 governance` /
`2 operational` subtree and its own roadmap (under any name, e.g. `GoG_Roadmap.md`) — you
usually do **not** want a fresh scaffold. The governance skills detect this and run
`--mode adopt`, which lays down only a thin `Virtuoso/` control marker whose
`workspace-layout.json` **points at the existing roadmap**; nothing is moved or
duplicated and no parallel `Roadmap.md` is seeded. Prefer adoption for an established
project; reach for the create flow below only to (re)build a documentation tree.

Both `create` flows below are also adoption-aware: when a roadmap already exists anywhere
under the documentation root, the manifest points at it instead of seeding a new one.

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

- `Roadmap.md` — the canonical roadmap (seed; flesh out via /roadmap-review). If the
  project already has a roadmap under another name, the manifest points at that file
  instead and no seed is written.
- `sprint-catalog.csv` — the authoritative sprint catalog (header row only; seeded
  with rows by /roadmap-review from the active section of the roadmap). Every skill
  reads and writes this CSV — it is never generated from or read back from a
  spreadsheet.
- `sprint-queue.xlsx` (optional) — a human-facing report, not a workspace file this
  script seeds by default. If a project wants one, generate it from
  `sprint-catalog.csv` via `build_sprint_queue.py`; its Dashboard tab is meant to be
  driven by Power Query against the CSV and refreshed by opening the workbook in
  Excel — no skill reads it back or force-writes its cells.
- `SpecRetro.Lessons_Learned.md` — running lessons catalog
- `WORKFLOW_REFERENCE.md` — index mapping legacy section numbers to skills
- `roadmap-reviews/` (+ `checkins/`), `Close-Outs/`, `Issues/`
- `4 Outside Audits/` for external audit packages and reports

Running `create` on a project that was previously **adopted** (thin) rebuilds the full
documentation tree under the existing documentation root — non-destructively, adding only
the missing empty subdirs and seeds — and switches it from thin-adopt to full management.
If you only want the lightweight marker, let the governance skills adopt it instead.

The script never overwrites existing files, so it is safe to re-run any time. The path
comes from `~/.virtuoso/plugin-root`, a bridge file the plugin's session-start hook records
every session (skill bodies cannot read `${CLAUDE_PLUGIN_ROOT}`). If that file is missing,
create `Virtuoso/.virtuoso`, `Virtuoso/scripts/`, `Virtuoso/workspace-layout.json`, and the
chosen `Project Documentation/` tree by hand — the spreadsheet and scripts then populate on
the next session, when the hook runs preflight.
