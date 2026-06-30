---
name: roadmap-review
description: |
  MANUAL INVOCATION ONLY. Heavyweight roadmap recalibration ceremony
  (~30-45 min). ONLY runs when the user types "/roadmap-review",
  "run roadmap review", or "perform roadmap review". DO NOT
  auto-trigger on conversational mentions of roadmaps, planning,
  sprints, phases, or specs — those belong to other skills. When
  invoked: establishes or updates the project's roadmap document,
  migrates completed work to the Completed Work Summary table (full
  content moves to a dated archive file), assesses progress and scope
  discipline, replans macro/micro steps, sequences remaining work as
  a conveyor belt under a Phase → Stage hierarchy, replenishes the
  eager-spec buffer to 5 dispatch-ready full specs (mandatory) via
  write-spec — each spec must pass the Dispatch-Readiness Rubric so
  a lower-model CLI implementer cannot fail — reviews lessons
  learned, and produces a phase brief.
---

# Roadmap Review

## Preflight — workspace check (run first)

This skill operates on the project's Virtuoso workspace. Before anything else, bring the project under management non-destructively:

    python "$(cat ~/.virtuoso/plugin-root 2>/dev/null)/scripts/virtuoso_preflight.py" --root . --mode adopt

`adopt` never moves or duplicates anything. Read the `virtuoso-status:` line it prints and branch:

- `ready` — a `Virtuoso/` workspace already exists (it was healed if needed); continue.
- `adopted roadmap=<path>` — the project already had an established documentation tree (e.g. `Project Documentation/` or `2. Project Documentation/`) with its own roadmap, so a thin `Virtuoso/` control marker was written that points at that existing roadmap. Tell the user it was adopted in place — nothing was moved or duplicated — then continue.
- `none` — there is no workspace and no documentation tree to adopt (treat a missing `~/.virtuoso/plugin-root` the same way). Stop this skill and route the user to `/virtuoso-init`, which asks whether to use the plugin-only or the canonical `Virtuoso/Project Documentation/` layout.

**Workspace paths.** Read `Virtuoso/workspace-layout.json` first and use its `paths` map. For an adopted project, `paths.roadmap` and `paths.sprintQueue` point at the project's own existing files under whatever names they use (e.g. `GoG_Roadmap.md`). Key entries include `roadmap`, `sprintQueue`, `closeOuts`, `issues`, `outsideAudits`, `reference`, and `scripts`. If the manifest is missing, run `/virtuoso-init`; only fall back to legacy flat `Virtuoso/` paths for older projects.

**Integrity gate.** This ceremony rewrites the roadmap in place, so before migrating or rewriting anything, verify the resolved roadmap is sound (substitute the `paths.roadmap` value from the manifest):

    python "$(cat ~/.virtuoso/plugin-root 2>/dev/null)/scripts/virtuoso_preflight.py" --check-roadmap "<paths.roadmap>"

Read the `roadmap-integrity:` line. On `fail` (null bytes, non-UTF-8, or missing — exit 3), STOP and report the corruption to the user; do not migrate or rewrite a corrupt roadmap. On `warn` (empty or unusually large — exit 2), surface it and confirm with the user before proceeding. On `ok`, continue.


Heavyweight, periodic recalibration of an entire project. The ceremony
you run when you need to know — with confidence — where the project
has been, where it's going, and what to dispatch next.

## When to use

Run this skill when:
- A phase has just closed
- The roadmap feels stale, drifted, or inaccurate
- You're prepping for a leadership or stakeholder checkpoint
- You're returning to a project after a gap and need to resync
- You suspect scope creep and want to verify

Do NOT use this skill for:
- Routine sprint planning (use sprint-planning instead)
- Single-spec authoring (use write-spec instead)
- Weekly status updates (use stakeholder-update or /roadmap-status)

## Invocation

Manual only. The user must explicitly type one of:
- `/roadmap-review`
- "run roadmap review"
- "perform roadmap review"

If you (Claude) infer this skill from context without an explicit
invocation, STOP. Confirm with the user before proceeding.

## Glossary

These terms are used precisely throughout this skill.

- **Sprint** — A discrete unit of work (1-5 days, S-M t-shirt) with
  clear acceptance criteria. The atomic dispatch unit. Identified
  by a code like `SK-XX`.
- **Phase** — A coherent shippable chunk containing multiple
  sprints, with a clear theme, goal, and exit criteria.
- **Stage** — Optional sub-grouping within a phase.
- **Stub** — A placeholder sprint card with just code, title, and
  optionally a one-line gist. Items beyond the eager-spec buffer of
  5 sit as stubs.
- **Full spec** — A sprint card with all 7 structural fields PLUS
  implementation detail. Lives inline in the roadmap.
- **Dispatch-ready full spec** — A full spec that has passed the
  Dispatch-Readiness Rubric below. Every code reference is verified.
  Every decision is made. No "TBD" remains. The CLI implementer can
  execute without judgment calls.
- **Dispatch** — The act of sending a sprint to the implementer.
  The implementer reads the dispatch-ready full spec inline in the
  roadmap and runs it.
- **Scope** — What's included in / excluded from a sprint.
- **Pointer** — A textual reference to where detail lives.

### The progression of a sprint's content density

```
Stub  →  Full spec  →  Dispatch-ready  →  Close-out
(TBD)    (drafted)      (rubric passed)    (post-completion)
                        ▲                  │
                        │                  ▼
                roadmap-review        One-line entry in
                Phase D.3 applies     Completed Work Summary;
                the rubric, then      full spec migrates to a
                saves the spec        dated archive file
```

This skill produces **dispatch-ready full specs** in the roadmap
document, plus parallel entries in `sprint-queue.xlsx` Catalog tab.

**Note on the legacy term "skeleton":** the section heading
`## Active & Remaining Sprint Skeletons` is preserved for backward
compatibility. In this skill's vocabulary, items in that section are
either **stubs** or **dispatch-ready full specs**.

## Dispatch-Readiness Rubric

Every full spec authored by Phase D.3 must pass these 10 checks
before being saved inline in the roadmap. The rubric exists because
the CLI agent that implements the spec is assumed to be a
lower-capability model than Cowork (which authors the spec). Every
decision, every code reference, every test, and every constant must
be resolved upstream so the implementer cannot fail.

The same rubric is duplicated in `/next-pointer` as a just-in-time
re-verification gate. Intentional self-containment for global skills.

### Rubric R1 — Edit Sites
For every `file:line` reference in the spec's Implementation Detail:
- [ ] The file exists at that path.
- [ ] The line number is current (grep / read to verify; line
      numbers can shift after upstream sprints land).
- [ ] The code at that line matches the spec's intent (the function
      name / constant / structure mentioned in the spec is actually
      there).
- [ ] If line numbers have shifted, **update them inline in the
      spec** before saving.

### Rubric R2 — Test Names
For every test mentioned in Done-when or Implementation Detail:
- [ ] The test name is a full path:
      `tests/test_module.py::test_function` (or test class form).
- [ ] For new tests: the target file is explicit; the test function
      name is explicit; the assertion content is explicit
      ("assert f(X) == Y", not "verify it works").
- [ ] For existing tests being modified: the current assertion is
      quoted in the spec; the new assertion is quoted in the spec.
- [ ] If any test reference is vague, **enrich the spec inline**.

### Rubric R3 — Constants
For every named constant in the spec:
- [ ] The constant exists in the codebase (grep to confirm).
- [ ] Current value is documented in the spec.
- [ ] Target value (or removal directive) is explicit.
- [ ] Constant's file location is named.
- [ ] If any constant is unverified, **grep and add the verified
      file:line + current value to the spec**.

### Rubric R4 — Done-When Criteria
For every Done-when bullet:
- [ ] The criterion is **mechanically verifiable** — a shell
      command, a test assertion, or a file-existence check that
      returns true/false unambiguously.
- [ ] No criterion requires human judgment ("looks right", "is
      reasonable", "matches design intent" — all forbidden).
- [ ] Each criterion's verification command is in the spec (e.g.,
      `grep -c '<constant>' .` returns 0).
- [ ] If a criterion is vague, **rewrite it inline to be
      mechanical**.

### Rubric R5 — Branch + Commit Hygiene
- [ ] Branch name is explicit (e.g., `sk-fu12-e-wave-a`).
- [ ] Source branch is explicit ("from clean main").
- [ ] Commit hygiene rules referenced (CL-WF-01 clean-tree gate;
      no `git add .` / `-A`; no destructive flags).
- [ ] If missing, **add to the spec**.

### Rubric R6 — Calibration Cadence (if applicable)
For any sprint touching calibration:
- [ ] Quick-cal config explicit: N value, seed count, deterministic
      flag.
- [ ] Full-cal escalation rule explicit: threshold (e.g., ">3pp on
      any primary metric"), reference SRL (e.g., SRL-113).
- [ ] Band check explicit: bands being measured, current values,
      targets.
- [ ] Pre-authorized halt conditions explicit (when to STOP and
      escalate).
- [ ] If missing, **enrich the spec**.

### Rubric R7 — Edge Cases + Failure Modes
- [ ] "If X fails, do Y" is explicit for each known failure mode.
- [ ] Rollback plan stated (revert command, branch deletion, etc.).
- [ ] Retry ceiling explicit (3 attempts max per wave is the
      default).
- [ ] If gaps exist, **enrich the spec**.

### Rubric R8 — Prerequisites Verified
- [ ] Every prerequisite is `Completed` in the Catalog OR
      `Dissolved`/superseded with a documented disposition.
- [ ] If a prerequisite is still `Queued` / `In Flight` /
      `Blocked`, the spec must encode "wait for prereq X" or
      sequencing must be revised in Phase C.

### Rubric R9 — No Deferred Decisions
- [ ] Search the spec for: "TBD", "to be decided", "decide later",
      "ask Cowork", "consult", "verify with user".
- [ ] If any of these appear, the decision must be resolved before
      saving. If Cowork can resolve via investigation
      (grep / DB query / file read), do it and update the spec. If
      it requires user judgment, AskUserQuestion.

### Rubric R10 — Source Citations
- [ ] The Source line links to specific close-outs, audits, or
      decision docs.
- [ ] Citations include exact section anchors (e.g., "FAS-1 §9
      Decision 10") where applicable.
- [ ] If missing, **enrich the spec**.

## Operating principles

1. **Iterative.** This skill doesn't need to produce a perfect plan
   on the first run. Each invocation makes the roadmap more
   accurate.
2. **Roadmap document is canonical.** All other docs are inputs;
   the project's roadmap document is the single source of truth and
   the home of dispatch-ready full specs for the next 5 sprints.
   Default filename `Roadmap.md`. Companion: `sprint-queue.xlsx`.
3. **Archive-forward discipline.** The active roadmap holds
   dispatch-ready full specs for the next 5 sprints, stubs for
   sprints beyond position 5, plus a one-line entry per completed
   sprint in the Completed Work Summary table. Full content migrates
   to a dated archive file at sprint close-out.
4. **Active section is uncompleted-only.** Hard invariant.
5. **Conveyor belt sequencing.** Dependency-first → risk-first
   tiebreaker → eat-the-frog second tiebreaker. The Catalog tab
   mirrors via the `Seq` column.
6. **Eager-spec buffer is mandatory at 5.** Each run replenishes to
   5 dispatch-ready full specs.
7. **Dispatch-Readiness Rubric is non-negotiable.** A spec that
   fails the rubric is not saved as a full spec. It's either
   enriched until it passes, or left as a stub and flagged as a
   buffer gap.
8. **Cowork is the highest model in the pipeline.** All judgment,
   investigation, and decision-making for spec authoring happens
   here. The CLI implementer follows the recipe; it does not
   improvise.
9. **Standing Rules consolidate inheritable lessons.** A
   `### Standing Rules All Skeletons Inherit` section in the
   roadmap captures rules every sprint inherits.
10. **Forward visibility minimum.** Always carry full specs or
    stubs for at least 3 sprints ahead of dispatch.
11. **Length ceiling.** Active roadmap targets ~2,000 lines. When
    crossed, snapshot to a dated archive; trim stubs >3 sprints out.
12. **Checkpoint between phases.** User confirms each phase.
13. **AskUserQuestion only.** 2+ alternatives, one tagged
    [RECOMMENDED], escape hatch.
14. **Orchestrate, don't reimplement.** Where existing skills
    handle a sub-task well (`write-spec`, `roadmap-update`, the
    xlsx skill), invoke them.

## Inputs

1. The roadmap document (creates if missing)
2. All `.md` files in the project root and subfolders (close-outs,
   retros, audit decisions, post-mortems, SRLs)
3. Git log of the roadmap document if version-controlled
4. All existing close-out files (e.g., `CloseOut.SK-XX.YYYY-MM-DD.md`)
5. Any existing dated archive files
6. `sprint-queue.xlsx` if it exists — Dashboard + Catalog tabs. Use
   the xlsx skill (anthropic-skills:xlsx) for read/write mechanics.
7. **Project codebase** — required for Phase D.3 rubric verification
   (grep, code reads, schema queries).

## Outputs

Saved to a `roadmap-reviews/` subfolder in the project:
- `YYYY-MM-DD-audit.md` — Phase A diff
- `YYYY-MM-DD-assessment.md` — Phase B opinion
- `YYYY-MM-DD-plan.md` — Phase C decomposition tree
- `YYYY-MM-DD-lessons-applied.md` — Phase D lessons-learned review
- `YYYY-MM-DD-phase-brief.md` — Phase D upcoming-phase brief

Plus, updated in place:
- The roadmap document (dispatch-ready full specs in buffer; stubs
  beyond; Completed Work Summary table grown; Standing Rules updated)
- `sprint-queue.xlsx` Catalog tab
- A new dated archive file if the length ceiling was crossed

---

## Phase 0 — INITIATE (only if needed)

### 0.1 Locate the roadmap document
If `Roadmap.md` exists in the project root, use it. Otherwise look
for a project-named variant (e.g., `gog_roadmap.md`). If ambiguous,
AskUserQuestion.

Persist as `roadmap_doc: <filename>` in frontmatter.

### 0.2 Check for a finish line
If a finish-line target is missing, AskUserQuestion to establish
it. DO NOT proceed without one.

### 0.3 Locate or create sprint-queue.xlsx
If missing, AskUserQuestion to create from the canonical template.
Persist as `sprint_queue_doc: <filename>`.

### 0.4 Migrate legacy structure
Detect and migrate older structures to the canonical form. Show
migration plan via AskUserQuestion before applying.

---

## Phase A — AUDIT (≈10 min)

Goal: enforce archive-forward discipline. Move completed sprints to
the Completed Work Summary table; migrate full content to the
current dated archive file. Mirror changes in the Catalog tab.

### A.1 Read everything
Inventory every sprint and its claimed status.

### A.2 Build a candidate completion/archive list
Classify each sprint as Likely complete / Likely dissolved /
Definitely live based on signals.

### A.3 Confirm with the user
Batched 5 at a time, AskUserQuestion.

### A.4 Apply changes
For each sprint migrated:
1. Add a one-line entry to `## Completed Work Summary`.
2. Move the full content (entire `#### SK-XX — Title` block
   including amendments) to the current dated archive file.
3. Remove the full content from the active roadmap.
4. Update the Catalog row: flip Implementation Status, clear Seq,
   populate Date Completed and Close-Out File.
5. For dissolved/superseded sprints, add to `## Disposition of
   Superseded Branches`.

### A.5 Length-ceiling check
If active roadmap >~2,000 lines, snapshot + trim.

### A.6 Checkpoint
Show the diff. AskUserQuestion: approve / roll back / pause.

---

## Phase B — ASSESS (≈10 min)

### B.1 Compute % work remaining
Sum LOE; divide; express as %.

### B.2 Compute pace
4-week trailing items/week. Compare to required. On / Behind /
Ahead pace.

### B.3 Score scope discipline
Forward / Sideways / Backward deltas vs. prior review. Score =
forward / (forward + sideways + backward). >80% healthy.

### B.4 Render the assessment
Write `YYYY-MM-DD-assessment.md`.

### B.5 Checkpoint
AskUserQuestion.

---

## Phase C — PLAN (≈15 min)

### C.1 Derive macro steps
3-7 large outcome blocks.

### C.2 Group macros into phases
2-5 phases.

### C.3 Decompose into micro-steps (sprint stubs)
1-5 days each. Each becomes a `#### SK-XX — [Title]` heading.

### C.4 Sequence the conveyor belt
Dependency → risk → eat-the-frog.

### C.5 Render the plan
Write `YYYY-MM-DD-plan.md`. Update the roadmap's Active section and
the Catalog tab.

### C.6 Checkpoint
AskUserQuestion.

---

## Phase D — DISPATCH (≈25 min)

Goal: write dispatch-ready full specs for the next 5 sprints
(mandatory replenishment), validate against lessons learned,
integrate into the canonical files, and brief the upcoming phase.

### D.1 Identify the head of the conveyor belt
First 5 sprints in `## Active & Remaining Sprint Skeletons`, in
conveyor-belt order. May span phase boundaries.

### D.2 Determine spec count (mandatory replenishment to 5)
Eager-spec buffer target = 5. Replenish each run.

**Compute the count:**
1. Walk the conveyor belt from the head.
2. Count sprints with dispatch-ready full specs already in place.
3. **New full specs to write = 5 − already_dispatch_ready_count.**
4. Target the next sprints in conveyor-belt order that currently
   lack full content (i.e., are stubs).

**Edge cases:**
- If active section has <5 uncompleted sprints, write specs for
  all of them.
- Phase boundaries are NOT a stopping condition.
- If a hard dependency or unresolved decision blocks writing a
  spec mid-buffer, stop at the block, flag in D.6, note the buffer
  will fall short of 5.

### D.3 Write the dispatch-ready full specs

For each sprint in scope:

**D.3.1 Draft via write-spec.**
Invoke `write-spec` with both structural inputs (the 7 fields) and
implementation-detail inputs (edit sites, tests, constants, branch,
commit hygiene, cal cadence). Source from upstream close-outs,
constitutional docs, the Standing Rules section, dated archives.

**D.3.2 Apply the Dispatch-Readiness Rubric (R1-R10).**
Walk the rubric — see the section earlier in this skill — against
the draft spec. For each item:
- **PASS** → check and move on.
- **CLOSABLE GAP** → resolve via investigation:

  | Gap type | How to close |
  |---|---|
  | Stale `file:line` | Grep + read; update line number inline. |
  | Missing test name | Read test file; insert specific name + assertion. |
  | Unverified constant | Grep; document current value + file location. |
  | Vague Done-when | Rewrite as mechanical check (shell command / test assertion). |
  | Missing branch | Apply `<sprint-id>-wave-<N>` convention. |
  | Missing cal cadence | Look at precedent close-outs; apply project defaults. |
  | Missing rollback | Standard pattern: revert wave commit, delete branch, re-baseline. |
  | Missing edge case | Identify common failure modes; add "if X, do Y". |
  | Missing source citation | Search and link. |

- **STRUCTURAL GAP** → AskUserQuestion or escalate to user. Do not
  invent decisions.

**D.3.3 Re-audit.**
Walk the rubric again. Max 2 enrichment passes. If a sprint still
fails after 2 passes, STOP at that sprint — the spec is NOT saved;
flag as a buffer gap in D.6; continue the buffer count from the
next dispatchable sprint.

**D.3.4 Save the dispatch-ready spec.**
Only when all 10 rubric items pass, save the full spec inline in
the roadmap document at the correct Phase → Stage → Sprint
position (D.5 handles placement mechanics).

### D.4 Lessons-learned review

**D.4.1 Gather lessons.** Scan project for `retro*.md`,
`*lesson*.md`, `*post-mortem*.md`, `SRL-*.md`, `CL-*.md`,
`*close-out*.md`, `CloseOut.*.md`, `*decision*.md`, `Audit*.md`.

**D.4.2 Build the checklist.** Deduped, grouped by theme.

**D.4.3 Update the Standing Rules section.**
- Present + current → verify wording
- Missing → add with source ID
- Superseded → update or remove

**D.4.4 Review newly written specs.** For each spec from D.3, walk
the lessons checklist. Update inline if a lesson applies and isn't
embodied.

**D.4.5 Review existing full specs.** Walk same checklist.
AskUserQuestion for misalignments.

**D.4.6 Render the lessons-applied report.** Write
`YYYY-MM-DD-lessons-applied.md`.

### D.5 Integrate specs into the roadmap and sprint-queue.xlsx

**D.5.1 Resolve filenames.**

**D.5.2 Place full specs in the roadmap.**
At correct Phase → Stage → Sprint position, replacing prior stubs.

**D.5.3 Full spec placement format (canonical).**

```
#### SK-XX — Sprint Title

- **What:** ...
- **Why:** ...
- **Prerequisites:** ...
- **Done when:**
    1. ...
- **Effort:** ...
- **Roster:** ...
- **Source:** ...

##### Implementation detail
- **Edit sites:** `engine_core.py:968-970`, ...
- **Tests:** `test_identity.py::test_per_fighter_instinct_invariant`
- **Constants:** ...
- **Branch:** `sk-xx-wave-a` from clean main
- **Commit hygiene:** explicit-stage; no destructive flags
- **Cal cadence:** ...
- **Edge cases:** if X fails, do Y; rollback: ...
```

Mid-dispatch amendments append as `##### Mid-Dispatch Amendment —
YYYY-MM-DD` sub-sections.

**D.5.4 Update sprint-queue.xlsx (Catalog tab).**

Sprint data lives on the **`DATA.sprint-catalog`** sheet (Excel table
`sprint_catalog`). Column layout (A–T):
A=Priority\*, B=Seq, C=Sprint Code, D=Phase, E=Stage, F=Title, G=LOE,
H=Dependencies, I=Implementation Status, J=Written Status, K=Branch,
L=Date Started, M=Date Completed, N=Close-Out File, O=Description, P=Notes,
Q=Done?\*, R=PhaseRank\*, S=SizeRank\*, T=SortKey\*.

`\*` = formula-driven computed columns — do **not** hand-write them (the Excel
table auto-fills them; `Priority` auto-ranks the conveyor belt from `SortKey`).
`Description` (O) and `Notes` (P) are plain text columns — write the one-liner and
any notes directly in the Catalog row.

For each newly written full spec, set on the `DATA.sprint-catalog` row:
- `Seq`: conveyor-belt position
- `Sprint Code`, `Title`, `Phase`, `Stage`, `LOE`, `Dependencies`: from the spec
- `Implementation Status`: `Queued`
- `Written Status`: `Full Spec`
- `Branch`: from spec

Write the one-line description in `Description` (O) and any notes in `Notes` (P).
Status/LOE vocabularies live on the `Variables` sheet. After
editing the Catalog headlessly (without Excel), run
`python <scripts>/recalc.py <sprintQueue>` to refresh KPIs, resolving both values from
`Virtuoso/workspace-layout.json`.

**D.5.5 Reconcile.**
Roadmap active section and Catalog tab match; positions 1-5 are
`Full Spec`; positions 6+ are `Stub`; Completed Work Summary has
one-line entries only; Standing Rules reflects the checklist.

### D.6 Write the phase brief
Write `YYYY-MM-DD-phase-brief.md`:
- Phase name(s) and goal(s)
- Sprints in the buffer of 5, in sequence
- Implementation-detail highlights
- Rubric pass rate (10/10 for each spec in the buffer)
- Lessons-applied summary
- Dependencies into and out of the buffer
- Exit criteria
- Estimated buffer duration
- Top 1-2 risks
- **Buffer gaps:** any sprints that couldn't be authored as
  dispatch-ready (rubric failed after 2 enrichment passes); list
  with the rubric items that blocked

### D.7 Final summary to user
Present:
- Roadmap changes
- Catalog changes
- Pace + scope discipline read
- Phase brief in chat
- Buffer status: N dispatch-ready full specs (out of 5 target)
- Lessons-applied highlights

---

## Roadmap document template

```markdown
# [Project Name] — Project Roadmap

**Last updated:** [Session N (YYYY-MM-DD)] — [one-line state]

## How This Document Is Maintained
[Archive-forward policy]

## Finish Line — Target
[Description, graduated tiers if applicable.]

## Completed Work Summary
| Sprint | Session | Result | Close-Out |
|--------|---------|--------|-----------|

**Disposition of superseded branches:**
- `[SK-XX]` — [reason]. Branch preserved at commit `[hash]`.

## Active & Remaining Sprint Skeletons

### Standing Rules All Skeletons Inherit
- **[ID — short title].** [Rule.]

### Phase 1 — [Phase Name]

#### SK-XX — Sprint Title    *(position 1 — dispatch-ready)*
- **What:** ...
- **Why:** ...
- **Prerequisites:** ...
- **Done when:**
    1. ...
- **Effort:** ...
- **Roster:** ...
- **Source:** ...

##### Implementation detail
- **Edit sites:** ...
- **Tests:** ...
- **Constants:** ...
- **Branch:** ...
- **Commit hygiene:** ...
- **Cal cadence:** ...
- **Edge cases:** ...

#### SK-XX — Sprint Title    *(position 6 — stub)*
[One-line gist.]

## Non-Blocking Follow-Up Queue
## Notes

<!-- Frontmatter:
loe_unit: t-shirt
last_review: YYYY-MM-DD
finish_line: ""
roadmap_doc: Roadmap.md
sprint_queue_doc: sprint-queue.xlsx
-->
```

## Sprint queue spreadsheet structure

The workbook has **three sheets**:

### Dashboard
- **Project Info** (B4–B8).
- **Pipeline Status** (B11–B18): Total, Completed, Blocked, Queued, In Flight,
  Dissolved, Superseded, % Complete (by count). `Completed*` matches dated variants
  (e.g. `Completed 2026-06-29`).
- **Effort & Progress** (B21–B26): LOE remaining, LOE completed, Total LOE,
  **% Complete (by LOE)**, Sprints remaining, Avg sprint size. The "Effort by LOE"
  helper (D10:H20) defines LOE points: XS 0.5, XS-S 0.75, S 1, S-M 2, M 3, M-L 5,
  L 8, XL 20.
- **Next Up — Active Queue** (A28–F41): auto-ranked from the Catalog `Priority`
  column (XLOOKUP).
- **Status Distribution** doughnut chart.
- Buffer health, full-specs-queued, and phase progress are **not** Dashboard cells —
  compute them from the Catalog (see /roadmap-status and /next-pointer).

### DATA.sprint-catalog
Excel Table `sprint_catalog`, 20 columns A–T (layout in D.5.4). Five are
formula-driven computed columns (Priority, Done?, PhaseRank, SizeRank, SortKey).

### Variables
Lookup tables — Status vocabulary, Phase→PhaseRank, LOE→size weight. Editing these
re-ranks the conveyor belt via the `Priority` column.

All Dashboard scalar KPIs are formula-driven and recompute live in Excel. For a
headless refresh, run `python <scripts>/recalc.py <sprintQueue>`, resolving both values
from `Virtuoso/workspace-layout.json`.

---

## Question protocol reminder

Every clarifying question uses AskUserQuestion with at least 2
alternatives, exactly one tagged [RECOMMENDED], and an escape hatch
on consequential decisions. Never ask open-ended free-text questions
during the run.
