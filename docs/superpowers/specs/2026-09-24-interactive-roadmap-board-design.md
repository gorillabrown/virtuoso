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
  - **Shown when the field has two or more distinct values:** Impl Status (each canonical
    status), Lane, Written (Stub / Full Spec), LOE, Phase, Stage, Deadline (has deadline /
    overdue / none), Dispatch-ready (passes the readiness rubric), Has comments. Any
    other register column with few distinct values also gets a slicer. On the reference
    board these are Lane, Impl Status, Written, LOE, Phase and Stage.
  - Values are ordered by policy where policy defines an order (lanes, status vocabulary,
    effort scale), and by first appearance otherwise.
  - Each slicer shows live counts that update as other slicers change (cross-filtering).
  - Every tile and chart re-renders from the filtered set.
  - Slicer state lives in the URL hash, so a filtered view can be bookmarked. A "Clear all"
    button resets it.
  - The Roadmap tab uses the same filter, with a toggle to link or unlink it.

### 3. Tab 2 — Roadmap (monday.com-style board)

This tab is modelled on the reference board: the *Gloves of Glory* main table in monday.com,
shared 2026-09-24. The page reproduces that board's layout from the Virtuoso register.
Nothing is synced with monday.

**Groups: one per pipeline state, not one per phase.** The reference board groups rows into
**Conveyor** and **Blocked / Gated**. The board groups by canonical status, in this order:

| Group | Canonical statuses | Rail | Default |
|---|---|---|---|
| In Flight | `in-flight` | amber | open |
| Conveyor | `queued` | blue | open |
| Blocked / Gated | `blocked` | red | open |
| Completed | `completed` | green | collapsed |
| Dissolved / Superseded | `dissolved`, `superseded` | grey | collapsed |

- **What each group shows.** A collapse chevron and the title in the group's colour. The
  column header row repeats under every group. Every row carries the group's coloured left
  rail. Empty groups are not shown. Items with status `unknown` go to Conveyor and get a
  warning mark.
- **Row order.** Rows are ordered by Seq and then by id. In the reference, the `1,000` and
  `2,000` values act as backlog tiers after the sequenced head (20, 25, 30).
- **Other groupings.** A **Group by** control regroups the rows by Phase, Lane or Stage, as
  monday's Group by does. Pipeline state stays the default.

**Columns.** Columns follow the reference board's order. A column appears only when the
register carries that field, and its header uses the register's own name ("Impl Status", not
"status").

| Column | Register field | Rendering |
|---|---|---|
| Item | `id` + `title` | `ID — Title`, cut short with an ellipsis; the full text shows on hover. Frozen on the left. |
| *(row actions)* | — | Comment bubble and copy button, in the slot where monday puts its updates icon (§4, §5) |
| Seq | `sequence` | Right-aligned, with thousands separator |
| Lane | `lane` | Full-cell colour label (ENGINE, GOV, …) |
| Impl Status | `status` | Full-cell colour label. The register's own spelling is shown; the colour comes from the canonical status. |
| Written | `written_status` | Full-cell label: Full Spec or Stub |
| Description | `description` | Plain text, cut short |
| Depends On | `prerequisites` | Plain text. Any token that matches an id on the board becomes a link that jumps to that row. |
| Sprint Code | `id` | Shown only when the register keeps the id apart from Item |
| Branch | `branch` | Monospace text |
| Repo Spec | `spec_link` | A link that opens the spec relative to the project root |
| Notes | `notes` | Plain text, cut short. The register's own provenance note, not the board's comments. |
| LOE | `effort` | Full-cell colour label, ordered by `roadmap.effortScale` (XS → XL) |
| Points | `extra["Points"]` | Number |
| Phase | `group` | Outlined chip, not a filled cell, as in the reference |
| Stage | `extra["Stage"]` | Plain text |

- **Unmapped columns.** Every other register column (anything the provider puts in
  `extra`) comes after the mapped ones, under the register's own header. The board never
  drops a column the register carries.
- **Colours.** Label columns (Lane, Impl Status, Written, LOE) fill the whole cell with
  white text, like monday's status columns.
  - Status colours follow the canonical status: queued blue, in-flight amber, blocked
    purple, completed green, dissolved and superseded grey. These match the reference, where
    Queued is blue and Blocked is purple.
  - Written: Full Spec blue, Stub purple.
  - Lane and LOE values take slots from a fixed palette. Each value's slot is derived from
    the value itself, so the same value keeps its colour across regenerations.
- **Group footer.** The reference board shows "battery" bars under Impl Status, Written and
  LOE. The board does the same: under each label column, a bar shows that group's mix of
  values, with count and percentage on hover. Under Points, the footer shows the group's
  total.
- **Toolbar.** The toolbar mirrors the reference: Search, Filter (the same filter model as
  the Dashboard slicers), Sort, Hide and Group by.
  - Hide sets which columns are visible, remembered per browser.
  - There is no New item or Person control, because the board never writes to the
    register.
- **Row checkboxes.** These are kept from the reference, but here they drive
  **Copy selected**: the names of the selected rows, one per line, for dispatching a batch.
- **Scrolling.** The group header row is sticky and the Item column is frozen. The table
  scrolls sideways inside its own frame, because the reference runs to about sixteen
  columns; the page itself never scrolls sideways.
- **At phone width**, each row becomes a card: `ID — Title`, then the status and Lane
  labels, then the other fields in a list.

**Reading the reference board's register.** The reference board's column names show four
mapping cases that the board, and its tests, must handle:

- **Item holds both id and title.** The reference's Item column holds `ID — Title` and has
  no separate title column. The default aliases take `id` from Sprint Code, leave Item in
  `extra`, and leave `title` empty. When `title` is empty and an `extra` value begins with
  the id and a dash, the board uses that value as the display name and as the copy text.
- **Lane and Stage are separate columns.** An exact header match wins over an alias, so
  Lane maps to `lane` and Stage falls to `extra`. That is the right result, and the tests
  pin it, because `stage` is also an alias of `lane`.
- **LOE and Points both look like effort.** Both are aliases of `effort`. LOE wins because it
  comes first in the alias list; Points falls to `extra` and renders as its own column.
- **Two headers have no default alias.** "Impl Status" and "Written" match nothing by
  default. Add `impl status` and `written` to `DEFAULT_ALIASES` so a board like this one reads
  without any `fieldMappings`.

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
  - copy-text format, including the Item-only register case;
  - a fixture register with the reference board's headers (Item, Seq, Lane, Impl Status,
    Written, Description, Depends On, Sprint Code, Branch, Repo Spec, Notes, LOE, Points,
    Phase, Stage) that renders every column in order, with nothing dropped;
  - an HTML escape test with a hostile title and comment.

## Delivery slices

1. **Board role and generator.** Registry role, default path, and create-on-first-review in
   D.7. The Roadmap tab as specified in §3: pipeline-state groups, the reference column set,
   label colours, footer bars and the copy button. The two new default aliases.
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
- **Committing the board.** Should `roadmap-board.html` be committed or gitignored? Proposed:
  commit the sidecar, which is the durable record, and let the project decide for the
  HTML. The scaffolded `.gitignore` entry stays commented out.
