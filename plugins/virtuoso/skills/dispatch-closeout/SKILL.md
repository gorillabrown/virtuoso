---
name: dispatch-closeout
description: |
  MANUAL INVOCATION ONLY. Closes a completed dispatch. Verifies completion
  evidence, drafts the close-out report and retrospective entries, and then
  performs a transactional crossing — create the close-out artifact, append the
  append-only terminal record, persist local governance changes, close the item
  in the live work register through its provider, and verify every result. Any
  partial failure leaves a recovery record naming exactly what remains. Triggered
  by "/dispatch-closeout", "close out this dispatch", or "run the close-out".
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

# Dispatch Close-Out

## Preflight — read-only registry check (run first)

Resolve the plugin through its launcher, then run the **read-only** check (zero project writes):

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check        # Unix-like shell
    & "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check  # Windows PowerShell

Add `--json` for the structured result. Branch on the `virtuoso-status:` line:

- `ready` — continue. `warning` — surface the findings and continue; not blockers.
- `repair-needed` — **STOP.** Run `--mode repair` for the preview, show the user the
  proposed paths, semantic changes, files affected, and backup location, and apply it
  with `--apply` only after they approve.
- `adoptable` — offer `--mode adopt`: it registers what exists, in place; nothing is
  moved, duplicated, or rewritten.
- `none` — route the user to `/virtuoso-init`. `failed` — report the error verbatim and stop.

If neither launcher resolves, report that the plugin could not be located and stop; do
not guess a path. Never create a parallel document for a registered role, write to a
role whose `allowedWriters` does not name this ceremony, or treat a `mirror`, `report`,
`archive`, or `unknown` role as truth.

Read the `roadmap-integrity:` line (after `deadlines:`; `roadmapIntegrity` in `--json`). `fail` (missing, not text, or null bytes): STOP and report the corruption; never migrate or rewrite a corrupt roadmap. `warn` (empty or unusually large): surface it and confirm with the user first. `ok` or `external`: continue. Before rewriting the roadmap, re-check it with `virtuoso_preflight --check-document <path>`.

**Bookend with `/next-dispatch`**: it opens a dispatch, this closes it — and a held plan
from `/write-plan` or an epic from `/epic` (`references/execution-paths.md`). Wave 1
writes nothing until the user confirms; Wave 2 writes in a fixed order, verifying each
step. Never print a next dispatch kickoff — that is `/next-dispatch`.

## Resolve roles and capabilities before Wave 1

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor dispatch-closeout provider
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . closeout --item "<ITEM-ID>" --date "<YYYY-MM-DD>"
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --open

`closeout` is **read-only** — paths and `nextLessonId` (per `policy.lessons.idPrefix`),
nothing created; `--prepare` waits for the approved crossing. It **fails loudly**, never
falling back to a conventional directory. `lessons --open` lists the live lessons: those
the specification applied, and those a new lesson may repeat (a second occurrence
promotes an observation to a rule).

| Step | Requires |
|---|---|
| append the terminal record | `terminalLedger` registered, and `policy.terminalLedger.writers` names `dispatch-closeout` |
| close the item in the live register | provider capability `record-completion` (or `write-status`), and `workRegister`'s `allowedWriters` names `dispatch-closeout` |
| write the close-out artifact | `closeOuts` writable by this ceremony |
| append lessons | `lessons` writable by this ceremony |
| persist to version control | whatever `policy.git.policy` permits |

Anything unavailable changes the plan **before** Wave 1 drafts: say what happens instead
(a hand-off, a manual step) rather than discovering it mid-crossing.

## Held plans, combined epics, and retirements

Read the dispatch's origin line first. These change which Wave 1 items and Wave 2 steps
run; for each, **read [references/other-origins.md](references/other-origins.md)**
under its heading before Wave 1:

- **Held plans — ad hoc work that is not on the roadmap yet** (`Origin: held plan`, or
  `HB-<n>`): Steps 3 and 5 wait for the absorbing review's **recording crossing**.
- **Combined epics — one run, several items** (`Origin: epic packet`): one crossing,
  one record per item.
- **Retirement records routed here**: a review's A.4 or roadmap-status 2.1 retiring an item.

## Wave 1 — Draft & Confirm

**Before item 1, read [references/closeout-report-format.md](references/closeout-report-format.md)**
— the five-line brief, findings and dispositions, and the *Files Created* rules.

1. **Lead with the five-line brief.** Name the actual things, never aggregates.
2. Findings table.
3. Interpret non-pass results; propose dispositions.
4. Draft the net-new governance updates still needed.
5. Draft the lessons (Deliverable 2).
6. Propose the register and roadmap changes.
7. **Review every file the dispatch created** (base: the specification's *Branch* ref)
   and what it left outside the repository:

       "$HOME/.virtuoso/bin/virtuoso" dispatch_guards created-files --root . --base "<base ref>"
       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . footprint --dispatch <ITEM-ID>

   Draft *Files Created* from both: every file a disposition, plus the `- **Footprint:**` line.
8. State the **crossing plan**: the exact ordered steps Wave 2 will perform, the
   roles each touches, and what happens on a partial failure.
9. Ask the user to confirm dispositions, lessons, file dispositions, and the crossing plan.

Wave 1 writes nothing.

## Deliverables

**1. Close-out report** — results interpreted, findings classified, dispositions,
governance updates, next work. One per completed item, named per the project's
convention, in the registered `closeOuts` directory, from
[assets/CloseOut.template.md](assets/CloseOut.template.md), with its cost and guards
(`references/closeout-report-format.md`).

**2. Lessons** — in the registered `lessons` role, where the next specification reads
them; a lesson only in a close-out is one no specification will apply. Every close-out
produces **new lessons**, headed with this item **by identifier**
([assets/SpecRetro.entry.template.md](assets/SpecRetro.entry.template.md)), **or**
**`No new lesson — <reason>`**, the reason naming by identifier what was examined; with
neither it is not finished. Either way it records **the outcome of every lesson the
specification applied**, by status record, never an edit, and evaluates the
specification (effort calibration, sizing, routing, precision, discovery yield).
**Before item 5, read [references/spec-retro-format.md](references/spec-retro-format.md)**
and [references/promotion-rules.md](references/promotion-rules.md) (when a lesson, or a
gate found invalid, becomes a rule).

---

## Wave 2 — The transactional crossing

Run the six steps **in this order**; each verifies before the next begins. Local,
reversible work happens before anything irreversible or external.

### Step 1 — Verify completion evidence

Before writing anything, confirm the work is actually done:

- the deliverables the specification named exist;
- its acceptance criteria are mechanically satisfied — run the recorded commands, read
  the output, never accept a summary;
- the repository state matches the claim (read-only: `GIT_OPTIONAL_LOCKS=0 git
  --no-optional-locks status -sb`, `log --oneline -5`, `show <commit> --stat`);
- any mid-dispatch amendments are accounted for;
- for an epic packet, `dispatch_guards artifacts-exist --ref <default branch> <packet directory>/done.md`
  exits 0. On exit 1 the crossing waits for a `--no-ff` merge of the run branch, or of its
  docs-only completion commit, into the default branch. The close-out runs the record
  merge's scope check itself and reports it
  ([references/evidence-reconciliation.md](references/evidence-reconciliation.md), *Epic packets*);
- a connector-backed register's snapshot is fresh before the Wave-1 revision read: read
  every item with the session's connector, write the rows keyed by the register's own
  column names, and run
  `virtuoso_registry --root . snapshot --import <rows.json>` (or `--import <page>
  --columns <columns>`). Report each `[DRIFT]` line as a finding.

Evidence that does not hold **stops the crossing**: report which criterion failed, with
its output. A close-out is a claim about reality; do not make one you have not checked.

### Acceptance and evidence reconciliation

Not a seventh step; it governs how the six read evidence. First identify the currently
authorized acceptance contract, with every published amendment; superseded criteria stay
in the history but are not current gates. What each rule requires:
[references/evidence-reconciliation.md](references/evidence-reconciliation.md).

<!-- rule:closeout-never-amends-acceptance (acceptance-amendment) -->
**Never amend acceptance criteria during close-out.** If the active criteria
conflict with superior governance, a known-red baseline, or the delivered scope,
stop the crossing and route a concrete amendment for owner approval and independent
review.

<!-- rule:classify-before-completion (failure-classification) -->
**Classify every non-pass result before deciding whether completion evidence holds:**

in-scope regression and admission or custody failure block completion; an inherited
baseline failure needs evidence and an authorized amendment; an infrastructure failure
is repaired or rerun; an authorized exclusion is never reported as passed.

<!-- rule:proportional-evidence (evidence-proportionality) -->
**Use the least expensive evidence that proves each integrity property.**

<!-- rule:tested-tree-is-the-published-tree (integrated-identity) -->
**Completion evidence must identify the exact integrated commit and tree tested.**
Before publication, verify:

the diff matches the authorized manifest, the tested tree is the published tree, local,
tracking and authoritative remote references agree, and nothing unreviewed landed since
final acceptance.

<!-- rule:protected-state-over-test-result (protected-custody) -->
**A passing test result cannot override protected-state drift.** Where protected
inputs exist, record their configured integrity properties immediately before and
after the accepted test session — hashes, sizes, modification times, database
sidecars, generated-file provenance, or whatever else the project declares.

<!-- rule:close-only-what-was-verified (completion-scope) -->
**Close only the item whose deliverables and acceptance criteria were verified.** Do
not mark a parent epic, program, milestone, or release complete unless its own
separate completion conditions also pass.

<!-- rule:name-populations-not-aggregates (population-naming) -->
**Name the accepted test population and the excluded population separately.** Avoid
aggregate statements such as "all tests passed" when any tested or excluded
population contains a known failure.

### Step 2 — Create the close-out artifact

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . closeout --item "<ITEM-ID>" --date "<YYYY-MM-DD>" --prepare

Write the report into the registered `closeOuts` directory. **Idempotent:** if it
already exists for this item and date, update it in place or stop and ask — never write
a second one. Fill its `runtime:` line and `## Time` section by pasting `timing --summary
--dispatch <DISPATCH-ID>` (plus `--item <ITEM-ID>` for a combined epic) as printed. With
no time log, write `runtime: not measured (no time log)` and leave the section out.

Process any governance staging file: apply its fold-ins to the registered targets,
amendment migrations before inline collapses; delete it only after every fold-in lands.
A fold-in that conflicts with current state is a reconciliation question, never a
silent overwrite.

Summarize each `## Decision` block in the item's issue files (`Issue.<ITEM-ID>.*` in the
registered `issues` role, appended by `mid-dispatch-decision` step 6d) into *Mid-Dispatch
Decisions*. An issue file with no `## Decision` block is an open decision: stop and route
it to `/mid-dispatch-decision` before the crossing continues.

### Step 3 — Append the terminal record

Append **one** record to the registered `terminalLedger`, only if
`policy.terminalLedger.writers` names `dispatch-closeout` (else hand it to a permitted
ceremony or the user). **Append-only:** never reorder, rewrite, or delete a record; a
correction is a **new** record naming the one it corrects
(`policy.terminalLedger.correctionWriters`). **Idempotent:** an existing record is a no-op.

**A local register and ledger: Steps 3 and 5 are one command**, run here (it appends,
closes the item at the Wave-1 revision, and verifies both; Step 4 persists them).
**An external register: add `--ledger-only`** and drop `--revision`; Step 5 closes the item.

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor dispatch-closeout record-completion --item "<ITEM-ID>" --date "<YYYY-MM-DD>" --result "<result>" --evidence "<close-out file>" --estimate "<estimate>" --actual "<actual>" --revision "<revision>" --apply

Preview once without `--apply`. Take `--estimate` and `--actual` from
`timing --summary --json --dispatch <DISPATCH-ID>`, never a typed runtime, and pass neither when there is
no time log or it says `"complete": false`. Effort and Hours come from the register;
**read [references/ledger-and-register.md](references/ledger-and-register.md)** for
both values, flagged rows, and a ledger missing its Effort or Hours column. If the
register refuses after the append, or the record does not read back, the command leaves
a recovery record — follow *On partial failure*.

### Step 4 — Persist local governance changes

Apply the confirmed roadmap changes and append the lessons (new entries and status
records, none edited).

**Parked rows become findings.** Each row `timing --summary --json` lists under `parked`
is appended to the registered `findings` role as its own entry, **Disposition:** `open`,
for the roadmap review (entry format:
[references/ledger-and-register.md](references/ledger-and-register.md)).

Carry out the confirmed file dispositions (delete untracked temporaries, `git rm`
committed ones, add ignore patterns, stage the files confirmed for commit). Then persist
as far as `policy.git.policy` allows (`references/git-policy.md`): `read-only` and
`prepare-no-stage` report the exact changed paths for someone else to commit;
`explicit-path-stage` stages them and verifies the cached set; `explicit-path-commit`
also commits; `push` also pushes, subject to `policy.git.networkOperations`. Stage
**exact paths**, never `git add .` or `-A`; verify `git diff --cached --name-only`
before committing and stop on anything unexpected; report unrelated dirty paths and
leave them. Under `policy.git.separationOfDuties`, hand the commit over with the file
list. With no git policy, say which files were written and whether they are committed.
The close-out is not finished while changes are unpersisted.

### Step 5 — Close the item in the live register

Through the provider, never by editing a file: pass the Wave-1 `revision` (a concurrent
change is refused, not clobbered), set the terminal status per
`policy.workRegister.statusMappings`, and record the completion date and, where
`policy.workRegister.fieldMappings` names `evidence`, the close-out link. **An external
register is mutated by this ceremony, not the plugin:** run the provider's instruction
through the connector, one plan per call, read back, then `mutation-confirm` or
`mutation-abandon` ([references/ledger-and-register.md](references/ledger-and-register.md)).

**Two mandatory register outcomes** — the belt moves by exactly one: **retire the
closed item** (no longer in flight or pending); **elevate the next item** to the head —
a sequence change, not a dispatch kickoff.

### Step 6 — Verify every result

Re-read each thing you wrote, from its source:

- the close-out artifact exists at the resolved path with the expected content;
- the ledger has exactly one new record for this item; prior records are byte-identical;
- its Estimate and Actual equal `timing --summary --json --dispatch <DISPATCH-ID>`'s,
  `flagged` rows settled with the owner (`references/ledger-and-register.md`); its Effort
  is the item's;
- the roadmap and lessons changes are present, and committed if policy required it;
- the Lessons section passes the gate (a combined epic: `--item "<PACKET-ID>,<ITEM-ID>,..."`):

      "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --check "<close-out path>" --closeout --item "<ITEM-ID>"

- the item, re-read through the provider, is terminal, and the next item is at the head;
- every other terminal operation (worktree, lock or merge-slot release, remote
  publication, recovery state) holds at its source (`references/evidence-reconciliation.md`);
- `dispatch_guards created-files --base "<base ref>"` exits 0, or lists only files
  *Files Created* leaves for someone else or for the user's decision.

### On partial failure

If a later step fails after an earlier one succeeded — most often, local files commit
but the external register does not update — **write a recovery record** naming what
completed and what remains (`"$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root .
recovery`) and report it in the summary. Never silently retry the whole crossing: the
steps are idempotent, but the user must know it is incomplete before it runs again.

---

## After the crossing

- **Board.** A local register's `record-completion` regenerates it (`board regenerated:
  <path>`); otherwise, or without that line, run `"$HOME/.virtuoso/bin/virtuoso"
  generate_board --root .`. No `board` role: skip (creating one is `/roadmap-review`
  D.7's). A failure is reported and never undoes the crossing.
- **Buffer check, governance gates, optional adversarial pass.** Read
  [references/governance-gates.md](references/governance-gates.md): recommend
  `/roadmap-review` when the buffer runs below `policy.roadmap.dispatchBuffer` (never
  author a specification here); surface any audit, milestone, or release gate; and,
  before Wave 2 writes, offer `/adversarial-review` only when the close-out carries
  something the project will inherit unexamined.

## Guardrails and anti-patterns

- Propose dispositions; never decide them. Prefer net-new governance updates over
  ceremonial rewrites. Promote a lesson only after the same pattern appears twice.
- A close-out without its Lessons section is not a close-out: "No new lesson" is an
  answer; silence is not. Never leave output only in conversation.
- Never edit a generated artifact — regenerate it through its registered generator.
- Never declare completion from a summary, append a record before the artifact exists or
  evidence holds, edit an existing record, or create directories while resolving paths.
- Never close an external register before local governance is persisted — the ordering
  that produces an unrecoverable split.
