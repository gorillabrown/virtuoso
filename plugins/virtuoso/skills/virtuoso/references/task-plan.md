Serves `virtuoso` Phase 2: the task-row format field by field, the task tiers, a worked plan, and the commands that open and extend the time log.

# Phase 2 — Task Plan Detail

### The five effort levels

| Level | Thinking Budget | Behavior |
|-------|----------------|----------|
| **low** | Minimal | Pattern-match from trained knowledge. Answer from memory, don't work through it. |
| **medium** | Moderate | Meaningful reasoning within capacity. Handles majority of standard tasks. |
| **high** | Substantial | Traces complex logic, considers multiple approaches, backtracks when needed. |
| **xhigh** | Deep | More deliberation than high, short of max: long traces across several modules. |
| **max** | Full available | Reasons as extensively as context allows. Slowest, most expensive, highest quality. |

### Task format

Every task line follows this format: `□ N. owner-label: Task description [tier] {effort} ‹model› @kind  M min (basis)`

- **Task tier** in square brackets: `[mechanical]`, `[bounded]`, or `[cross-cutting]`.
  The tier describes the *task*, not the capability of whoever runs it; a host maps a tier
  to whatever model or agent it has available.
- **Effort level** in curly braces, on every row: `{low}`, `{medium}`, `{high}`,
  `{xhigh}` or `{max}`. A task the specification leaves blank takes its tier's default
  (mechanical→low, bounded→medium, cross-cutting→high), and the row prints it.
- **Model** in angle quotes: the alias that the plugin's `references/model-tiers.md` gives
  the owner agent's tier (the table's Agents column names each agent's tier). A row with
  no owner agent yet shows its tier's alias. Nothing depends on the host honouring
  `model` or `effort`: a host that reads neither still runs the plan, and the row says
  what the planner intended.
- **Kind** after an `@`, optional: a name for a row that recurs across dispatches
  (`@merge-slot`, `@fix-round`, `@gate-3-calibration`). A recurring row is priced from its
  kind's own history, so reuse a name `timing --kinds` already lists rather than coin a
  near-duplicate. Names are normalized to lowercase words joined by hyphens.
- **Prediction** last: the row's predicted working minutes and their basis, `38 min (median
  of 6 runs)` or `90 min (estimated)`. `timing --open` prices every row when the task list
  is first listed. It uses the median of at least 3 measured rows of the same kind, else
  of the same tier and effort, else the row's own `estimate`, labelled `estimated`. Only
  rows that ran to `done` count. A prediction is fixed once its row is listed, so the
  first listing's total never moves. A run's own finished rows price the rows added
  after them, and every later dispatch. Never type a prediction in yourself, and never
  label a guess as measured.
- **Task #1 is always `Zeus: Load spec, build plan, assign owners [cross-cutting]`.** Non-negotiable.
  This represents Phases 1–3 combined. Task #1 is marked ✓ only after the lead has:
  1. Read and understood the full dispatch spec (Phase 1)
  2. Built the numbered task plan (Phase 2)
  3. Assigned parent-owned tasks and child-worker candidates (Phase 3)
  4. Recorded the repository starting point when the spec requires one
  5. For a governed dispatch, printed the conflict check, and for a held plan, recorded
     the entry `in-flight`
  6. Printed the final assignment table
  Task #1 is the parent thread's setup work. Everything after Task #1 is either
  executed by the parent or delegated to child workers under this same dispatch plan.
- Every subsequent task starts with `unassigned:` as a placeholder — Phase 3 replaces
  these with owner labels.
- The dispatch's declared effort level is the default. Task-level annotations override it.

### Task tiers

Annotate each task with the **lowest tier that can carry it without sacrificing accuracy**.
A tier is a property of the task, not a ranking of hosts, products, or models. The host
maps a tier onto whatever agents or models it actually has.

**mechanical** — deterministic steps with a known correct answer: running a test suite,
formatting a file, updating a version number, committing. Speed and reliability, not
reasoning depth.

**bounded** — single-domain work requiring judgment inside one scope: writing a function,
tuning a constant, fixing a bug in one module, updating documentation to match code.
Domain knowledge, but no cross-cutting awareness required.

**cross-cutting** — work touching multiple modules, requiring an understanding of
interactions between subsystems, or involving architectural decisions. Root-cause analysis
across files, interpreting measurements, resolving conflicting requirements.

### Blast-radius override — the three cases

The rule's paragraph is in SKILL.md Phase 2. The three cases where cheapness is the wrong
axis:

- **An output that becomes a baseline.** A figure that later work is measured against
  is load-bearing even when producing it is a single command. A baseline capture
  assigned to the cheapest tier returned figures that could not be reproduced under any
  invocation, and an entire merge gate had to be re-derived. Baselines go to a tier that
  can notice its own output is wrong.
- **An interpretation wearing a mechanical label.** "Re-run the tool and report" sizes
  as mechanical, but is reasoning-dense whenever the deliverable is an *interpretation*
  rather than an *artifact*. Classify by the shape of the output, not by the phrasing
  of the task.
- **Cross-module work at the top effort tier.** These systematically trigger critical
  review findings. Pre-allocate a **fix round as its own planned task**, so it appears
  in the plan as a step rather than arriving as an overrun.

### Example (Phase 2 output — tasks enumerated, agents not yet assigned)

```
## Task Plan — Effort: Medium | Override: tasks #6, #8 → High
□ 1. Zeus: Load spec, build plan, assign owners                [cross-cutting] {high} ‹model›  20 min (median of 5 runs)
□ 2. unassigned: Modify calc_defense_effectiveness() — WEIGHT 3.0→2.0  [bounded] {medium} ‹model›  25 min (estimated)
□ 3. unassigned: Update constants.toml default                          [mechanical] {low} ‹model›  6 min (median of 9 runs)
□ 4. unassigned: Run fast test suite — all shards pass                  [mechanical] {low} ‹model› @fast-suite  14 min (median of 4 runs)
□ 5. unassigned: Run the full verification sweep                           [mechanical] {low} ‹model›
□ 6. unassigned: Interpret cal results + decide if tuning needed        [cross-cutting] {max} ‹model›
□ 7. unassigned: Generate profiler snapshot with pathway metrics        [mechanical] {low} ‹model›
□ 8. unassigned: Analyze profiler — does freed space flow to both?      [cross-cutting] {max} ‹model›
□ 9. unassigned: Update CLAUDE.md with constants and cal results        [bounded] {medium} ‹model›
□ 10. unassigned: Commit, merge to main, push                          [mechanical] {low} ‹model›
```

(Rows 5–10 carry their predictions the same way; they are elided here.)

Note: Tasks #6 and #8 override to `{max}` because interpreting calibration results
and analyzing profiler output across subsystems are genuinely hard analytical problems
where getting it wrong has real downstream consequences. All other tasks use their
task-tier defaults (mechanical→low, bounded→medium, cross-cutting→high).

**Governance task rewrite (worktree-resident dispatches):** Task #9 targets CLAUDE.md,
which is a protected governance document. In a worktree-resident dispatch, the lead rewrites
this task at plan time:
```
□ 9. unassigned: Write staging fold-ins for CLAUDE.md (constants + cal results) [bounded]
```
The implementation agent writes fold-in entries to the staging file instead of editing CLAUDE.md
directly. See [governance-staging.md](governance-staging.md) (*Worktree Governance Staging*)
for the full pattern.

Also create a TodoWrite to track the same tasks programmatically. The printed plan is for
human readability; TodoWrite is for persistent tracking.

### Rules

- Task #1 is always parent-thread setup work (Phases 1–3). No exceptions — except a plan
  opened from a specification's task list, whose numbers stand (the setup row is added).
- One task per logical deliverable. Don't bundle "edit file AND run tests" into one line.
- **No collapsing tasks into batches or waves.** Every task from Phase 1 stays its own
  numbered line item in the plan. If you need to batch dispatches for practical reasons
  (e.g., tool-count ceilings), that is a dispatch optimization inside Phase 4 — but the
  task plan still tracks each deliverable individually. Never merge tasks like
  "implement tasks 1-6 + write tests" into a single line. Each task is executed or
  delegated, tracked, and reported on independently.
- If the spec says to do it, it gets a line. Don't silently absorb steps.

### Adding and parking rows

- If you discover a new required step during execution, ADD it to the plan with
  `timing --kinds`, then `timing --dispatch <DISPATCH-ID> --add --rows-file <row.json>`, and reprint. It takes the next number and shows as
  `+N`, the mark of a row the first listing missed. A row a review or an audit raised says
  so: `--add --origin review` shows `RN`, `--origin audit` shows `AN` (the default origin
  is `added`). Plan review and fix rounds as rows from the start (they are priced from
  history), so they are not the ones added later.
- **A row the run will not do is parked, not deleted:** `timing --dispatch <DISPATCH-ID>
  --park N --reason "<why>"`, for a row not yet started (a started row ends `--result
  cancelled`). It shows `◇` under *Parked* in `--status` and `--summary`, and at the
  close-out each parked row becomes a `findings` entry with Disposition `open`.

### Open the time log

As the task list is first listed, open the dispatch's time log. The log prices every
row and records its working time from the machine clock. First list the kind names
already in use, so a recurring row reuses one:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . timing --kinds

Then write the rows to a scratch JSON file, one object
per row: `id`, `title`, `owner`, `tier`, `effort`, `item` (the item the row belongs to,
for a combined epic), `parallel`, an optional `kind`, and an `estimate` in minutes for
any row history cannot price. Record what the log can never backfill: `class`
(`calculable`, `repeat` or `frontier`), `specRevision` (the specification's commit),
and `group` (the parallel group's id). A frontier row is never estimated: it carries a
`timebox` in minutes and `onTimebox`, the action when the budget runs out, and is
priced at its timebox (`timeboxed`). Then run:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor virtuoso timing --dispatch <DISPATCH-ID> --open --rows-file <rows.json>

When the specification carries a `##### Task list` (`references/task-rows.md`), open
from it instead, so its rows keep their numbers and the specification's price stays
beside the launch-time one:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor virtuoso timing --dispatch <DISPATCH-ID> --open --from-spec <spec> --item <ITEM-ID>

The specification's numbers are the plan's numbers. Rows it does not list, Task #1's
setup row among them, go in with `--add`, take the next numbers, and are measured like
any other row.

The log is `Timing.<DISPATCH-ID>.jsonl` in the registry's `closeOuts` role. The row
numbers it holds are the plan's numbers from here through close-out. `--open` refuses a
row it cannot price, naming it. Give that row an `estimate` and open again. Print the
plan with the predictions `timing --status` shows, so they are not retyped. No flag takes a
time or a duration: every stamp comes from the clock, so never write the log by hand.
The `closeOuts` directory must exist. In a project with no close-out yet, create it
first with `closeout --item <DISPATCH-ID> --date <YYYY-MM-DD> --prepare`. A step
discovered mid-run is registered before its first `--start` with
`timing --dispatch <DISPATCH-ID> --add --rows-file <row.json>`. It takes the next number.
If `timing` refuses (no `closeOuts` role, no open log, an unknown row), stop and report
the message.

Return to SKILL.md Phase 2, then go on to Phase 3.
