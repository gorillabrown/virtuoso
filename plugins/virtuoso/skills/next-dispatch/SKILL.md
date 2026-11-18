---
name: next-dispatch
description: |
  MANUAL INVOCATION ONLY. The dispatch gate. Reads the next eligible
  work item from the project's configured work-register provider,
  finalizes its specification against the shared readiness rubric,
  drives every pre-flight check to a resolved state, and prints a
  dispatch kickoff with a repository-reconciliation recipe matched to
  the project's declared git policy. Routes a head item whose path is
  epic to /epic. Triggered by "/next-dispatch", "next dispatch",
  "show next", or "what's next". Does NOT replan, re-sequence, or author new
  items — that is /roadmap-review; new work that is not on the roadmap
  starts at /storyboard.
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

# Dispatch Kickoff

The dispatch gate. It reads the next eligible item **through the configured provider**,
finalizes its specification, resolves every pre-flight check (or elevates it as a
question), and prints three sections, in order: a plain-language summary, the readiness
findings (five, separate) and figures, and the code-boxed kickoff with a reconciliation
recipe matched to `policy.git`. A specification must be complete because an incomplete one
cannot be executed without inventing the missing decisions — by anyone, at any capability.
That is the only reason; this skill never ranks hosts, products, or models.

**Bookend with `/dispatch-closeout`**, which closes the dispatch transactionally. **One of
three paths, one destination:** this path opens only on an item a roadmap review placed on
the master roadmap; the ad hoc path (`/storyboard`, then `/write-plan`) and the epic path
(`/epic`) deliver the same thing to execution, per `references/execution-paths.md`.

Linked `references/` files are in this skill's folder; unlinked ones are the plugin's.

## Preflight — read-only registry check (run first)

Resolve the plugin through its launcher, then run the **read-only** check (zero project
writes).

**Unix-like shell**

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check

**Windows PowerShell**

    & "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check

Add `--json` for the structured result (status, writes, findings, and the full resolved
role table). Branch on the `virtuoso-status:` line:

- `ready` — the registry is valid. Continue.
- `warning` — usable; surface the findings and continue. Warnings are not blockers.
- `repair-needed` — **STOP.** Run `--mode repair` for the preview, show the user the
  proposed paths, semantic changes, files affected, and backup location, and apply it
  with `--apply` only after they approve.
- `adoptable` — governance documents exist but are not registered. Offer `--mode adopt`:
  it registers what exists, in place. Nothing is moved, duplicated, or rewritten.
- `none` — no registry and nothing to adopt. Route the user to `/virtuoso-init`.
- `failed` — report the error verbatim and stop.

If neither launcher resolves, report that the plugin could not be located and stop. Do not
guess a path.

**Governance authority** (`references/registry-contract.md`): never create a parallel
document for a registered role, write to a role whose `allowedWriters` does not name this
ceremony, or treat a `mirror`, `report`, `archive`, or `unknown` role as truth.

Read the `roadmap-integrity:` line the preflight printed (it follows the `deadlines:` line; `--json` carries it as `roadmapIntegrity`). On `fail` (missing, not text, or null bytes), STOP and report the corruption to the user; do not migrate or rewrite a corrupt roadmap. On `warn` (empty or unusually large), surface it and confirm with the user before proceeding. On `ok`, or `external` (a roadmap the preflight does not read), continue. Before rewriting the roadmap, re-check it: `virtuoso_preflight --check-document <path>` prints the same state for one file.

## Resolve the register before anything else

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor next-dispatch provider
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor next-dispatch next --json

**The absence of any particular file is never a hard stop** (redesign item 37): what matters
is what the provider can do. **Read [references/register-provider.md](references/register-provider.md)**
for the capabilities to negotiate **before** planning the run, the compatibility adapter,
and the stale-snapshot refresh. A **stale** snapshot (`next` prints `[STALE]`) is refreshed
before naming the head — for a connector-backed register,
`virtuoso_registry snapshot --import <rows.json>` — and `next` run again. When it cannot be,
print its age; external-register readiness is a GAP and the verdict "Not ready" until the
head is confirmed against the live register.

## When to use, and when not

Manual only: `/next-dispatch`, "next dispatch", "show next", "what's next" — to finalize the
specification before dispatching, check what is queued, or ask "where am I + what is next".
Not for: a status briefing (`/roadmap-status`); replanning, re-sequencing, or authoring items
(`/roadmap-review`); work not on the roadmap (`/storyboard`, then `/write-plan`); several
specified items run together unattended (`/epic <ITEM-ID> <ITEM-ID> …`, which checks whether
they combine); or a stub at the head — this skill refuses.

## Glossary

**Work item** — a discrete unit of work with clear acceptance criteria. **Stub** — id, title,
maybe a one-line gist. **Specification** — the full item card, wherever
`policy.roadmap.specStorage` puts it; **dispatch-ready** when it passes the shared rubric.
**Kickoff** — the code-boxed block telling the dispatcher exactly where the specification
lives, plus its immediate context. **Buffer** — the dispatch-ready items carried ahead,
sized by `policy.roadmap.dispatchBuffer`. **Conveyor belt** — the sequenced active items in
the live register.

## Operating principles

1. **Finalizing the specification is the job.** An item passes dispatch-ready by the shared
   rubric, or it does not pass. Hard halt on a stub at the head (no partial dispatch) and on
   a structural gap (a bounded question; never improvise the decision).
2. **The provider is the register.** Never open a register file directly, or treat a
   mirror, a generated report, or an archive as the live pipeline.
3. **Writes are narrow:** the head item's specification and its own register row — never
   re-sequencing, new items, or other items' specifications (`/roadmap-review`). Every write
   goes through the provider with the `revision` read, and only when the role's
   `allowedWriters` names `next-dispatch`.
4. **Descriptive names first** (item 38): an item's human title leads, the identifier
   second; an id alone never explains. **Bounded questions only**
   (`references/actors-and-interaction.md`); most gaps close by investigation.
5. **Git behaviour is `policy.git`** (`references/git-policy.md`). Read-only inspection is
   open under every policy; run it lock-free (`GIT_OPTIONAL_LOCKS=0 git --no-optional-locks …`).
   Every kickoff carries a reconciliation recipe that preserves uncommitted work, halts on
   divergence rather than forcing, and never prescribes deleting a lock file automatically.
6. **Verify from primary evidence.** Never accept "tree clean" or "reconciled" as a claim;
   read the underlying output.
7. **Pre-flight checks are resolved, not noted** (Phase 3.6). "Noted, non-blocking" under a
   Ready verdict is forbidden.

---

## Dispatch-Readiness Rubric

**One rubric, one home:** the plugin's `references/readiness-rubric.md` — its universal
checks, at the version it declares at its top, plus the project's declared extensions.
`/roadmap-review` applies the same file, so the two cannot disagree.

### Report readiness as five separate findings (item 39)

Never one blended verdict:

| Finding | What it covers |
|---|---|
| **Specification readiness** | U1–U4, U6, U7, U9, U10, U11 plus declared project extensions |
| **Prerequisite readiness** | U5, resolved against the live register through the provider |
| **Repository readiness** | U8 plus the repository's actual current state, under `policy.git` |
| **External-register readiness** | can the register be read; is the snapshot fresh; does the provider support the mutations this dispatch needs |
| **Execution-environment readiness** | tooling, dependencies, and access the work requires |

Each is independently PASS / GAP / BLOCKED, each with its own reason. A dispatch is ready
only when all five pass.

---

## Repository reconciliation

The recipe is a **template**, filled from `policy.git` and the detected repository state —
never a placeholder, never a step the policy does not permit. **To fill or print it, read
[references/reconciliation-recipe.md](references/reconciliation-recipe.md)**: detection,
the Step 0 recipe (0a–0d) and its sanctioned fallback, printing it for the host's shell,
branch cleanup, and the git rules during the work. **Halt semantics:** any STOP halts the
implementation agent, which reports the exact git output and escalates — a dispatch
blocker, like a failed prerequisite, never improvised around.

---

## Phase 1 — READ AND IDENTIFY

### 1.1 Determine the head item

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor next-dispatch next --json

The provider returns the next item not in flight whose prerequisites are all terminal, in
sequence order, with provenance (lacking `next-eligible`, compute it the same way from
`items`). In-flight items it skips are listed in `inFlight` (an `in flight:` line each); name
each in *What's next* as in flight, never as the head. No active items → **Queue empty**.

### 1.2 Hard-halt checks (epic path, stub at head)

- Roadmap entry declares `Path: epic` → STOP; **Epic at head**. An epic is chartered, not
  dispatched, and this rubric is not its gate.
- An active charter in the registered `epics` role names the head item, in its
  `item:` or its `items:` → STOP; it is already part of an epic run (`next` reports
  `inEpicPacket` in the JSON, an `in epic run:` line in the text). Name the packet and point
  to its launch file's resume prompt: a combined epic runs its items itself, in its own
  order, and a separate dispatch would collide with it.
- Specification state is not `full-spec` → STOP; **Stub at head**.

### 1.3 Locate the specification

Per `policy.roadmap.specStorage` — inline in the roadmap, a file under
`policy.roadmap.specDirectory`, or the external system the item's `spec_link` names —
resolved through the registry.

### 1.4 Figures, with provenance

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . kpis --json

Report each metric with its provider, source, and snapshot time. **A metric the data cannot
support is `not computable`, with the missing inputs named** — never estimated or quietly
omitted. **Never read a generated report or spreadsheet cache for any of this.** **Read
*Pipeline figures* in [references/kickoff-format.md](references/kickoff-format.md)** for
the effort unit, buffer health, "last review", and pace.

### 1.5 Standing rules

Match the rules at `policy.standingRules.source` against the head item's domain and pick
the one or two most relevant. Identifiers are the project's own
(`policy.standingRules.ids`); never invent or hardcode one.

### 1.6 Live lessons

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --open

Match them the same way. The specification's *Lessons applied* section must account for
them (U9): each that bears on the item and the change it made, or that none applies.

---

## Phase 2 — READINESS AUDIT

Walk `references/readiness-rubric.md` against the head item's specification and sort every
result into the five findings: **PASS** → record it; **CLOSABLE GAP** (a verifiable
assertion investigation can settle) → flag for Phase 3; **STRUCTURAL GAP** (a real deferred
decision) → halt the print and ask. Run U9's mechanical half and read its findings in:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --check <spec> --item <ITEM-ID>

A missing or empty *Lessons applied* section is a closable gap. A live lesson whose
recommendation demands a decision the specification does not make is a structural gap.

### 2.1 Prerequisite readiness

Resolve each prerequisite's state **through the provider**:
- terminal (`completed`, `dissolved`, `superseded`) → met
- `queued` / `in-flight` / `blocked` → pending
- not present in the register → unknown; `next` names it in `missingPrerequisites`. Check
  the terminal ledger before concluding, and report "unknown" if it is in neither

Any pending or unknown prerequisite makes prerequisite readiness fail. Still produce the
full output, with the verdict "Not ready" and the reason named, and offer a dispatchable
alternative deeper in the queue if one exists.

### 2.2 External-register readiness

Report plainly: can the register be read; is the snapshot fresh (or stale, by how much);
does the provider support every mutation this dispatch will need (`write-status` for the
in-flight transition, `record-completion` for close-out); is it served through the
compatibility adapter. A read-only register is permissible — say so, so nobody expects a
status write later.

### 2.3 Execution-environment readiness

Tooling, runtime dependencies (`policy.dependencies`), credentials, and access the work
requires — a finding here, not a surprise mid-implementation.

---

## Phase 3 — ENRICHMENT (only if Phase 2 flagged closable gaps)

Close each gap by investigation and update the specification in place, surgically. **Read
the gap table in [references/enrichment.md](references/enrichment.md)** — how to close a
stale location, vague test, unverified constant (absent → structural), non-mechanical
criterion, branch plan, failure handling, rollback, source citation, extension detail,
reconciliation recipe, lessons applied, task list, or milestones (the last two always
closable, never structural).

### 3.1 Re-audit
Walk the rubric again. Two passes maximum. Still failing → ask, or escalate to
`/roadmap-review` and halt the print.

### 3.2 Correct the head item's own register row (only if needed)
If the head item's status in the register is behind reality, correct **that one item**
through the provider, passing the `revision` you read. If the provider is read-only, or
`allowedWriters` does not name `next-dispatch`, do not attempt the write: report the
discrepancy and hand it to the user.

### 3.3 Regenerate the roadmap board (only when the head changed)
If 3.2 wrote to the register, regenerate a registered board so it shows the same head:

    "$HOME/.virtuoso/bin/virtuoso" generate_board --root .

Skip it when nothing was written or no `board` role is registered (creating one is
`/roadmap-review` D.7's job). A failure is reported, never a reason to stop the gate.

---

## Phase 3.5 — THE ENRICHMENT CHANGE

A Phase 3 edit is uncommitted. What happens next is `policy.git`:

| `policy.git.policy` | What this ceremony does |
|---|---|
| `read-only` | Report the edit and its paths. Someone else commits it. |
| `prepare-no-stage` | Leave it in the working tree; report the exact paths. |
| `explicit-path-stage` | `git add "<exact path>"`; verify the cached set; report. |
| `explicit-path-commit` | Stage the exact path and commit it. |
| `push` | As above, then push, subject to `policy.git.networkOperations`. |

If `policy.git.separationOfDuties` is true, the authoring actor does not commit the edit.
**Then verify from primary evidence** per the Phase 3.5 sections of
[references/enrichment.md](references/enrichment.md): the hand-off, and the checks that
only your paths are dirty and the enrichment is where you claim.

### Gate consequence

If the work will be executed from a branch cut off the default branch, and the
specification is not yet on that branch, repository readiness is **BLOCKED**: cutting from
it would start from a base missing its own specification. Name that as the blocker; do not
print "Ready".

---

## Phase 3.6 — PRE-FLIGHT RESOLUTION

Drive every check to a resolved state before composing the output.

| State | Action |
|---|---|
| **SATISFIED** | Record it. |
| **AUTO-COMPLETABLE** | Do the work now, then record it and say what was done. |
| **NEEDS A DECISION** | Ask a bounded question; complete it on the answer. |
| **EXTERNALLY BLOCKED** | Cannot be closed here (a pending prerequisite; a commit another actor must make). Surface the hand-off and set the verdict to **Not ready**. This is the only legitimate unresolved check at print time. |

### The pre-flight checklist

1. **Rubric** — universal checks plus extensions, re-confirmed against current state
   (locations drift between authoring and dispatch).
2. **Prerequisites** — from the provider. Pending → externally blocked.
3. **Specification reachable from the execution base** — Phase 3.5.
4. **Figures accurate** — computed through the provider at read time, with provenance.
5. **Register reflects reality** — the head item's own row, corrected if the provider
   permits; otherwise reported.
6. **Serialization** — read-only inspection finds no branch or worktree for this item in
   flight; one may mean a dispatch is already running. Ask before re-dispatching.
7. **Reconciliation recipe embedded**, filled, no placeholders left.
8. **Execution environment** — declared dependencies present.

A decision becomes a bounded question: the concern stated plainly, 2–4 options, one
recommended, and an escape hatch.

---

## Phase 4 — COMPOSE AND PRINT

### 4.1 Plain-language rules

- Lead with the item's **descriptive name**; the identifier is secondary.
- One to two bolded sentences answering what the work does and why it matters.
- Complete sentences, no fragments, no bare acronyms — expand on first use. Lead with news,
  not process.
- The "stranger test": someone who has never seen this project should understand what is
  about to happen.

### 4.2 Output format

**Before composing the print, read [references/kickoff-format.md](references/kickoff-format.md)**
— the full template, with the recipe inside the kickoff's one fence.

### 4.3 Pre-print verification

**Gate: print nothing until all ten checks in §4.3 of
[references/kickoff-format.md](references/kickoff-format.md) hold** — among them five
separate findings, a verdict matching them, every pre-flight item resolved, the recipe
filled inside the one block, and the Session line present.

---

## Edge cases

**When one applies, read [references/edge-cases.md](references/edge-cases.md)** for its
output and handling: **Stub at head** (halt → `/roadmap-review`); **Epic at head** (halt →
`/epic [ITEM-ID]`, or the existing packet's resume prompt); **Queue empty** (→
`/roadmap-review`); **No work register registered** (halt); **Structural gap** (bounded
question; halt on pause or escalation); **Prerequisites pending** ("Not ready", plus an
alternative dispatch if one qualifies); **Blocker escalation** (an issue document per
`policy.issues.targets`, then `/mid-dispatch-decision`); **No roadmap or specification
store** (halt; report, never replace, an absent target).
