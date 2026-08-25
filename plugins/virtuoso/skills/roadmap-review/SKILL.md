---
name: roadmap-review
description: |
  MANUAL INVOCATION ONLY. Heavyweight roadmap recalibration ceremony
  (~30-45 min). ONLY runs when the user types "/roadmap-review",
  "run roadmap review", or "perform roadmap review". DO NOT
  auto-trigger on conversational mentions of roadmaps, planning,
  work items, phases, or specs — those belong to other skills. When
  invoked: reconciles the roadmap document against the project's
  configured work register through its provider, migrates completed
  work to the terminal record, assesses progress and scope
  discipline, replans and re-sequences remaining work, replenishes
  the dispatch buffer to the size the project's policy declares —
  each specification passing the shared versioned readiness rubric —
  reviews lessons learned, and produces a phase brief.
---

<!-- virtuoso-shared-contract v2 -->
**Shared contract (all Virtuoso skills).** Reference block; the skill body below governs specifics.

- **Registry resolution** — `Virtuoso/workspace-layout.json` is the authority; `Virtuoso.Governance.Readme.md` is its synchronized human view. Resolve every document, work item, and permission through the registry. Never hardcode a path, never fall back to a conventional one, and never infer authority from a role's name. Full contract: the plugin's `references/registry-contract.md`.
- **Read-only preflight** — session start and any "where am I" check runs `--mode check`, which performs **zero project writes**. Adoption, creation, and repair are separate operations, each explicitly invoked.
- **Providers** — work items come from the configured work-register provider (local file, spreadsheet, connector-backed task manager, issue tracker, database, or read-only snapshot). Negotiate capabilities before planning work; never open a register file directly. The live work register, the append-only terminal ledger, and any compatibility export are three different roles.
- **Provenance** — every derived figure cites its provider, source, and snapshot time. A figure whose inputs are missing is reported as *not computable* with the missing inputs named, never approximated.
- **Git** — behaviour is `policy.git`, not a fixed rule of this plugin. See `references/git-policy.md`. Under every policy: inspect first, stage exact paths, preserve unrelated work, no destructive flags, no force-push without explicit authorization.
- **Readiness** — one shared, versioned rubric: `references/readiness-rubric.md` (v1.0 — 8 universal checks plus the project's declared extensions). No skill restates it in its own words.
- **Actors** — roles from `policy.actors`: planner, implementation agent, reviewer, repository operator. Never a product, vendor, or model name. See `references/actors-and-interaction.md`.
- **Issue contract** — any stop, hold, block, or elevation becomes an issue document, routed per `policy.issues.targets` (local file, external tracker, or both).
- **Effort levels** — low / medium / high / max. A property of the task's difficulty, never a ranking of whoever performs it.

# Roadmap Review

## Preflight — read-only registry check (run first)

Resolve the plugin through its launcher, then run the **read-only** check. It performs
discovery and validation with zero project writes.

**Unix-like shell**

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check

**Windows PowerShell**

    & "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check

Add `--json` when you want the structured result (status, writes, findings, and the full
resolved role table). Read the `virtuoso-status:` line and branch:

- `ready` — the registry is valid. Continue.
- `warning` — usable; surface the findings to the user and continue. Warnings are not blockers.
- `repair-needed` — **STOP.** Run `--mode repair` to produce the preview, show the user the
  proposed paths, semantic changes, files affected, and backup location, and apply it only
  with `--apply` after they approve.
- `adoptable` — the project has governance documents but is not registered. Offer
  `--mode adopt`: it registers what exists, in place. Nothing is moved, duplicated, or rewritten.
- `none` — no registry and nothing to adopt. Route the user to `/virtuoso-init`.
- `failed` — report the error verbatim and stop.

If neither launcher resolves, report that the plugin could not be located and stop. Do not
guess a path.

**Governance authority.** Resolve every document you need through the registry
(`references/registry-contract.md`). Never create a parallel document for a registered role;
never write to a role whose `allowedWriters` does not name this ceremony; never treat a
`mirror`, `report`, `archive`, or `unknown` role as truth.

Read the `roadmap-integrity:` line. On `fail` (null bytes, non-UTF-8, or missing — exit 3), STOP and report the corruption to the user; do not migrate or rewrite a corrupt roadmap. On `warn` (empty or unusually large — exit 2), surface it and confirm with the user before proceeding. On `ok`, continue.


Heavyweight, periodic recalibration of an entire project. The ceremony
you run when you need to know — with confidence — where the project
has been, where it's going, and what to dispatch next.
### Resolve the work register before Phase 0

This ceremony reads and (where policy permits) writes work items. It does that
through the configured provider, never by opening a file directly.

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor roadmap-review provider
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor roadmap-review items --all --json

Read the provider description and **negotiate capabilities up front**:

| To do this | You need |
|---|---|
| read the pipeline at all | `list-active`, `read-status` |
| re-sequence the conveyor belt | `read-sequence` **and** `write-status` on a sequence field |
| replenish the dispatch buffer | `store-spec-link` (or inline specs — see policy) |
| record completion in Phase A | `record-completion` |

If a capability you need is missing, say so plainly and adjust the plan before
starting. Example: a project whose register is a read-only snapshot can still get
Phases A–C as a *report*, but Phase D cannot write status back — offer the report
and stop, rather than starting and failing halfway.

**Three roles, not one.** The live work register (`workRegister`), the append-only
terminal ledger (`terminalLedger`), and any compatibility export (`sprintCatalog`,
`sprintQueue`) are separate. This ceremony writes to the live register when its
`allowedWriters` names `roadmap-review`; it appends corrections to the terminal
ledger only when `policy.terminalLedger.correctionWriters` permits it; and it
regenerates exports only via their registered generator.

**If the project has no `workRegister` role,** the provider layer serves a
registered legacy `sprintCatalog` **read-only** through the compatibility adapter
and says so. In that state, run Phases A–C as analysis and offer to register a
`workRegister` role before doing anything that mutates.

### Read the project's policy before planning

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . roles --json

The manifest's `policy` block governs the shape of the plan. Nothing below is a
fixed number or a required structure:

| Policy | What it controls | Default |
|---|---|---|
| `roadmap.dispatchBuffer` | how many dispatch-ready specifications to carry | 5 (0 disables eager specification) |
| `roadmap.eagerSpec` | whether to specify ahead at all | true |
| `roadmap.hierarchy` | grouping levels, e.g. `["phase","stage"]`, `["milestone"]`, or `[]` | `["phase","stage"]` |
| `roadmap.lanes` | parallel lanes, if the project uses them | none |
| `roadmap.specStorage` | `inline` (in the roadmap), `files` (one per item), or `external` | inline |
| `roadmap.lengthCeilingLines` | when to snapshot and trim | 2000 |
| `roadmap.effortScale` | size → points for effort-weighted metrics | generic t-shirt scale |
| `standingRules.ids` | the project's inheritable rule identifiers | none — never hardcode one |
| `issues.targets` | where a blocker is written: `local`, `external`, or both | `["local"]` |

A project with a flat backlog and no phases is fully supported: `hierarchy: []`
means do not invent a phase layer to hang items from.

## When to use

Run this skill when:
- A phase or milestone has just closed
- The roadmap feels stale, drifted, or inaccurate
- You're prepping for a leadership or stakeholder checkpoint
- You're returning to a project after a gap and need to resync
- You suspect scope creep and want to verify

Do NOT use this skill for:
- Routine single-item planning
- Single-specification authoring (use `write-spec`)
- Weekly status updates (use `/roadmap-status`)

## Invocation

Manual only. The user must explicitly type one of:
- `/roadmap-review`
- "run roadmap review"
- "perform roadmap review"

If you infer this skill from context without an explicit invocation, STOP and
confirm with the user before proceeding.

## Glossary

- **Work item** — a discrete unit of work with clear acceptance criteria. The
  atomic dispatch unit. Identified by whatever id the project's register uses.
- **Group / lane** — optional grouping levels, named by `policy.roadmap.hierarchy`
  and `policy.roadmap.lanes`. A project may use neither.
- **Stub** — a placeholder item: id, title, and optionally a one-line gist.
- **Specification** — an item card with full structural fields plus implementation
  detail. It lives wherever `policy.roadmap.specStorage` says.
- **Dispatch-ready** — a specification that passes the shared readiness rubric.
- **Dispatch** — sending an item to the implementation agent.
- **Dispatch buffer** — the number of dispatch-ready specifications carried ahead
  of the head of the conveyor belt. Size is `policy.roadmap.dispatchBuffer`.

### The progression of an item's content density

```
Stub  →  Specification  →  Dispatch-ready  →  Close-out
(gist)   (drafted)         (rubric passed)    (terminal record)
                           ▲                  │
                           │                  ▼
                   roadmap-review        One record appended to the
                   Phase D.3 applies     terminal ledger; the full
                   the shared rubric     specification migrates to a
                                         dated archive
```

## Dispatch-Readiness Rubric

**Do not restate the rubric here.** There is exactly one rubric, versioned, in
the plugin's `references/readiness-rubric.md` (v1.0: eight universal checks U1–U8
plus whatever the project declares in `policy.rubric.extensions`). Open it and
apply it. `/next-pointer` applies the same file — that is the point.

Report readiness as the five separate findings the rubric defines
(specification, prerequisite, repository, external-register,
execution-environment). Never blend them into one verdict.

## Operating principles

1. **Iterative.** Each invocation makes the plan more accurate. It does not need
   to be perfect on the first run.
2. **The registry decides what is authoritative.** The roadmap document is the
   specification store; the work register is the live status authority. Which
   file plays which role is declared, not assumed.
3. **Archive-forward discipline.** The active roadmap holds dispatch-ready
   specifications for the buffer, stubs beyond, and one line per completed item.
   Full content migrates to a dated archive at close-out.
4. **The active section is uncompleted-only.** Hard invariant.
5. **Conveyor-belt sequencing.** Prerequisites first → risk-first tiebreaker →
   hardest-first second tiebreaker. The register's sequence field mirrors it.
6. **The dispatch buffer is policy.** Replenish to `policy.roadmap.dispatchBuffer`.
   If it is 0, skip eager specification entirely and say so.
7. **The rubric is non-negotiable.** A specification that fails it is not saved as
   dispatch-ready. It is enriched until it passes, or left a stub and flagged as a
   buffer gap.
8. **Specifications are complete because incomplete ones cannot be executed** —
   by anyone. Never justify rigor by claiming the implementer is a weaker model.
9. **Standing rules consolidate inheritable lessons.** Their identifiers come from
   `policy.standingRules.ids`; never invent or hardcode a rule id.
10. **Forward visibility minimum.** Carry specifications or stubs for at least
    three items ahead of dispatch, or the whole remaining backlog if it is shorter.
11. **Length ceiling.** Honour `policy.roadmap.lengthCeilingLines`. When crossed,
    snapshot to a dated archive and trim distant stubs.
12. **Checkpoint between phases.** The user confirms each phase.
13. **Bounded questions only.** Follow `references/actors-and-interaction.md`:
    2–4 concrete options, one recommended, an escape hatch on consequential
    decisions — structured when the host supports it, plain text when it does not.
14. **Orchestrate, don't reimplement.** Where an existing skill handles a
    sub-task well, invoke it.

## Inputs

1. The registry (`virtuoso_registry roles --json`) — the authority for every path.
2. The roadmap document, resolved through the `roadmap` role.
3. The work register, read through its provider.
4. Close-outs, retrospectives, audits, and decision records, resolved through
   their registered roles.
5. The terminal ledger, for what is already final.
6. The project codebase — required for Phase D.3 rubric verification.

## Outputs

Written into the registered `roadmapReviews` directory:
- `YYYY-MM-DD-audit.md` — Phase A diff
- `YYYY-MM-DD-assessment.md` — Phase B opinion
- `YYYY-MM-DD-plan.md` — Phase C decomposition
- `YYYY-MM-DD-lessons-applied.md` — Phase D lessons review
- `YYYY-MM-DD-phase-brief.md` — Phase D forward brief

Plus, updated in place where policy permits:
- The roadmap document
- The live work register, via its provider
- A new dated archive if the length ceiling was crossed

Every output states the provider, source, and snapshot time its figures came from.

---

## Phase 0 — INITIATE (only if needed)

### 0.1 Confirm the roadmap role

Resolve the `roadmap` role. If it is registered but absent, **report that** — do
not go looking for a similarly named file and do not seed a replacement. Offer
either to point the role at the real document (a registry edit, previewed) or to
create the document at the registered path.

### 0.2 Check for a finish line

If a finish-line target is missing, ask for one. Do not proceed without it.

### 0.3 Confirm the work register

If no `workRegister` role is registered, ask which of these the project wants,
and register it (the answer is a registry edit, previewed and approved — this
ceremony does not decide authority on its own):

- a local file the project already maintains (CSV or Markdown table),
- a spreadsheet,
- a connector-backed task manager, issue tracker, or database (registered as an
  external identifier such as `monday:board/1234567890`),
- a read-only snapshot, for reporting only.

If a legacy `sprintCatalog` is being read through the compatibility adapter, say
so explicitly in your report: it is a mirror, not the authority, and it cannot be
written until a `workRegister` role exists.

### 0.4 Legacy structure

Detect older structures and show a migration plan before applying anything.
Migration is conservative: an unrecognized legacy role stays unclassified rather
than being promoted to writable or authoritative.

---

## Phase A — AUDIT (≈10 min)

Goal: enforce archive-forward discipline. Move completed work out of the active
section, append its terminal record, and reconcile the register.

### A.1 Read everything
Inventory every item and its claimed status, from the register and the roadmap
separately. Record where they disagree; do not silently pick a winner.

### A.2 Build a candidate completion/archive list
Classify each item as *likely complete*, *likely dissolved*, or *definitely live*,
citing the signal for each.

### A.3 Confirm with the user
Batched, 5 at a time, with the bounded-question protocol.

### A.4 Apply changes
For each item being retired:
1. Append one record to the **terminal ledger** — but only if
   `policy.terminalLedger.correctionWriters` names `roadmap-review`. If it does
   not, list the records that need appending and route them to the close-out
   ceremony instead. Terminal records are append-only: a correction is a *new*
   record referencing the one it corrects. Never reorder, rewrite, or delete.
2. Add its one-line entry to the roadmap's completed summary.
3. Move its full content to the current dated archive.
4. Remove the full content from the active roadmap.
5. Update the item in the live register through the provider: set status, clear
   the sequence, record the completion date and the evidence link. Pass the
   `revision` you read so a concurrent change is refused rather than clobbered.
6. Re-running this step must not duplicate anything: the provider's writes are
   idempotent, and a terminal record that already exists is a no-op.

If the register write succeeds but an external half fails, a recovery record is
written under `Virtuoso/.recovery/`. Surface it; do not paper over it.

### A.5 Length-ceiling check
If the active roadmap exceeds `policy.roadmap.lengthCeilingLines`, snapshot and trim.

### A.6 Checkpoint
Show the diff. Ask: approve / roll back / pause.

---

## Phase B — ASSESS (≈10 min)

### B.1 Work remaining

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . kpis --json

Use the returned metrics. Each carries provenance. **A metric returned as
`not computable` is reported as not computable, with its missing inputs named.**
Never substitute an estimate, and never present a percentage the data cannot
support.

### B.2 Pace
Trailing completion rate versus the rate the finish line requires. If completion
dates are missing from the register, pace is not computable — say so.

### B.3 Scope discipline
Forward / sideways / backward deltas since the previous review. Score =
forward / (forward + sideways + backward).

### B.4 Render the assessment
Write `YYYY-MM-DD-assessment.md` into the registered reviews directory, with the
provenance block at the top.

### B.5 Checkpoint

---

## Phase C — PLAN (≈15 min)

### C.1 Derive macro steps
3–7 large outcome blocks.

### C.2 Group them
Only if `policy.roadmap.hierarchy` declares grouping levels. With `hierarchy: []`,
skip this step entirely — do not invent phases.

### C.3 Decompose into items
Each becomes a stub in the roadmap and a row in the register.

### C.4 Sequence the conveyor belt
Prerequisites → risk → hardest-first. Write the sequence back through the
provider only if it supports `write-status` on the sequence field; otherwise
produce the sequence as a recommendation and say why it was not written.

### C.5 Render the plan
Write `YYYY-MM-DD-plan.md`; update the roadmap's active section.

### C.6 Checkpoint

---

## Phase D — DISPATCH (≈25 min)

Goal: bring the dispatch buffer up to `policy.roadmap.dispatchBuffer`, validate
against lessons learned, integrate, and brief.

### D.1 Identify the head of the conveyor belt

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . next

Then take the first *N* active items in sequence order, where *N* is the buffer size.

### D.2 Determine the specification count

1. `target = policy.roadmap.dispatchBuffer` (default 5).
2. If `target == 0` or `policy.roadmap.eagerSpec` is false: skip D.3 entirely.
   Say that eager specification is disabled for this project and move to D.4.
3. Walk the belt from the head; count items already dispatch-ready.
4. `new specifications = target − already_ready`.
5. Target the next items in sequence order that are still stubs.

Edge cases: fewer than *N* active items → specify all of them. Group boundaries
are not a stopping condition. A hard blocker mid-buffer → stop there, flag it in
D.6, and note the buffer will fall short.

### D.3 Write the dispatch-ready specifications

For each item in scope:

**D.3.1 Draft.** Invoke `write-spec` with structural and implementation-detail
inputs, sourced from close-outs, decision records, standing rules, and archives.

**D.3.2 Apply the shared rubric.** Open `references/readiness-rubric.md` and walk
U1–U8 plus the project's declared extensions. For each item:
- **PASS** → move on.
- **CLOSABLE GAP** → resolve by investigation:

  | Gap | How to close |
  |---|---|
  | Stale location reference | Read the source; correct it in place. |
  | Vague test reference | Read the test file; insert the exact name and assertion. |
  | Unverified constant | Search; record the current value and where it lives. |
  | Non-mechanical acceptance criterion | Rewrite it as a command or assertion. |
  | Missing branch plan | Apply `policy.git.branchNameTemplate`. |
  | Missing failure handling | Enumerate the known failure modes; add "if X, do Y". |
  | Missing rollback | State the revert path for this project's git policy. |
  | Missing source citation | Find it and link it, with an anchor. |
  | Missing project-extension detail | Consult the project's own precedent. |

- **STRUCTURAL GAP** → ask the user. Do not invent decisions.

**D.3.3 Re-audit.** Walk the rubric again. Two enrichment passes maximum. A
specification still failing after two passes is NOT saved as dispatch-ready: flag
it as a buffer gap in D.6 and continue from the next item.

**D.3.4 Save.** Store the specification where `policy.roadmap.specStorage` says:

- `inline` — in the roadmap document at the item's position.
- `files` — one file per item under `policy.roadmap.specDirectory`, with the link
  stored on the register item via `store-spec-link`.
- `external` — in the external system, with the link stored the same way.

If the provider lacks `store-spec-link` and storage is `files` or `external`,
say so and record the links in the roadmap instead.

### D.4 Lessons-learned review

**D.4.1 Gather.** Read the registered `lessons` role, close-outs, audits, and
decision records. Resolve each through the registry; do not scan the filesystem
for lookalike names.

**D.4.2 Build the checklist.** Deduped, grouped by theme.

**D.4.3 Update the standing rules.** Rules live where
`policy.standingRules.source` says, and their identifiers come from
`policy.standingRules.ids`. Present rules get their wording verified; missing ones
are added with a source; superseded ones are updated or removed.

**D.4.4 Review the new specifications** against the checklist; enrich inline.

**D.4.5 Review existing specifications** against the same checklist; ask about
misalignments.

**D.4.6 Render** `YYYY-MM-DD-lessons-applied.md`.

### D.5 Integrate

**D.5.1** Place specifications per `policy.roadmap.specStorage`.

**D.5.2** Specification format (structural fields first, then implementation
detail). Grouping headings appear only if `policy.roadmap.hierarchy` declares them:

```
#### ITEM-ID — Item title

- **What:** …
- **Why:** …
- **Prerequisites:** …
- **Done when:**
    1. … (mechanically verifiable)
- **Effort:** …
- **Owners:** … (roles from policy.actors)
- **Source:** …

##### Implementation detail
- **Edit sites:** …
- **Tests:** …
- **Constants:** …
- **Branch:** … from …
- **Staging plan:** explicit paths, per policy.git
- **Failure handling:** if X, do Y; rollback: …
- **Project extensions:** … (only those policy.rubric.extensions declares)
```

Mid-dispatch amendments append as `##### Mid-Dispatch Amendment — YYYY-MM-DD`.

**D.5.3 Update the live work register.** Through the provider, for each newly
specified item: sequence, title, group, lane, effort, prerequisites, status, the
specification state, branch, description. Pass the `revision` you read.

Only write fields the provider reports it can write. Field *names* come from
`policy.workRegister.fieldMappings`; status *words* come from
`policy.workRegister.statusMappings`. Never assume a column is called
"Implementation Status" or that "Queued" is the right word for this project.

**D.5.4 Regenerate exports (optional).** If the project registers a generated
report role, regenerate it through its registered generator:

    "$HOME/.virtuoso/bin/virtuoso" build_register_report --root . --role sprintQueue

The generator refuses to write any role the project has not declared generated.
A generated export is a presentation output: never read it back as truth, and
never hand-edit it — regenerate it.

**D.5.5 Reconcile.** The roadmap's active section and the live register agree;
the first *N* items in sequence are dispatch-ready; later ones are stubs; the
completed summary carries one line each; standing rules reflect the checklist.

### D.6 Write the phase brief

`YYYY-MM-DD-phase-brief.md`:
- Group name(s) and goal(s), if the project uses grouping
- The items in the buffer, in sequence, **by descriptive name first** with the
  internal id secondary
- Implementation-detail highlights
- Rubric result per item, split into the rubric's five findings
- Lessons applied
- Prerequisites into and out of the buffer
- Exit criteria and estimated buffer duration
- Top 1–2 risks
- **Buffer gaps** — items that could not be made dispatch-ready, with the rubric
  checks that blocked them
- **Provenance** — provider, source, snapshot time for every figure

### D.7 Regenerate the planning cockpit

    "$HOME/.virtuoso/bin/virtuoso" generate_cockpit --root .

The cockpit reads the **configured authoritative work register** through its
provider and the roadmap through its registered role, and writes
`Virtuoso/reports/planning-cockpit.html`. It never modifies a source document; it
surfaces drift instead. Every figure it shows carries its provenance, and a
snapshot-backed read is labelled with its age.

### D.8 Final summary

- Roadmap changes
- Work-register changes, and which provider served them
- Pace and scope-discipline read, with any *not computable* metrics named as such
- The phase brief, in chat
- Buffer status: N dispatch-ready of the policy target
- Lessons applied
- Cockpit path
- Any outstanding recovery records

---

## Roadmap document template

Headings the plugin's parser recognizes are shown; a project may rename sections
and register the change. Grouping headings appear only if the project uses them.

```markdown
# [Project] — Roadmap

**Last updated:** [YYYY-MM-DD] — [one-line state]

## How This Document Is Maintained
[Archive-forward policy; dispatch buffer size; where specifications live]

## Finish Line — Target
[Description, graduated tiers if applicable]

## Completed Work Summary
| Item | Session | Result | Close-Out |
|------|---------|--------|-----------|

**Disposition of superseded work:**
- `[ITEM-ID]` — [reason]. [Where the work is preserved.]

## Active & Remaining Work

### Standing Rules All Items Inherit
- **[id from policy.standingRules.ids — short title].** [Rule.]

#### ITEM-ID — Title    *(position 1 — dispatch-ready)*
[structural fields + implementation detail, per D.5.2]

#### ITEM-ID — Title    *(beyond the buffer — stub)*
[One-line gist.]

## Non-Blocking Follow-Up Queue
## Notes
```

## The work register

The register's shape is the project's, not the plugin's. The canonical fields the
plugin reasons in are:

`id`, `title`, `sequence`, `status`, `written_status`, `prerequisites`, `effort`,
`lane`, `group`, `spec_link`, `branch`, `started`, `completed`, `evidence`,
`description`, `notes`.

Map them to the project's own column names in
`policy.workRegister.fieldMappings`, and the project's own status words in
`policy.workRegister.statusMappings`. Canonical statuses: `queued`, `in-flight`,
`blocked`, `completed`, `dissolved`, `superseded`. Canonical specification
states: `stub`, `full-spec`.

All metrics are computed from the register at read time, through the provider,
with provenance. There is no cache to refresh and nothing to recalculate.

## Escalating a blocker

A stop, hold, or block becomes an issue document routed per `policy.issues.targets`:

- `local` — write it to the registered `issues` directory using
  `policy.issues.filenameTemplate`.
- `external` — create it in the tracker named by `policy.issues.externalRole`,
  through the host's connector, and record the resulting identifier.
- both — do both, and cross-reference them.

Then route to `/mid-dispatch-decision` by path or identifier.

---

## Question protocol reminder

Every clarifying question follows `references/actors-and-interaction.md`: 2–4
concrete options, exactly one recommended, an escape hatch on consequential
decisions, structured when the host supports it and plain text when it does not.
Never ask an open-ended free-text question when a bounded set exists.
