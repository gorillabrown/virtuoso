# Interactive Roadmap Board — Design

**Status:** proposed (roadmap) · **Date:** 2026-09-24 · **Schema:** unchanged (v2) — one new role

## Problem Statement

The planning cockpit (`tools/roadmap_visualizer`, regenerated at `roadmap-review` D.7) is a
read-only report. It sits in `Virtuoso/reports/planning-cockpit.html`, where a person rarely
looks. It is only as fresh as the last roadmap review. Its three views (Cockpit, Conveyor,
Dependencies) are health readouts, not a working surface.

A person working a Virtuoso project needs something else: one page, always current, where
they can:

- see where the project stands at a glance and slice it by what they care about;
- scan the whole roadmap as a board, grouped and colour-coded, the way a monday.com board
  reads;
- leave a note against a row for the next review to pick up;
- grab a row's name in one click to start a dispatch or to reference the work in whichever
  LLM they are using.

## Goals

- **One page in the project root**: an always-current, self-contained, interactive HTML file.
- **Created on the first `roadmap-review`** if it is not already there, and regenerated
  whenever the register changes after that.
- **Three tabs**: Dashboard, Roadmap, and a third view (see Open Questions).
- **Roadmap tab laid out as a monday.com-style board**, with a comment box and a copy
  button on every row.
- **Dashboard with smart slicers**: complete/incomplete, lane, group/phase and the other
  fields the data actually carries.
- Offline and dependency-free: it opens from `file://` with no server, no CDN and no build
  step.

## Non-Goals

- Not a second source of truth. The board never edits the work register or the roadmap.
  Status, order and scope still change only through the ceremonies.
- Not a sync to monday.com. "monday.com-style" describes the layout, not an integration.
- No hosted service, accounts or multi-user state.

## Design

### 1. Location, lifecycle, freshness

- **New registry role `board`.** The default path is `<project root>/roadmap-board.html`. The
  role is registered like every other artifact, so a project can move or rename the file
  (the principle is "always the registry, never a convention"). `allowedWriters` lists the
  ceremonies below. The existing `_refuse_protected_output` guard still applies.
- **Creation.** `roadmap-review` D.7 checks the `board` role. If the role is missing, D.7
  registers it at the default path. If the file is missing, D.7 generates it and reports
  "board created" in the D.8 summary.
- **Always up to date.** The board is regenerated after every write to the register or the
  roadmap: `roadmap-review` D.7, `pointer-closeout`, `record-completion`, and `next-pointer`
  when it changes the head. Preflight also compares the board's embedded snapshot time with
  the provider's source time and prints `board: stale` as an advisory. It never blocks.
- **Staleness is visible.** The page header shows the snapshot time and provider. When that
  time is older than the source's last change as of generation, the header shows an age
  badge, the same way the cockpit labels snapshot-backed reads today.
- **Successor to the cockpit.** One generator and one `PlanningModel` feed both outputs.
  `planning-cockpit.html` keeps being written for one release, with a banner pointing to the
  board, and is then retired. The cockpit's views move into the board: pace, buffer and
  drift go to the Dashboard; group, lane and prerequisites become Roadmap columns.

### 2. Tab 1 — Dashboard

- **KPI tiles**: total, complete, incomplete, % complete, dispatch-buffer ready vs. target,
  blocked, and pace against the nearest deadline. All come from the existing `kpi.compute`
  and `summarize_health` output, with provenance on hover.
- **Charts**: status by lane (stacked bar), completion by group/phase (progress bars), and
  completions over time (trailing weeks). Hand-rolled inline SVG, with no chart library.
- **Smart slicers.** Slicers are built from the data, not hard-coded:
  - **Always shown:** Complete / Incomplete. This is a two-way toggle over the canonical
    status set, so a project's own vocabulary (`statusMappings`) still collapses correctly.
  - **Shown when the field has two or more distinct values:** Status (each canonical
    status), Lane, Group/phase, Effort, Deadline (has deadline / overdue / none),
    Dispatch-ready (passes the readiness rubric), Has comments.
  - Values are ordered by policy where policy defines an order (lanes, status vocabulary,
    effort scale), and by first appearance otherwise.
  - Each slicer shows live counts that update as other slicers change (cross-filtering).
  - Every tile and chart re-renders from the filtered set.
  - Slicer state lives in the URL hash, so a filtered view can be bookmarked. A "Clear all"
    button resets it.
  - The Roadmap tab uses the same filter, with a toggle to link or unlink it.

### 3. Tab 2 — Roadmap (monday.com-style board)

- **Groups** are collapsible sections, one per group/phase in roadmap order, falling back to
  lane when a project has no groups. Each group has a coloured left rail, a header showing
  the item count, and a footer "battery" bar showing the status mix across the group.
- **Rows** are one per work item. The columns are:
  - Item: the id in monospace, then the title.
  - Status: a full-cell coloured pill, using a fixed colour per canonical status.
  - Lane.
  - Effort.
  - Prerequisites: shown as chips; a chip jumps to its row.
  - Deadline: turns red when overdue.
  - Spec: a link.
  - Comment.
  - Copy.
- **Board behaviour.** The header row is sticky. The item column is frozen while the other
  columns scroll sideways. Columns are sortable within a group, and there is a search box.
  Completed items sit in a collapsed "Done" group at the bottom, as monday does.
- **At phone width**, each row becomes a card: status pill first, then title, with the other
  fields in a list.

### 4. Row comments

- **Editing.** Each row's comment control opens an inline text box. A comment saves on blur
  or Ctrl/Cmd+Enter. The row then shows a comment count badge and the first line as a
  tooltip.
- **Where comments live.** A static file cannot write to disk, so comments have two layers:
  1. **Browser storage** (`localStorage`, keyed by project root + item id). Saves are
     immediate. Every read and write is wrapped in try/catch, and the page still renders
     if storage is unavailable.
  2. **A sidecar file, `roadmap-board.comments.json`,** registered alongside the `board`
     role. It is the durable, Virtuoso-readable copy. The page writes it in one of two
     ways:
     - **"Save comments"** writes it directly through the File System Access API where the
       browser supports it (Chromium).
     - **"Export comments"** downloads it everywhere else, for the person to drop into the
       project root.
- **Surviving regeneration.** The generator reads the sidecar and embeds its comments in the
  new page. The page merges them with browser storage (newest timestamp wins per item), so a
  comment outlives regeneration.
- **The loop closes.** `roadmap-review` B.3 reads open board comments next to open
  `findings`. The review addresses, adopts or answers each one. Answered comments are marked
  resolved in the sidecar by the review, and the page shows them greyed out.

### 5. Copy button

- **What it copies:** the row's work name, `<ID> — <Title>` (for example, `SK-01 — Deadline
  support`). This is the handle the ceremonies and dispatch prompts already use.
- **Variant:** Shift-click copies a dispatch-ready reference instead: the name plus the spec
  path and branch, when known.
- **Clipboard mechanics.** The button uses `navigator.clipboard.writeText`, falling back to a
  hidden-textarea `execCommand("copy")` for `file://` contexts that block the async API. It
  confirms with a transient "Copied" state.

### 6. Rendering and safety

- **One file.** The page stays self-contained: inline CSS and JS, and the model embedded as
  JSON with `</` escaped, as `render.py` does today.
- **Theming.** Colours are CSS custom properties with a dark-mode variant. The layout is
  checked at 360 px width with no horizontal page scroll.
- **Escaping.** All item text is inserted through `textContent`, never `innerHTML`, because
  titles and comments are user-authored.
- **Tests** extend the visualizer suite:
  - the `board` role is registered and created on the first review;
  - no protected overwrite;
  - regeneration preserves the sidecar;
  - slicer derivation (a field with a single value gets no slicer);
  - copy-text format;
  - an HTML escape test with a hostile title and comment.

## Delivery slices

1. **Board role and generator.** Registry role, default path, create-on-first-review in D.7,
   Roadmap tab with groups, status pills and the copy button.
2. **Dashboard.** KPI tiles, charts, derived and cross-filtering slicers, URL-hash state.
3. **Comments.** Browser storage, sidecar save/export, merge on regeneration, and the
   `roadmap-review` B.3 intake.
4. **Freshness.** Regeneration from `pointer-closeout`, `record-completion` and
   `next-pointer`; the preflight `board: stale` advisory; the cockpit deprecation banner.

## Open Questions

- **Third tab.** The request names three tabs but describes two (Dashboard, Roadmap). The
  proposed default is **Health**: the cockpit's drift findings, dependency graph and
  provenance, so nothing the cockpit shows today is lost. Alternatives are a **Comments**
  inbox (every open comment in one list) or a **Timeline** (deadlines and pace).
- **The reference board.** The monday.com example that was meant to be attached did not come
  through. Section 3 follows monday's standard main-table layout; adjust it against the
  example when it is re-shared.
- **Committing the board.** Should `roadmap-board.html` be committed or gitignored? Proposed:
  commit the sidecar, which is the durable record, and let the project decide for the
  HTML. The scaffolded `.gitignore` entry stays commented out.
