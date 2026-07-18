---
name: roadmap-status
description: |
  MANUAL INVOCATION ONLY. Lightweight roadmap pulse check (~5-10 min).
  ONLY runs when the user types "/roadmap-status", "run roadmap
  status", or "check roadmap status". DO NOT auto-trigger on
  conversational mentions of status, progress, or "where do things
  stand" — this is a deliberate ritual, not a casual status answer.
  Reads the current state, computes KPIs directly from
  sprint-catalog.csv (catalog-direct — no cached Dashboard to trust
  or distrust), enforces archive-forward discipline by migrating any
  shipped sprints lingering in active skeletons to the Completed Work
  Summary table (and keeps the catalog CSV in sync), reports a fast
  Axios-style briefing with bracketed sprint IDs and LEDE-first
  bullets, and optionally executes small (under 5 min) recommended edits.
  Lightweight sibling of /roadmap-review — use that when full
  recalibration is needed.
---

# Roadmap Status

## Preflight — workspace check (run first)

This skill operates on the project's Virtuoso workspace. Before anything else, bring the project under management non-destructively:

    python "$(cat ~/.virtuoso/plugin-root 2>/dev/null)/scripts/virtuoso_preflight.py" --root . --mode adopt

`adopt` never moves or duplicates anything. Read the `virtuoso-status:` line it prints and branch:

- `ready` — a `Virtuoso/` workspace already exists (it was healed if needed); continue.
- `adopted roadmap=<path>` — the project already had an established documentation tree (e.g. `Project Documentation/` or `2. Project Documentation/`) with its own roadmap, so a thin `Virtuoso/` control marker was written that points at that existing roadmap. Tell the user it was adopted in place — nothing was moved or duplicated — then continue.
- `none` — there is no workspace and no documentation tree to adopt (treat a missing `~/.virtuoso/plugin-root` the same way). Stop this skill and route the user to `/virtuoso-init`, which builds the plugin-only `Project Documentation/` layout (the only layout the workspace scaffolder supports).

**Governance authority — read `Virtuoso.Governance.Readme.md` first.** The project-root `Virtuoso.Governance.Readme.md` is the single source of truth for where every governance document lives (roadmap, sprint catalog, lessons, close-outs, issues, review artifacts). Resolve each document you need through its registry and **defer to the paths it lists**, whatever layout the project uses (e.g. `docs/governance/ROADMAP.md`, `2. Project Documentation/…`, or the plugin default). `Virtuoso/workspace-layout.json` is the machine-readable mirror of the same paths. **Never create a parallel or competing document for a role the registry already lists** — open and edit the registered file in place. If the registry and the files on disk diverge (a registered path is an empty stub while the project's real document lives elsewhere), fix the **registry** — repoint it to the existing document and tell the user — do **not** seed or fork a rival. If `Virtuoso.Governance.Readme.md` is missing, run `/virtuoso-init` to generate it by registering the project's existing governance documents (it seeds a new file only for a role that genuinely has none).


A fast pulse on where the project stands and what's next, in
Axios-style bullets: bracketed sprint ID, then a LEDE that says the
news, then optional sub-bullets with supporting detail. ~5-10
minutes. No replanning, no spec authoring. Cleanup duty: enforces
archive-forward discipline by migrating any shipped sprints that
linger in `## Active & Remaining Sprint Skeletons`, and keeps
`sprint-catalog.csv` in sync with the canonical roadmap document.

## When to use

- Weekly or biweekly recurring check-in
- Before a stakeholder conversation where you want a fresh read
- When something feels off and you want a sanity check
- Between phases to spot what's drifting

Do NOT use this for:
- Full replanning (use /roadmap-review)
- Skeleton or full-spec authoring (use /roadmap-review)
- Adding new initiatives (use roadmap-update)
- Sprint scoping (use sprint-planning)

## Invocation

Manual only. The user must explicitly type one of:
- `/roadmap-status`
- "run roadmap status"
- "check roadmap status"

If no roadmap document exists, STOP and recommend running
/roadmap-review to establish one first.

## Glossary

These terms are used precisely throughout this skill.

- **Sprint** — A discrete unit of work (1-5 days, S-M t-shirt) with
  clear acceptance criteria.
- **Phase** — A coherent shippable chunk containing multiple
  sprints, with a clear theme, goal, and exit criteria.
- **Stage** — Optional sub-grouping within a phase.
- **Stub** — A placeholder sprint card with just code, title, and
  optionally a one-line gist. Lives inline in the roadmap; the
  Catalog row marks Written Status as `Stub` (or `None`).
- **Full spec** — A sprint card with all 7 structural fields PLUS
  implementation detail. Lives inline in the roadmap; Catalog row
  marks Written Status as `Full Spec`.
- **Dispatch** — The act of sending a sprint to the implementer.
  The implementer reads the full spec inline in the roadmap and
  runs.
- **Scope** — What's included in / excluded from a sprint.
- **Pointer** — A textual reference to where detail lives.

### The progression of a sprint's content density

```
Stub  →  Full spec  →  Close-out
(TBD)    (in roadmap)  (post-completion)
```

This skill **reads** the roadmap and `sprint-catalog.csv`. It does
not write full specs or stubs. Its only write actions are small
cleanup migrations.

**Note on the legacy term "skeleton":** the section heading
`## Active & Remaining Sprint Skeletons` is preserved for backward
compatibility.

## Operating principles

1. **LEDE first, detail second.** Each bullet leads with
   `[SPRINT-ID]` in brackets, then a one-to-two-sentence bolded
   LEDE.
2. **Plain language, always.** Plain English, complete sentences,
   no fragments, no bare acronyms.
3. **Bulleted and fast.** Whole briefing readable in under 60
   seconds at the LEDE level.
4. **Active section is uncompleted-only.** Cleanup duty: scan
   `## Active & Remaining Sprint Skeletons` for any sprint that has
   actually shipped. Stragglers get auto-recommended for migration
   in Phase 2 — always <5 min edits.
5. **sprint-catalog.csv stays in sync.** When a sprint moves out of
   active, its catalog row is updated (Implementation Status flipped
   to `Completed` / `Dissolved`, Seq cleared, Date Completed
   populated, Close-Out File pointer recorded). Both views reflect
   the same reality after Phase 2.
6. **sprint-catalog.csv is the canonical KPI source.** All KPIs are
   computed directly (catalog-direct) from the CSV — there is no
   cached Dashboard to trust or distrust. If a companion
   `sprint-queue.xlsx` report exists, it is a generated, human-facing
   view only; never read it back, and never treat its Dashboard tab
   as authoritative (its Power Query cache only refreshes when a
   human opens it in Excel, so it can silently go stale/contradictory —
   the CSV numbers are always the ground truth).
7. **Read, don't restructure.** Beyond cleanup, this skill never
   re-sequences, generates new specs, or changes phase boundaries.
8. **Two-phase hard ceiling.** Phase 2 only executes <5 min edits.
   Anything bigger gets handed off to /roadmap-review.
9. **AskUserQuestion for all confirmations.** 2+ alternatives, one
   tagged [RECOMMENDED], escape hatch.

## Writing rules for bullets

These rules apply to every bullet in **Recently completed** and
**Coming up**. Apply them WHILE writing.

### Rule 1 — Bracket the ID, then bold the LEDE
```
- [SPRINT-ID] **One- or two-sentence LEDE that says the news.**
  - Supporting detail (optional).
  - *Issue: [plain-language sentence, if any].*
```

### Rule 2 — The LEDE answers "what + why"
Pick the 1-2 angles most useful: what was supposed to happen / what
happened / why it matters / zoom in or out.

### Rule 3 — Lead with news, not process
❌ "[SK-FU12-DIAGNOSTIC] **Investigated a failing calibration result
and discovered the original explanation was wrong; wrote up a
diagnostic protocol.**"

✓ "[SK-FU12-DIAGNOSTIC] **The previous calibration failure was
misdiagnosed — the deeper investigation produced a standing
diagnostic protocol now in force for every future calibration
failure.**"

### Rule 4 — Use complete sentences, never fragments
❌ "[SK-FU12-RESOLUTION] **B6 hybrid revert; Sub gate cleared at
20.90%.**"

✓ "[SK-FU12-RESOLUTION] **The broken submission-finish gate is
fixed.** Reverting to a clean baseline cleared it at 20.9%, inside
the target band; the rest of the calibration cluster is unblocked."

### Rule 5 — Translate or paraphrase acronyms in the LEDE
❌ "[SK-FLASH-SUB-SYM] **Added Sub-INT flash mult; ref overshot at
70, retuned to 60.**"

✓ "[SK-FLASH-SUB-SYM] **Submission specialists now get a finish
bonus comparable to strikers, finally evening out the two finish
channels.** An initial multiplier value overshot the target band
and was tuned down."

### Rule 6 — Coming-up bullets follow the same format
❌ "[SK-FU12-E] **Wire Instinct + RT into submission finish-threat
bonus.**"

✓ "[SK-FU12-E] **Wires the Instinct and Risk Tolerance attributes
into the submission finish-bonus calculation, so high-instinct,
high-risk-tolerance fighters get a bigger reward for committed
submission attempts.**"
  - *Adaptation: validation calibration runs with two random seeds
    instead of one to reduce noise variance.*

### The "stranger test"
Before saving, ask of every LEDE: would a smart colleague who has
never seen this project understand the news from this LEDE alone?
If no, rewrite.

---

## Inputs

1. The project's roadmap document — specifically `## Active &
   Remaining Sprint Skeletons` and `## Completed Work Summary`
2. `sprint-catalog.csv` — the single source of truth for sprint
   data. Used for:
   - **KPI computation** — buffer health, % complete, phase
     progress, totals, and category counts, all computed
     catalog-direct. See Phase 1.3a.
   - **Row-level reads** needed by the cleanup scan, sync check, and
     window-specific signals (Date Completed in window, recently
     added rows, etc.) — see Phase 1.3b.
   - Read/write it as a plain CSV (standard library / pandas-style
     row parsing) — this is not a spreadsheet mechanic.
3. Most recent file in `roadmap-reviews/` — baseline
4. Most recent file in `roadmap-reviews/checkins/` — baseline
5. Recent git log (last 7 days)
6. Close-out files (`CloseOut.<SPRINT>.<DATE>.md`)

## Outputs

1. Axios-style bulleted briefing in chat
2. Saved file: `roadmap-reviews/checkins/YYYY-MM-DD-status.md`
3. (If Phase 2 runs) Direct edits to the roadmap document AND
   sprint-catalog.csv — most commonly, migrating a shipped sprint out
   of active

---

## Phase 1 — READ & REPORT

### 1.1 Determine the window
"Recent" = the longer of:
- Time since the last status or review file
- Last 7 days

### 1.2 Identify the current phase
Look at `## Active & Remaining Sprint Skeletons` for a `(current)`
marker. If ambiguous, AskUserQuestion.

### 1.3 Compute KPIs from sprint-catalog.csv + read window signals

**1.3a Compute KPIs catalog-direct from sprint-catalog.csv.**
Read the CSV (columns: Seq, Sprint Code, Phase, Stage, Title, LOE,
Dependencies, Implementation Status, Written Status, Branch, Date
Started, Date Completed, Close-Out File, Description, Notes) and
compute:

| KPI | How |
|---|---|
| Total sprints | row count |
| Completed | rows where Implementation Status matches `Completed*` |
| Blocked | rows where Implementation Status = `Blocked` |
| Queued | rows where Implementation Status = `Queued` |
| In Flight | rows where Implementation Status = `In Flight` |
| Dissolved | rows where Implementation Status = `Dissolved` |
| Superseded | rows where Implementation Status = `Superseded` |
| % Complete (by count) | Completed ÷ (Total − Dissolved − Superseded) |
| LOE remaining (points) | sum LOE points for rows not done (not Completed/Dissolved/Superseded) |
| LOE completed (points) | sum LOE points for Completed rows |
| Total LOE (points, excl. dissolved/superseded) | remaining + completed |
| **% Complete (by LOE)** — primary progress metric | completed points ÷ total points |
| Sprints remaining | Blocked + Queued + In Flight |
| Avg sprint size (points) | total points ÷ (Total − Dissolved − Superseded) |
| **Full specs queued** | rows where Implementation Status = `Queued` AND Written Status = `Full Spec` |
| **Buffer health** | from full-specs-queued count: ≥5 Healthy, ≥3 Running low, ≥1 Critical, else Empty |
| **Phase progress** | rows where Phase = the current phase (total / completed / remaining) |

Status vocabulary includes **`Superseded`** and **`Pivot`**, and a completed sprint
may read `Completed` or `Completed <date>` (match `Completed*`). LOE sizes are
XS/XS-S/S/S-M/M/M-L/L/XL (points 0.5/0.75/1/2/3/5/8/20).

There is no cache to refresh — every figure is derived from the CSV as it stands
right now. If a companion `sprint-queue.xlsx` exists and its Dashboard tab shows
different numbers, that's a stale Power Query cache (it only recomputes when a
human opens the workbook in Excel) — note the discrepancy if asked, but the
figures computed here from the CSV are authoritative.

**1.3b Read window-specific signals from sprint-catalog.csv.**
The CSV captures temporal information via Date Started and Date
Completed. Read:
- Sprints with Date Completed within the window → recently shipped
- Sprints added (new rows) during the window — flag sideways adds
- Sprints at the head of active (low Seq, Implementation Status =
  Queued / In Flight) that have been there from before the window
  → potentially stuck
- Pace: completion count in window vs recent average

**1.3c Active section cleanup scan (mandatory).**
Walk every sprint in active skeletons and check for completion
signals:
- `CloseOut.<SPRINT>.<DATE>.md` file exists
- Status marker `[COMPLETED ...]`
- Closed PRs / merge commits closing the sprint
- A deliverable the sprint was supposed to produce now exists

Any sprint with completion signals but still in active is a
**straggler**. Auto-recommendation in 1.4.

**1.3d Sync check between roadmap and sprint-catalog.csv.**
- Sprints in roadmap's active section but missing from the CSV →
  flag for sync
- CSV rows with Implementation Status = `Queued` but absent
  from the roadmap's active section → flag for sync (likely stale)
- CSV `Seq` order doesn't match roadmap's active sequence →
  flag for sync

Mismatches generate auto-recommendations.

### 1.4 Compose the briefing
Use this exact structure. Every Recently-completed and Coming-up
bullet must obey the writing rules above.

```
## Roadmap Status — YYYY-MM-DD

### Roadmap health
- [Plain-language sentence about whether sprints are moving.]
- [Plain-language sentence about anything stuck.]
- [Plain-language sentence about anything sideways.]
- [Plain-language sentence about pace.]
- [Plain-language sentence about buffer health — computed from sprint-catalog.csv
  (full specs queued = Implementation Status `Queued` ∧ Written Status `Full Spec`;
  ≥5 Healthy / ≥3 Running low / ≥1 Critical / else Empty); mention N full specs of 5
  if not "Healthy".]
- [If stragglers: plain-language sentence noting N sprints look
  complete and need migration.]
- [If sync mismatches: plain-language sentence noting roadmap and
  Catalog drifted out of sync.]

### Recently completed (since YYYY-MM-DD)
- [SPRINT-ID] **LEDE.**
  - Supporting detail.
  - *Issue: ...*

### Coming up (next 2-4 sprints)
- [SPRINT-ID] **LEDE.**
  - *Adaptation: ...*

### Where we stand
- **Current phase ([Phase Name]):** X% of work remaining.
  *(computed from sprint-catalog.csv: completed-in-phase ÷ sprints-in-phase; X = 1 − that ratio)*
- **Finish line:** Y% of work remaining by LOE; N sprints remaining.
  *(computed catalog-direct from sprint-catalog.csv: Y = 1 − % Complete by LOE)*

### Health read
- **[On Track / Watch Closely / Concerns]** — one plain-language
  sentence explaining why.

### Recommendations
- [SPRINT-ID] **One-sentence specific action, <5 min to execute.**
```

**Section rules:**
- Recently-completed: from sprints migrated to Completed Work
  Summary during the window.
- Coming-up: from the head of active skeletons going forward.
- Stragglers become auto-recommendations:
  `- [SPRINT-ID] **Migrate from active skeletons to Completed Work
  Summary in both the roadmap document and sprint-catalog.csv.**`
- Sync mismatches become auto-recommendations:
  `- [SPRINT-ID] **Reconcile sprint-catalog.csv with the
  roadmap — [specific drift].**`
- If zero recommendations: `- _No recommendations — status quo
  holds._`

**Pre-save verification (mandatory):** stranger test on every LEDE.

**Escalation rule:** If a recommendation would require
restructuring, do NOT include it. Instead, add:

```
### Larger changes detected
- [SPRINT-ID] **One-sentence LEDE explaining why /roadmap-review
  is recommended.**
```

### 1.5 Save the briefing
Save to `roadmap-reviews/checkins/YYYY-MM-DD-status.md`.

### 1.6 Present and pause
Show in chat. AskUserQuestion:
- (A) Approve all — execute Phase 2 [RECOMMENDED if recs exist]
- (B) Approve some — let me pick which
- (C) Skip Phase 2 — read only
- (D) The read is wrong — let me explain

If no recommendations exist, skip to (C) and close.

---

## Phase 2 — ACT (only if Phase 1 produced approved recommendations)

### 2.1 Execute the approved recommendations
For each approved recommendation:

- **Straggler migration** (most common):
  1. In the roadmap document, add a one-line entry to
     `## Completed Work Summary`.
  2. Remove the full skeleton/spec block from
     `## Active & Remaining Sprint Skeletons`.
  3. In `sprint-catalog.csv`: flip Implementation Status
     from `Queued`/`In Flight` to `Completed` (or `Dissolved`),
     clear `Seq`, populate `Date Completed`, populate `Close-Out
     File`.

  All three edits count as one logical migration; <5 min. KPIs are
  computed catalog-direct on the next read — there is no cache to
  refresh.

- **Sync reconciliation** (catalog drift):
  - CSV row for already-completed sprint → flip Implementation
    Status to `Completed`, clear Seq.
  - Missing row for an active skeleton → add row with appropriate
    Implementation Status, Written Status, Seq.
  - Order mismatch → renumber `Seq` column to match roadmap's
    active sequence.

- **Status updates** → edit the roadmap; mirror in the CSV if it
  changes a column value.

- **Dependency or context notes** → edit roadmap or relevant
  close-out file. The CSV's Notes column may also receive a short note.

- **Risk flags** → append to roadmap `## Notes` or relevant Phase
  section header.

Read/write `sprint-catalog.csv` as a plain CSV — this is a text file,
not a spreadsheet mechanic. If a companion `sprint-queue.xlsx` report
exists, do not write to it here; it is regenerated (via
`/roadmap-review` or `build_sprint_queue.py`) from the CSV, not edited
directly.

**Hard ceiling enforcement:** if any single recommendation balloons
past >5 min of editing or affects >2 sprints, STOP. Roll back
partial changes for that recommendation and tell the user to run
/roadmap-review for that one. Others can still proceed.

### 2.2 Confirm and close
Show the diff in BOTH the roadmap doc and sprint-catalog.csv.
AskUserQuestion:
- (A) Approve — close [RECOMMENDED]
- (B) Roll back

---

## Question protocol reminder

Every clarifying question uses AskUserQuestion with at least 2
alternatives, one tagged [RECOMMENDED], and an escape hatch. Never
ask open-ended free-text questions during the run.
