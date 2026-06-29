---
name: roadmap-status
description: |
  MANUAL INVOCATION ONLY. Lightweight roadmap pulse check (~5-10 min).
  ONLY runs when the user types "/roadmap-status", "run roadmap
  status", or "check roadmap status". DO NOT auto-trigger on
  conversational mentions of status, progress, or "where do things
  stand" — this is a deliberate ritual, not a casual status answer.
  Reads the current state, pulls KPIs from the sprint-queue.xlsx
  Dashboard tab, enforces archive-forward discipline by migrating any
  shipped sprints lingering in active skeletons to the Completed Work
  Summary table (and keeps the Catalog tab in sync), reports a fast
  Axios-style briefing with bracketed sprint IDs and LEDE-first
  bullets, and optionally executes small (under 5 min) recommended edits.
  Lightweight sibling of /roadmap-review — use that when full
  recalibration is needed.
---

# Roadmap Status

## Preflight — workspace check (run first)

This skill operates on the project's `Virtuoso/` workspace. Before anything else, ensure it exists and is complete:

    python "$(cat ~/.virtuoso/plugin-root 2>/dev/null)/scripts/virtuoso_preflight.py" --root . --mode create

The script is idempotent — it never overwrites existing files. The bundled-script path comes from `~/.virtuoso/plugin-root`, a bridge file the plugin's session-start hook records every session (skill bodies cannot read `${CLAUDE_PLUGIN_ROOT}`, only hooks can). If that file is missing or the command fails, run `/virtuoso-init`, or create the workspace by hand: a `Virtuoso/` directory containing `roadmap-reviews/` (and `roadmap-reviews/checkins/`), `Close-Outs/`, `audits/`, `scripts/`, a `.virtuoso` marker, and seed `Roadmap.md` + `SpecRetro.Lessons_Learned.md`. If the workspace was just created, tell the user where it lives, then continue.

**Workspace paths.** Canonical files live under `Virtuoso/`: `Virtuoso/Roadmap.md`, `Virtuoso/sprint-queue.xlsx`, bundled scripts in `Virtuoso/scripts/`, review outputs in `Virtuoso/roadmap-reviews/` (check-ins in `Virtuoso/roadmap-reviews/checkins/`), close-outs in `Virtuoso/Close-Outs/`, audits in `Virtuoso/audits/`. Wherever this skill names `Roadmap.md`, `sprint-queue.xlsx`, or `roadmap-reviews/` without a directory, resolve them under `Virtuoso/` first (falling back to the project root for legacy projects).


A fast pulse on where the project stands and what's next, in
Axios-style bullets: bracketed sprint ID, then a LEDE that says the
news, then optional sub-bullets with supporting detail. ~5-10
minutes. No replanning, no spec authoring. Cleanup duty: enforces
archive-forward discipline by migrating any shipped sprints that
linger in `## Active & Remaining Sprint Skeletons`, and keeps the
`sprint-queue.xlsx` Catalog tab in sync with the canonical roadmap
document.

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

This skill **reads** the roadmap and the `sprint-queue.xlsx`
Dashboard + Catalog tabs. It does not write full specs or stubs.
Its only write actions are small cleanup migrations.

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
5. **sprint-queue.xlsx stays in sync.** When a sprint moves out of
   active, its Catalog row is updated (Implementation Status flipped
   to `Completed` / `Dissolved`, Seq cleared, Date Completed
   populated, Close-Out File pointer recorded). Both views reflect
   the same reality after Phase 2.
6. **Dashboard is the canonical KPI source.** Pull pre-computed KPIs
   from the Dashboard tab (load with `data_only=True`). Catalog
   reads are only for things Dashboard can't capture (temporal
   window signals, sync reconciliation).
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
2. `sprint-queue.xlsx`:
   - **Dashboard tab** for pre-computed KPIs (read with
     `data_only=True`) — primary source for buffer health, %
     complete, phase progress, totals, and category counts. See
     Phase 1.3a for the cell map.
   - **Catalog tab** for row-level reads needed by the cleanup
     scan, sync check, and window-specific signals (Date Completed
     in window, recently added rows, etc.) — see Phase 1.3b.
   - Use the xlsx skill (anthropic-skills:xlsx) for mechanics.
3. Most recent file in `roadmap-reviews/` — baseline
4. Most recent file in `roadmap-reviews/checkins/` — baseline
5. Recent git log (last 7 days)
6. Close-out files (`CloseOut.<SPRINT>.<DATE>.md`)

## Outputs

1. Axios-style bulleted briefing in chat
2. Saved file: `roadmap-reviews/checkins/YYYY-MM-DD-status.md`
3. (If Phase 2 runs) Direct edits to the roadmap document AND the
   Catalog tab — most commonly, migrating a shipped sprint out of
   active

---

## Phase 1 — READ & REPORT

### 1.1 Determine the window
"Recent" = the longer of:
- Time since the last status or review file
- Last 7 days

### 1.2 Identify the current phase
Look at `## Active & Remaining Sprint Skeletons` for a `(current)`
marker. If ambiguous, AskUserQuestion.

### 1.3 Pull KPIs from Dashboard + read window signals

**1.3a Read pre-computed KPIs from the Dashboard tab.**
Use the xlsx skill and load with `data_only=True` to get cached
values. Read these cells:

| Cell | KPI |
|---|---|
| B11 | Total sprints |
| B12 | Completed |
| B13 | In Flight |
| B14 | Queued |
| B15 | Blocked |
| B16 | Dissolved |
| B17 | % Complete (by count) |
| B20 | Sprints remaining (uncompleted, undissolved) |
| B21 | LOE remaining (points) |
| B22 | LOE completed (points) |
| B23 | Total LOE (points, excl. dissolved) |
| B24 | **% Complete (by LOE)** — primary progress metric |
| B25 | Avg sprint size (LOE points) |
| B29 | Full specs queued |
| B32 | **Buffer health** flag (Healthy / Running low / Critical / Empty) |
| B35 | Sprints in current phase |
| B36 | Completed in current phase |
| B37 | Remaining in current phase |
| B38 | % phase complete |

Prefer these cached values over recomputing from Catalog rows. The
Dashboard is recalculated at the end of every /roadmap-review and
at the end of /roadmap-status Phase 2.

If Dashboard cells return stale or missing values (e.g., file
hasn't been recalced after manual edits), fall back to computing
from Catalog and flag the staleness as a recommendation (run
recalc).

**1.3b Read window-specific signals from the Catalog tab.**
The Dashboard doesn't capture temporal information; the Catalog
does (via Date Started, Date Completed). Read:
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

**1.3d Sync check between roadmap and sprint-queue.xlsx Catalog.**
- Sprints in roadmap's active section but missing from Catalog →
  flag for sync
- Catalog rows with Implementation Status = `Queued` but absent
  from the roadmap's active section → flag for sync (likely stale)
- Catalog `Seq` order doesn't match roadmap's active sequence →
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
- [Plain-language sentence about buffer health — sourced from
  Dashboard B32; mention N full specs of 5 if buffer is not
  "Healthy".]
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
  *(sourced from Dashboard B38; X = 1 − B38)*
- **Finish line:** Y% of work remaining by LOE; N sprints remaining.
  *(sourced from Dashboard B24 and B20; Y = 1 − B24)*

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
  Summary in both the roadmap document and the sprint-queue.xlsx
  Catalog tab.**`
- Sync mismatches become auto-recommendations:
  `- [SPRINT-ID] **Reconcile sprint-queue.xlsx Catalog with the
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
  3. In `sprint-queue.xlsx` Catalog tab: flip Implementation Status
     from `Queued`/`In Flight` to `Completed` (or `Dissolved`),
     clear `Seq`, populate `Date Completed`, populate `Close-Out
     File`.
  4. Run `python Virtuoso/scripts/recalc.py Virtuoso/sprint-queue.xlsx` to refresh
     Dashboard KPIs.

  All four edits count as one logical migration; <5 min.

- **Sync reconciliation** (Catalog drift):
  - Catalog row for already-completed sprint → flip Implementation
    Status to `Completed`, clear Seq.
  - Missing row for an active skeleton → add row with appropriate
    Implementation Status, Written Status, Seq.
  - Order mismatch → renumber `Seq` column to match roadmap's
    active sequence.
  - Recalc after.

- **Status updates** → edit the roadmap; mirror in Catalog if it
  changes a column value.

- **Dependency or context notes** → edit roadmap or relevant
  close-out file. Catalog Notes may also receive a short note.

- **Risk flags** → append to roadmap `## Notes` or relevant Phase
  section header.

Use the xlsx skill (anthropic-skills:xlsx) for all Catalog tab
read/write mechanics.

**Hard ceiling enforcement:** if any single recommendation balloons
past >5 min of editing or affects >2 sprints, STOP. Roll back
partial changes for that recommendation and tell the user to run
/roadmap-review for that one. Others can still proceed.

### 2.2 Confirm and close
Show the diff in BOTH the roadmap doc and Catalog tab.
AskUserQuestion:
- (A) Approve — close [RECOMMENDED]
- (B) Roll back

---

## Question protocol reminder

Every clarifying question uses AskUserQuestion with at least 2
alternatives, one tagged [RECOMMENDED], and an escape hatch. Never
ask open-ended free-text questions during the run.
