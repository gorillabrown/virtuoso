---
name: roadmap-review
description: "MANUAL INVOCATION ONLY. Heavyweight roadmap recalibration ceremony\n(~30-45 min). ONLY runs when the user types \"/roadmap-review\",\n\"run roadmap review\", or \"perform roadmap review\". DO NOT\nauto-trigger on conversational mentions of roadmaps, planning,\nwork items, phases, or specs — those belong to other skills. When\ninvoked: reconciles the roadmap document against the project's\nconfigured work register through its provider, migrates completed\nwork to the terminal record, reconciles the ad hoc plans waiting\nin the holding bay, assesses progress and scope\ndiscipline, replans and re-sequences remaining work, replenishes\nthe dispatch buffer to the size the project's policy declares —\neach specification passing the shared versioned readiness rubric —\nreviews lessons learned, and produces a phase brief."
---

<!-- virtuoso-shared-contract v2 -->
**Shared contract (all Virtuoso skills).** Reference block; the skill body below governs specifics.

- **Registry resolution** — `Virtuoso/workspace-layout.json` is the authority; `Virtuoso.Governance.Readme.md` is its synchronized human view. Resolve every document, work item, and permission through the registry. Never hardcode a path, never fall back to a conventional one, and never infer authority from a role's name. Full contract: the plugin's `references/registry-contract.md`.
- **Read-only preflight** — session start and any "where am I" check runs `--mode check`, which performs **zero project writes**. Adoption, creation, and repair are separate operations, each explicitly invoked.
- **Providers** — work items come from the configured work-register provider (local file, spreadsheet, connector-backed task manager, issue tracker, database, or read-only snapshot). Negotiate capabilities before planning work; never open a register file directly. The live work register, the append-only terminal ledger, and any compatibility export are three different roles.
- **Provenance** — every derived figure cites its provider, source, and snapshot time. A figure whose inputs are missing is reported as *not computable* with the missing inputs named, never approximated.
- **Git** — behaviour is `policy.git`, not a fixed rule of this plugin. See `references/git-policy.md`. Under every policy: inspect first, stage exact paths, preserve unrelated work, no destructive flags, no force-push without explicit authorization.
- **Readiness** — one shared, versioned rubric: `references/readiness-rubric.md` (its universal checks, at the version it declares, plus the project's declared extensions). No skill restates it in its own words.
- **Actors** — roles from `policy.actors`: planner, implementation agent, reviewer, repository operator. Never a product, vendor, or model name. See `references/actors-and-interaction.md`.
- **Issue contract** — any stop, hold, block, or elevation becomes an issue document, routed per `policy.issues.targets` (local file, external tracker, or both).
- **Effort levels** — low / medium / high / xhigh / max. A property of the task's difficulty, never a ranking of whoever performs it.

<!-- virtuoso-overlay-clause v2 -->
**Project overlay.** If the registry declares an `overlays` role, read the overlay mirroring
every shipped file you read beneath it — this file at its own path (`skills/<skill>/SKILL.md`,
`agents/<Agent>.md`) and any `references/<file>.md` this one sends you to — and apply each on
top of the file it mirrors. Resolve them with the registry helper's `overlays` subcommand;
never fork or edit a shipped file to carry a project's rules. An overlay is additive and
wins on conflict, with one exception: it may not loosen a shared-contract safety rule
(registry resolution, read-only preflight, write permission, git safety, provenance, the
issue contract), and `references/registry-contract.md` may not be overlaid at all. No
`overlays` role, an absent overlays directory, and no matching overlay file all mean the
same thing — proceed on the shipped file alone.

# Roadmap Review

Periodic recalibration of a whole project: where it has been, where it is going, what to
dispatch next. Linked `references/<topic>.md` files are this skill's own detail, read at
the step that links them; unlinked `references/...` paths are the plugin's.

## Preflight — read-only registry check (run first)

Resolve the plugin through its launcher and run the **read-only** check (zero project writes):

**Unix-like shell**

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check

**Windows PowerShell**

    & "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check

`--json` gives the structured result. Branch on the `virtuoso-status:` line:

- `ready` — continue.
- `warning` — usable; surface the findings and continue. Warnings are not blockers.
- `repair-needed` — **STOP.** Run `--mode repair` for the preview; show the user the
  proposed paths, semantic changes, files affected, and backup location; apply with
  `--apply` only after they approve.
- `adoptable` — governance documents exist but are unregistered. Offer `--mode adopt`: it
  registers what exists, in place; nothing is moved, duplicated, or rewritten.
- `none` — nothing to adopt. Route the user to `/virtuoso-init`.
- `failed` — report the error verbatim and stop.

If neither launcher resolves, report that the plugin could not be located and stop; do
not guess a path. Resolve every document through the registry
(`references/registry-contract.md`): never create a parallel document for a registered
role, write to a role whose `allowedWriters` does not name this ceremony, or treat a
`mirror`, `report`, `archive`, or `unknown` role as truth.

Read the `roadmap-integrity:` line (after `deadlines:`; `roadmapIntegrity` in `--json`).
`fail` (missing, not text, or null bytes): STOP and report the corruption; never migrate
or rewrite a corrupt roadmap. `warn` (empty or unusually large): surface it and confirm
with the user before proceeding. `ok` or `external`: continue. Before rewriting the
roadmap, re-check it with `virtuoso_preflight --check-document <path>`.

### Resolve the work register and the policy before Phase 0

Work items are read and written through the configured provider, never by opening a file:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor roadmap-review provider
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor roadmap-review items --all --json
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . roles --json

**Read [references/setup.md](references/setup.md)**: the capability each phase needs, and
the `policy` keys that shape the plan (none is a fixed number or a required structure).
If a capability is missing, say so and adjust the plan before starting — never start and
fail halfway.

**Three roles, not one:** the live work register (`workRegister`), the append-only
terminal ledger (`terminalLedger`), and any compatibility export (`sprintCatalog`,
`sprintQueue`). Write the register only when its `allowedWriters` names
`roadmap-review`; the ledger only as A.4 allows; an export only through its registered
generator. With no `workRegister` role, a legacy `sprintCatalog` is served **read-only**
through the compatibility adapter: run Phases A–C as analysis, and offer to register a
`workRegister` role before anything mutates.

## When to use

**Manual only:** the user types `/roadmap-review`, "run roadmap review", or "perform
roadmap review"; if you inferred it from context, STOP and confirm first. Run it when a
phase or milestone closed, the roadmap feels stale, a stakeholder checkpoint is near, you
return after a gap, or you suspect scope creep. Not for single-item planning, weekly
status (`/roadmap-status`), or ad hoc work between reviews (`/storyboard`, then
`/write-plan`; their output waits in the holding bay for this ceremony). Terms:
[references/roadmap-format.md](references/roadmap-format.md) § Glossary.

## Readiness and operating principles

**Do not restate the rubric.** There is one, versioned: the plugin's
`references/readiness-rubric.md` (its universal checks at the version it declares, plus
`policy.rubric.extensions`), the same file `/next-dispatch` applies. Report readiness as
its five separate findings (specification, prerequisite, repository, external-register,
execution-environment), never one blended verdict.

1. **Iterative.** Each run makes the plan more accurate; the first need not be perfect.
2. **The registry decides authority.** The roadmap is the specification store; the work
   register is the live status authority. Roles are declared, not assumed.
3. **Archive-forward; the active section is uncompleted-only** (hard invariant). It holds
   dispatch-ready specifications for the buffer, stubs beyond, and one line per completed
   item; full content migrates to a dated archive at close-out.
4. **Specifications are complete because incomplete ones cannot be executed** — by
   anyone. Never justify rigor by claiming the implementer is a weaker model.
5. **Standing rules consolidate inheritable lessons.** Ids come from
   `policy.standingRules.ids`; never invent or hardcode one.
6. **Forward visibility.** Carry specifications or stubs for at least three items ahead
   of dispatch, or the whole backlog if shorter.
7. **Checkpoint between phases.** The user confirms each phase.
8. **Bounded questions only** (`references/actors-and-interaction.md`): 2–4 concrete
   options, exactly one recommended, an escape hatch on consequential decisions;
   structured when the host supports it, plain text when not. Never open free text when
   a bounded set exists.
9. **Orchestrate, don't reimplement.** Invoke an existing skill that handles a sub-task well.
10. **The holding bay empties at every review**, the one ceremony that brings ad hoc work
    onto the roadmap: each open entry is absorbed or withdrawn, except one in flight,
    reported and reconciled next review (`references/execution-paths.md`).

## Inputs and outputs

**Inputs**, each through the registry: the roadmap, the work register (via its
provider), close-outs, retrospectives, audits, decision records, the terminal ledger, the
codebase (for D.3), and the holding bay if registered.

**Outputs** go in the registered `roadmapReviews` directory. Run the resolver once, at the start:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . review --date <YYYY-MM-DD>

Keep the `date` it prints (default: today, UTC) for every later call, so a review past
midnight UTC keeps one prefix. Write under its `prefix` (the date, or `DATE-2`…), or
under `resume` when it names an interrupted review of that date, which you finish. Never
overwrite an earlier review's records. `YYYY-MM-DD` below is that prefix: `-audit.md`,
`-assessment.md`, `-plan.md`, `-lessons-applied.md`, `-phase-brief.md`. Every output
states the provider, source, and snapshot time of its figures.

---

## Phase 0 — INITIATE (only if needed)

- **0.1 Roadmap role** registered but absent → **report that**; never seek a lookalike
  file or seed a replacement. Offer to point the role at the real document (a previewed
  registry edit) or create the document at the registered path.
- **0.2 Finish line** missing → ask for one. Do not proceed without it.
- **0.3 Work register** unregistered → ask which kind and register it as a previewed,
  approved registry edit: [references/setup.md](references/setup.md) § Register kinds.
- **0.4 Legacy structure.** Show a migration plan before applying anything. An
  unrecognized legacy role stays unclassified, never promoted to writable or authoritative.

---

## Phase A — AUDIT (≈10 min)

Goal: move completed work out of the active section, append its terminal record, and
reconcile the register.

### A.1 Read everything
Inventory every item's claimed status from the register and the roadmap separately;
record disagreements, never silently pick a winner. Read a connector-backed register
fresh first: read every item with the session's connector, write the rows keyed by the
register's own column names, and import them with `virtuoso_registry --root . snapshot
--import <rows.json>` (or a raw page: `--import <page> --columns <columns>`;
`references/registry-contract.md`, *Refreshing a connector-backed register's
snapshot*). Each `[DRIFT]` line is a finding. Read the holding bay (`holding --open
--json`; Exit 3 naming `holdingBay` means none is held — say so), and surface an entry
with problems (`holding --check <entry>`), never skip it. Check each close-out since the
last review with `lessons --check <close-out> --closeout --item <ITEM-ID>`: one that
fails is a gap for D.4 — a lesson nobody recorded, or nothing recorded and no reason given.

### A.2 Build a candidate completion/archive list
Classify each item *likely complete*, *likely dissolved*, or *definitely live*, citing
the signal. Route each open held entry by trail state: `executed` → A.4b; `storyboarded`
or `planned` → C.3 (a `planned` entry whose trail names closed-out items sends those to
A.4b first); `paused` (a storyboard or plan stopped before alignment) → A.3, asking
whether to resume it (`/storyboard <entry>`, which aligns it first) or withdraw it; it is
never absorbed while unaligned; `in-flight` → report only (the review after its close-out absorbs it); `unrecorded` or with problems → A.3, repaired
through its owner or withdrawn.

### A.3 Confirm with the user
Batched, 5 at a time, with bounded questions.

### A.4 Apply changes
**Read [references/audit.md](references/audit.md) § A.4 first.** Route each retired
item's terminal record to `/dispatch-closeout`: a retirement is an *ordinary* record,
which only an actor `policy.terminalLedger.writers` names may append (by default
`dispatch-closeout` alone; `correctionWriters` covers corrections only), and its
*Retirement records routed here* says what runs. Then add the completed-summary line,
archive the full content, and update the register through the provider with the
`revision` you read. Terminal records are append-only; a re-run duplicates nothing.
Surface any recovery record under `Virtuoso/.recovery/`.

### A.4b Absorb held plans that already ran
For each `executed` entry, follow [references/audit.md](references/audit.md) § A.4b. Its
completion is recorded by `/dispatch-closeout`'s recording crossing, never by you.

### A.5 Length-ceiling check
Past `policy.roadmap.lengthCeilingLines`, snapshot to a dated archive and trim distant stubs.

### A.6 Checkpoint
Show the diff. Ask: approve / roll back / pause.

---

## Phase B — ASSESS (≈10 min)

### B.1 Work remaining

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . kpis --json

Each metric carries provenance. **A metric returned as `not computable` is reported as
such, with its missing inputs named** — never an estimate, never an unsupported percentage.

### B.2 Pace
Read the `pace` block of the same call: per declared deadline, a verdict (`ahead`, `on
track`, `behind`, `overdue`, `met`). **[references/assess.md](references/assess.md) §
B.2** lists what to report per deadline and how to record a deadline the owner sets or
moves. With none declared, say "no deadline is declared": pace against a date is not
computable. Never derive pace by hand or copy a date from anywhere but the policy.

### B.3 Scope discipline
Score = forward / (forward + sideways + backward), over items that reached a terminal
status since the previous review and work shipped with no register entry (named as
such), each counted once:

- **Forward** — toward the finish line: named in a declared deadline's `scope`
  (`policy.roadmap.deadlines.<id>.scope`), or, with none declared, in the roadmap's
  finish-line section.
- **Sideways** — delivered, not toward the finish line: hardening, measurement, tooling,
  an ad hoc stream, a held plan that already ran (A.4b).
- **Backward** — undoes delivered work: a revert or rollback, a terminal item reopened,
  a release withdrawn.

Added scope, including held entries absorbed in C.3, is listed with the class it would
take, and is not scored. Say where a call is a judgement; keep the previous review's call
for the same item. Name each absorbed held entry by title and entry, and each withdrawn
one with its reason: unreviewed ad hoc entry is how scope drifts unseen.

Then carry in the previous cycle's `YYYY-MM-DD-lessons-applied.md`, every open entry in
the registered `findings` role, and the open board comments (`board_comments`), each as
[references/assess.md](references/assess.md) § B.3 says.

### B.4 Render the assessment
`YYYY-MM-DD-assessment.md`, provenance block at the top.

### B.5 Checkpoint

---

## Phase C — PLAN (≈15 min)

### C.1 Derive macro steps
3–7 large outcome blocks.

### C.2 Group them
**Workstreams and deliverables.** Run the read-only proposal:

    python <plugin>/scripts/virtuoso_registry.py --root . structure --propose --json

First check its `registerColumns`. When `ready` is false, settle that before naming any
candidate: tell the owner which columns are `missing` and how to add them
(`references/registry-contract.md`, *Adding the workstream and deliverable columns*), map
them, refresh the snapshot, propose again. Never ask for an approval the register cannot
store; if the owner declines the columns, record that and skip grouping. **Read
[references/plan.md](references/plan.md) § C.2** for what each review proposes and what
the apply writes. Ask the owner to approve, rename or reject each workstream and
deliverable. **Nothing is written before the owner approves.** Then:

    python <plugin>/scripts/virtuoso_registry.py --root . --actor roadmap-review structure --apply --file <approved.json>

A `hierarchy` naming other levels groups by those; an owner who wants no workstreams
skips the proposal. With `hierarchy: []` and no structure approved, invent no phases.

### C.3 Decompose into items
Each becomes a roadmap stub and a register row. Every open `storyboarded` or `planned`
held entry is absorbed or withdrawn here (asked in a batch; nothing is carried past the
review), and every item already on the roadmap gets its `Path` set:
[references/plan.md](references/plan.md) § C.3.

### C.4 Sequence the conveyor belt
Prerequisites first → risk-first → hardest-first; the register's sequence field mirrors
it. Write it through the provider only if it supports `write-status` on the sequence
field; otherwise give a recommendation and say why. An epic row (`/epic`) is sequenced as
one item; the items nested under it (`member_of`) ride with it and are never sequenced
apart.

### C.5 Answer the pace verdict
A `behind` or `overdue` verdict gets a stated response in the plan, at least one of:
reduce scope with the owner; resequence toward the dated finish line; release blocked
work, naming what holds it; take a moved date to the owner (via `policy-set`, never by
hand). A plan that leaves it unaddressed says so.

### C.6 Render the plan
Write `YYYY-MM-DD-plan.md`; update the roadmap's active section (template:
[references/roadmap-format.md](references/roadmap-format.md)).

### C.7 Checkpoint

---

## Phase D — DISPATCH (≈25 min)

Goal: fill the dispatch buffer to `policy.roadmap.dispatchBuffer`, validate against
lessons learned, integrate, and brief.

### D.1 Identify the head of the conveyor belt
Run `virtuoso_registry --root . next`; take the first *N* active items in sequence (*N*
= buffer size).

### D.2 Determine the specification count
1. `target = policy.roadmap.dispatchBuffer` (default 5).
2. `target == 0` or `policy.roadmap.eagerSpec` false → skip D.3, say eager specification
   is disabled, go to D.4.
3. `new specifications = target − items already dispatch-ready` from the head.
4. Target the next stubs in sequence. Skip one declaring `Path: epic` (`/epic` charters
   it; it does not count toward the buffer), and one an active epic charter names
   (`item:` or `items:`, in the registered `epics` role): it runs under that packet's order.

Fewer than *N* active items → specify all. Group boundaries do not stop the walk. A hard
blocker → stop there, flag it in D.6, note the shortfall.

### D.3 Write the dispatch-ready specifications
**Follow [references/specifications.md](references/specifications.md) § D.3** (D.3.0–D.3.4):
the live lessons first (`lessons --open`), drafts in the D.5.2 format, the shared rubric
(`references/readiness-rubric.md`) walked per item. **Gates:** a STRUCTURAL GAP goes to
the user — never invent decisions; after two enrichment passes, a still-failing
specification is NOT saved as dispatch-ready but flagged as a buffer gap in D.6.

### D.4 Lessons-learned review
**Follow [references/lessons-review.md](references/lessons-review.md)** (D.4.1–D.4.6):
decide every computed promotion candidate (`lessons --candidates`), record promotions as
status records (`--record-status`), and re-check every dispatch-ready specification
against the live lessons.

### D.5 Integrate
- **D.5.1** Place specifications per `policy.roadmap.specStorage`.
- **D.5.2 Specification format** — in [references/specifications.md](references/specifications.md),
  which also holds D.5.3–D.5.4. Other skills cite it as roadmap-review's D.5.2.
- **D.5.3 Update the live work register** as that file says. Create a missing item only
  through `create-item`, and only when `policy.workRegister.creators` names this
  ceremony — otherwise say so and stop.
- **D.5.4 Regenerate exports (optional)**, only through the registered generator.
- **D.5.5 Reconcile.** Roadmap and register agree; the first *N* items are
  dispatch-ready, later ones stubs; one completed-summary line each; standing rules
  reflect the checklist.

### D.6 Write the phase brief
`YYYY-MM-DD-phase-brief.md`: [references/review-outputs.md](references/review-outputs.md) § D.6.

### D.7 Regenerate the board

    "$HOME/.virtuoso/bin/virtuoso" generate_board --root . --create

Reports `board created` at the first review, `board regenerated` after. Never commit the
page; commit its comments file. See [references/roadmap-format.md](references/roadmap-format.md)
§ The roadmap board.

### D.8 Final summary
In chat: [references/review-outputs.md](references/review-outputs.md) § D.8.

## Escalating a blocker

A stop, hold, or block becomes an issue document per `policy.issues.targets` (`local`:
the registered `issues` directory, named by `policy.issues.filenameTemplate`; `external`:
the tracker `policy.issues.externalRole` names, via the host's connector, recording its
identifier; both: cross-referenced). Then route to `/mid-dispatch-decision` by path or
identifier.
