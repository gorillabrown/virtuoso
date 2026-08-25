---
name: next-pointer
description: |
  MANUAL INVOCATION ONLY. The dispatch gate. Reads the next eligible
  work item from the project's configured work-register provider,
  finalizes its specification against the shared readiness rubric,
  drives every pre-flight check to a resolved state, and prints a
  dispatch pointer with a repository-reconciliation recipe matched to
  the project's declared git policy. Triggered by "/next-pointer",
  "next pointer", "show next", or "what's next". Does NOT replan,
  re-sequence, or author new items — that is /roadmap-review.
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

# Next Pointer

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
The dispatch gate. It reads the next eligible item **through the configured
provider**, finalizes its specification so it can be executed without inventing
decisions, completes every pre-flight check (or elevates it as a question), and
prints:

1. **A plain-language summary** of what is next, by descriptive name
2. **Readiness findings**, reported as five separate results
3. **The dispatch pointer**, including a repository-reconciliation recipe matched
   to the project's declared git policy

A specification must be complete because an incomplete one cannot be executed
without inventing the missing decisions — by anyone, at any capability. That is
the reason, and the only reason. This skill never asserts a capability ranking
between hosts, products, or models.

**Bookend with `/pointer-closeout`.** This skill opens a dispatch; that one
closes it, transactionally.

## Resolve the register before anything else

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor next-pointer provider
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor next-pointer next --json

**The absence of any particular file is never a hard stop** (redesign item 37).
The register may be a CSV, a Markdown table, a spreadsheet, a connector-backed
task manager, an issue tracker, a database, or a read-only snapshot. What matters
is what the provider can do:

| To do this | Capability required |
|---|---|
| find the next eligible item | `next-eligible` (or `list-active` + `read-sequence`) |
| verify prerequisites | `read-prerequisites` |
| report effort-based figures | `read-effort` |
| record a status change during pre-flight | `write-status` |
| store a specification link | `store-spec-link` |

Negotiate these **before** planning the run. If the provider cannot serve one you
need, say so up front, and adjust: a read-only snapshot still supports the whole
read path and produces a complete pointer; it simply cannot record a pre-flight
status correction, which you then hand to the user instead.

If the register is served through the **compatibility adapter** (a legacy
`sprintCatalog` with no `workRegister` role), say so in the output: reads work,
writes do not, and registering a `workRegister` role is the fix.

If the snapshot is **stale**, print its age and say plainly that the pipeline
figures may not reflect current state.

## When to use

- About to dispatch and want the specification finalized
- Checking what is queued before committing to a dispatch
- Quick "where am I + what is next"

## Do NOT use this for

- A full status briefing — use `/roadmap-status`
- Replanning, re-sequencing, or authoring new items — use `/roadmap-review`
- Dispatching when the head item is still a stub — this skill refuses

## Invocation

Manual only: `/next-pointer`, "next pointer", "show next", "what's next".

## Glossary

- **Work item** — a discrete unit of work with clear acceptance criteria.
- **Stub** — a placeholder: id, title, maybe a one-line gist.
- **Specification** — the full item card, wherever `policy.roadmap.specStorage`
  puts it.
- **Dispatch-ready** — a specification that passes the shared readiness rubric.
- **Pointer** — the code-boxed block telling the dispatcher exactly where the
  specification lives, plus its immediate context.
- **Buffer** — the dispatch-ready items carried ahead, sized by
  `policy.roadmap.dispatchBuffer`.
- **Conveyor belt** — the sequenced list of active items in the live register.

## Operating principles

1. **Specification finalization is the primary job.** An item that passes through
   this skill is dispatch-ready by the shared rubric, or it does not pass.
2. **The provider is the register.** Never open a register file directly. Never
   treat a mirror, a generated report, or an archive as the live pipeline.
3. **Writes are narrowly scoped.** This skill may enrich the head item's
   specification and correct that item's own row in the live register. It does
   **not** re-sequence, add items, or edit other items' specifications — that is
   `/roadmap-review`. Every write goes through the provider with the `revision`
   that was read, and only when the role's `allowedWriters` names `next-pointer`.
4. **Hard halt on a stub at the head.** No partial dispatch.
5. **Hard halt on a structural gap.** A deferred design decision or unresolved
   scope question stops the print and becomes a bounded question. Never improvise
   the decision.
6. **Three-section output, in this order:** plain-language summary, readiness
   findings and figures, code-boxed pointer.
7. **Descriptive names first** (item 38). Every reference to an item leads with
   its human title; the internal identifier appears second, in parentheses or a
   trailing field. An id alone is never the whole explanation.
8. **Bounded questions only**, per `references/actors-and-interaction.md`. Most
   gaps close by investigation; escalate only a real decision.
9. **Git behaviour is `policy.git`.** Read `references/git-policy.md`. What this
   skill may do to the repository — nothing, prepare, stage, commit, or push —
   is the project's declaration, not a fixed rule. Read-only inspection is
   available under every policy; run it lock-free
   (`GIT_OPTIONAL_LOCKS=0 git --no-optional-locks …`).
10. **Verify from primary evidence.** Never accept "tree clean" or "reconciled"
    as a claim; read the underlying output.
11. **Pre-flight checks are resolved, not noted.** Every check ends resolved —
    satisfied, completed now, explicitly accepted by the user, or named as the
    blocker that flips the verdict. "Noted, non-blocking" under a Ready verdict
    is forbidden.
12. **Every pointer carries a reconciliation recipe** appropriate to the project's
    git policy. It preserves uncommitted work, halts on divergence rather than
    forcing, and never prescribes deleting a lock file automatically.

---

## Dispatch-Readiness Rubric

**One rubric, one home:** the plugin's `references/readiness-rubric.md` (v1.0 —
universal checks U1–U8 plus the project's declared extensions). Open it and apply
it. `/roadmap-review` applies the same file; the two cannot disagree because
there is only one.

### Report readiness as five separate findings (item 39)

Never collapse these into a single verdict:

| Finding | What it covers |
|---|---|
| **Specification readiness** | U1–U4, U6, U7 plus declared project extensions |
| **Prerequisite readiness** | U5, resolved against the live register through the provider |
| **Repository readiness** | U8 plus the repository's actual current state, under `policy.git` |
| **External-register readiness** | can the register be read; is the snapshot fresh; does the provider support the mutations this dispatch needs |
| **Execution-environment readiness** | tooling, dependencies, and access the work requires |

Each is independently PASS / GAP / BLOCKED, each with its own reason. A dispatch
is ready only when all five pass.

---

## Inputs

1. The registry — the authority for every path and permission.
2. The live work register, through its provider.
3. The roadmap or specification store, resolved through its registered role.
4. The most recent review artifacts in the registered reviews directory — for the
   "last review" timestamp and the pace read.
5. The standing rules, at `policy.standingRules.source`.
6. The terminal ledger — for what is already final.
7. The project codebase — for rubric verification.
8. `policy.git` — for what this ceremony may do to the repository.

## Outputs

1. One formatted briefing in chat (the three-section output).
2. Possibly: enrichment edits to the head item's specification, in place.
3. A reconciliation recipe embedded in the pointer, matched to `policy.git`.
4. Possibly: a corrected status for the head item in the live register, written
   through the provider.
5. Possibly: bounded questions for any check needing a decision.
6. Possibly: an issue document for a blocker, routed per `policy.issues.targets`.

---

## Repository reconciliation

The recipe below is a **template**. Fill it from `policy.git` and from the
repository's actual state. Never emit a placeholder, and never emit a step the
project's policy does not permit.

### First, detect — do not assume

```
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks rev-parse --is-inside-work-tree

# Remote: policy.git.remote if set; else the current branch's upstream remote;
# else the single remote if there is exactly one; else ASK. Never assume "origin".
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks remote

# Default branch: policy.git.defaultBranch if set; else
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks symbolic-ref --quiet --short refs/remotes/<remote>/HEAD
#   else `git remote show <remote>` → "HEAD branch"; else the current branch.
#   Never assume "main".

# Worktrees: distinguish the primary tree from a dedicated execution worktree.
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks worktree list
```

**There may be no remote at all.** A local-only repository is fully supported.
Unless `policy.git.requireRemote` is true, record "no remote" as a fact and skip
every network step. Fetching and pushing are governed by
`policy.git.networkOperations` (`ask` by default): surface the operation and get
approval rather than running it silently, and treat offline as a normal state.

### The recipe

```
# ── Step 0: REPOSITORY RECONCILIATION — before any implementation ──

# 0a. Scope the working tree.
git status --porcelain
#   Compare against the EXPECTED dirty set for this item.
#   Paths inside it   → fine; they are this dispatch's own work.
#   Paths outside it  → REPORT them and leave them alone. An unrelated dirty
#                       path in the primary tree does NOT invalidate a separate,
#                       clean execution worktree (policy.git.worktreeAware).
#   Never stash, reset, clean, or destructively checkout to "tidy up".
#   If .git/index.lock exists: REPORT it and check whether a git process is
#   actually running. Never delete it automatically.

# 0b. Sync the default branch (only if a remote exists AND
#     policy.git.networkOperations permits it).
git fetch <remote> --prune
git switch <default>
git merge --ff-only <remote>/<default>
#   Diverged → STOP. No force, no reset --hard, no unauthorized rebase.
#   SANCTIONED FALLBACK (flag it; never silent): branch directly off the remote
#   tip and leave the local default branch for a human:
#       git switch -c <branch-name> <remote>/<default>
#   Then skip 0c. Report that the local default branch is still diverged.

# 0c. Create the work branch from the reconciled default branch.
git switch -c <branch-name> <default>
#   Already exists → confirm its base is current; if stale, STOP and report.

# 0d. Verify.
git status --porcelain                       # → only the expected set
git branch --show-current                    # → <branch-name>
git rev-list --count <default>..<remote>/<default>   # → 0  (skip if no remote)
```

**Branch cleanup is maintenance, not a prerequisite** (item 68). Report stale or
`[gone]` branches and unpruned worktrees as housekeeping. Do not gate this
dispatch on removing them, and never use `git branch -D` or `git worktree remove
--force` as part of a dispatch.

**During the work**, under whatever `policy.git.policy` permits: stage explicit
paths only (never `git add .` / `-A`); verify the cached set matches the expected
set before committing; no destructive flags; no force-push without explicit
authorization.

**Halt semantics.** Any STOP above halts the implementation agent, which reports
the exact git output and escalates. A halt is a dispatch blocker, surfaced like a
failed prerequisite — never improvised around.

---

## Phase 1 — READ AND IDENTIFY

### 1.1 Determine the head item

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor next-pointer next --json

The provider returns the next item whose prerequisites are all terminal, in
sequence order, together with its provenance. If the provider lacks
`next-eligible`, fall back to `items` and compute it the same way.

If there are no active items → **Queue empty** edge case.

### 1.2 Hard-halt check (stub at head)

If the head item's specification state is not `full-spec` → STOP and branch to
the **Stub at head** edge case.

### 1.3 Locate the specification

Per `policy.roadmap.specStorage`: inline in the roadmap document, in a file under
`policy.roadmap.specDirectory`, or in the external system named by the item's
`spec_link`. Resolve every one of those through the registry.

### 1.4 Figures, with provenance

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . kpis --json

Report each metric with the provider, source, and snapshot time it came from.
**A metric the data cannot support is reported as `not computable`, with the
missing inputs named** — never estimated, never quietly omitted. Effort-weighted
figures need an effort value on every item and a scale entry for every value; if
either is missing, the figure is not computable and the message says which items.

Buffer health compares the count of dispatch-ready active items against
`policy.roadmap.dispatchBuffer`. If the buffer is 0, report "eager specification
disabled" rather than a ratio.

"Last review" is the newest artifact in the registered reviews directory. Pace
comes from the most recent assessment; if none exists, pace is not computable.

**Never read a generated report or spreadsheet cache to obtain any of this.** A
generated artifact is a presentation output; the provider is the source.

### 1.5 Standing rules

Read the rules at `policy.standingRules.source` and match them against the head
item's domain. The rule identifiers are the project's own
(`policy.standingRules.ids`); this skill never invents or hardcodes one. Pick the
one or two most relevant.

---

## Phase 2 — READINESS AUDIT

Walk `references/readiness-rubric.md` against the head item's specification, then
sort every result into the five findings.

For each check:
- **PASS** → record it.
- **CLOSABLE GAP** → a verifiable assertion investigation can settle. Flag for
  Phase 3.
- **STRUCTURAL GAP** → a real deferred decision. Halt the print and ask.

### 2.1 Prerequisite readiness

For each prerequisite, resolve its state **through the provider**:
- terminal (`completed`, `dissolved`, `superseded`) → met
- `queued` / `in-flight` / `blocked` → pending
- not present in the register → unknown; check the terminal ledger before
  concluding, and report "unknown" if it is in neither

Any pending or unknown prerequisite makes prerequisite readiness fail. Still
produce the full output, with the verdict "Not ready" and the reason named, and
offer a dispatchable alternative deeper in the queue if one exists.

### 2.2 External-register readiness

- Can the register be read at all?
- Is the snapshot fresh (or is it stale, and by how much)?
- Does the provider support every mutation this dispatch will eventually need
  (`write-status` for the in-flight transition, `record-completion` for close-out)?
- Is the register being served through the compatibility adapter?

Report each of these plainly. A dispatch against a read-only register is
permissible — but say so, so nobody expects a status write later.

### 2.3 Execution-environment readiness

Tooling, runtime dependencies (`policy.dependencies`), credentials, and access
the work requires. A missing dependency is a finding here, not a surprise
mid-implementation.

---

## Phase 3 — ENRICHMENT (only if Phase 2 flagged closable gaps)

Close each gap by investigation and update the specification in place. Be
surgical: do not rewrite sections that do not need it; preserve existing
structure and formatting.

| Gap | How to close |
|---|---|
| Stale location reference | Search for the symbol; read the file; correct the reference. |
| Vague test reference | Read the test file; insert the exact name and assertion. |
| Unverified constant | Search; record the current value and its location. If it does not exist, this is a structural gap. |
| Non-mechanical acceptance criterion | Rewrite it as a command or assertion. |
| Missing branch plan | Apply `policy.git.branchNameTemplate`. |
| Missing failure handling | Enumerate known failure modes; add "if X, do Y". |
| Missing rollback | State the revert path this project's git policy permits. |
| Missing source citation | Find it; link it with an anchor. |
| Missing project-extension detail | Consult the project's own precedent, not another project's. |
| Missing reconciliation recipe | Fill the template above from `policy.git` and detected repository state. Pure text; no git mutation. |

### 3.1 Re-audit
Walk the rubric again. Two passes maximum. Still failing → ask, or escalate to
`/roadmap-review` and halt the print.

### 3.2 Correct the head item's own register row (only if needed)
If the head item's status in the register is behind reality, correct **that one
item** through the provider, passing the `revision` you read. If the provider is
read-only, or `allowedWriters` does not name `next-pointer`, do not attempt the
write: report the discrepancy and hand it to the user.

---

## Phase 3.5 — THE ENRICHMENT CHANGE

If Phase 3 edited a specification, that edit is uncommitted. What happens next is
`policy.git`, not a fixed rule:

| `policy.git.policy` | What this ceremony does |
|---|---|
| `read-only` | Report the edit and its paths. Someone else commits it. |
| `prepare-no-stage` | Leave it in the working tree; report the exact paths. |
| `explicit-path-stage` | `git add "<exact path>"`; verify the cached set; report. |
| `explicit-path-commit` | Stage the exact path and commit it. |
| `push` | As above, then push, subject to `policy.git.networkOperations`. |

If `policy.git.separationOfDuties` is true, the actor that authored the edit does
not commit it: emit the commit as a hand-off to another actor, with explicit
paths only. This is an *optional project policy* — it is not implied by which
product or model is running the ceremony, and it never applies unless the project
declares it.

### Verify from primary evidence

```
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks status -sb
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks diff --stat
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks show HEAD:"<spec path>" | grep -c "<distinctive token>"
```

Confirm the only dirty paths are the ones you edited, and that the enrichment is
actually present where you claim it is. If a report says "clean" but the
enrichment is not on `HEAD`, state the contradiction: nothing was lost — the edit
is still in the working tree — it simply has not been committed yet.

### Gate consequence

If the work will be executed from a branch cut off the default branch, and the
specification is not yet on that branch, repository readiness is **BLOCKED**:
cutting from it would start from a base missing its own specification. Name that
as the blocker; do not print "Ready".

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

1. **Rubric** — every universal check plus declared extensions, re-confirmed
   against current state (locations can drift between authoring and dispatch).
2. **Prerequisites** — from the provider. Pending → externally blocked.
3. **Specification reachable from the execution base** — Phase 3.5.
4. **Figures accurate** — computed through the provider at read time, with
   provenance. There is no cache that can go stale.
5. **Register reflects reality** — the head item's own row, corrected if the
   provider permits; otherwise reported.
6. **Serialization** — no branch or worktree for this item is already in flight.
   Read-only inspection; an in-flight branch means a dispatch may already be
   running. Ask before re-dispatching.
7. **Reconciliation recipe embedded**, filled from `policy.git` and detected
   state, with no placeholders left.
8. **Execution environment** — declared dependencies present.

A check needing a decision becomes a bounded question with the concern stated
plainly, 2–4 options, one recommended, and an escape hatch.

---

## Phase 4 — COMPOSE AND PRINT

### 4.1 Plain-language rules

- Lead with the item's **descriptive name**. The identifier is secondary.
- One to two sentences, bolded, answering what the work does and why it matters.
- Complete sentences. No fragments. No bare acronyms — expand on first use.
- Lead with news, not process.
- The "stranger test": someone who has never seen this project should understand
  what is about to happen.

### 4.2 Output format

```
# Dispatch Pointer — [Item title]

## What's next

**[One-to-two-sentence plain-language summary: what the work does and why it
matters.]** *(item [ITEM-ID])*
- *Optional sub-bullet: adaptation, risk, or upstream consideration.*

## Readiness

| Finding | Result | Reason |
|---|---|---|
| Specification | PASS / GAP / BLOCKED | … |
| Prerequisites | … | … |
| Repository | … | … |
| External register | … | … |
| Execution environment | … | … |

## Pipeline

| Metric | Value |
|---|---|
| Dispatch-ready items remaining (incl. this one) | N / [policy buffer] — [healthy / low / critical / empty / eager spec disabled] |
| Items to end of current group | X *(omit if the project uses no grouping)* |
| Items to finish line | Y — ~Z% remaining by effort *(or: not computable — [missing inputs])* |
| Prerequisites for this item | all met / pending: [descriptive names] |
| Last review | N days ago |
| Pace | On track / Behind / Ahead — [reason] *(or: not computable)* |

*Source: [register] via [provider], snapshot [timestamp][ — STALE: reason].*

## Pointer

\```
[Item title]  ([ITEM-ID])
[Group / lane, if the project uses them]
Effort: [size]
Branch: [branch-name] from [default branch] @ [sha carrying the specification]
Specification: [resolved location]
Status: next up (not in flight) | Prerequisites: [descriptive names, met/pending]
Readiness: specification ✓ · prerequisites ✓ · repository ✓ · register ✓ · environment ✓
\```

## Repository reconciliation — run this FIRST

\```
[the filled recipe: detected remote and default branch, no placeholders,
 only steps this project's git policy permits]
\```

Halt on any STOP and report the git output — a halt is a dispatch blocker, not
something to improvise around.

## Standing rules that apply
- **[project rule id] — [short title].** [One-sentence statement.]

## Pre-flight

- [resolved] Readiness rubric ([universal + extensions]) re-confirmed against current state
- [resolved] Prerequisites
- [resolved] Specification reachable from the execution base
- [resolved] Figures computed through the provider, with provenance
- [resolved] Register reflects reality
- [resolved] Serialization — no in-flight branch or worktree for this item
- [resolved] Reconciliation recipe embedded and filled
- [resolved] Execution environment

[Ready to dispatch — all five readiness findings pass.]
| [Not ready — [the named open item].]
```

### 4.3 Pre-print verification

1. Does the summary pass the stranger test, and lead with the descriptive name?
2. Are all five readiness findings reported separately?
3. Is every figure either a value with provenance, or explicitly *not computable*
   with its missing inputs named?
4. Are met/pending markers consistent across the table, the pointer, and pre-flight?
5. Does the verdict match the findings?
6. If enrichment ran, did the re-audit pass?
7. Is the recipe filled with real detected values — remote, default branch, branch
   name — and does it contain only steps `policy.git` permits?
8. If a specification edit is still unreachable from the execution base, is
   repository readiness BLOCKED and the verdict "Not ready"?
9. Is every pre-flight item resolved? Under a Ready verdict there are no open
   items at all.

---

## Edge case: Stub at head

```
# Cannot Dispatch — Stub at Head

The item at the head of the conveyor belt has no specification.

## Buffer status

| Seq | Item | Specification |
|---|---|---|
| 1 | [Title] ([ID]) | stub |
| 2 | [Title] ([ID]) | stub |

*Source: [register] via [provider], snapshot [timestamp].*

## Required action

Run **/roadmap-review** to author specifications up to the project's dispatch
buffer ([policy.roadmap.dispatchBuffer]). Then run /next-pointer again.
```

---

## Edge case: Queue empty

```
# Finish Line Reached

No active items remain in the work register.

## Status

- Last completed: [Title] ([ID]) on [date]
- Terminal records: [N]
- Finish line: [tier] — reached.

*Source: [register] via [provider], snapshot [timestamp].*

## Required action

Run **/roadmap-review** to introduce and plan new work.
```

---

## Edge case: No work register registered

```
# Cannot Dispatch — No Work Register

This project has not registered a `workRegister` role, so there is no live
pipeline to read.

## Required action

Register one in `Virtuoso/workspace-layout.json`. It can be a local CSV or
Markdown table, a spreadsheet, a connector-backed task manager, an issue tracker,
a database, or a read-only snapshot. Run
`virtuoso_preflight.py --mode repair` to preview the registry change.
```

If a legacy `sprintCatalog` exists, note that reads are available through the
compatibility adapter in the meantime, but nothing can be written back.

---

## Edge case: Structural gap

Halt the print and ask a bounded question. Example:

> The specification for **[Item title]** defers a decision the implementation
> agent should not be making: which secondary channel to gate on. Pick:
> - (a) Gate on the primary channel only *(recommended — matches the precedent in
>   [close-out])*
> - (b) Gate on both channels
> - (c) Pause — you will update the specification yourself
> - (d) Escalate to /roadmap-review

Capture the decision, update the specification in place, and continue to Phase 4.
On (c) or (d), halt.

---

## Edge case: Prerequisites pending

Run the full output with prerequisite readiness failing, the pending items named
**by descriptive name**, and the verdict "Not ready".

If a deeper item is dispatchable (specified, prerequisites met), add:

```
## Alternative dispatch

**[Title]** ([ID]) at sequence [N] has all prerequisites met and is dispatchable
now. Skipping ahead is appropriate only when the head item's blocker is external
(waiting on data, waiting on a person); otherwise hold the head and resolve it.
```

If the user takes the alternative, re-run Phases 2–3 against that item first.

---

## Edge case: Blocker escalation

A stop, hold, or block becomes an issue document routed per
`policy.issues.targets`:

- `local` — write it into the registered `issues` directory using
  `policy.issues.filenameTemplate`.
- `external` — create it in the tracker named by `policy.issues.externalRole`,
  through the host's connector, and record the identifier it returns.
- both — do both and cross-reference.

Then route to `/mid-dispatch-decision` by path or identifier.

---

## Edge case: No roadmap or specification store

```
# Cannot Dispatch — No Specification Store

The `roadmap` role is not registered, or its registered target is absent.

## Required action

A registered-but-absent target is reported, never replaced. Either point the role
at the real document (run `virtuoso_preflight.py --mode repair` to preview the
registry change) or create the document at the registered path, then run
/roadmap-review.
```
