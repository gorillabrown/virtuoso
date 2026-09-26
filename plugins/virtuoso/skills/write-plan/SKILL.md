---
name: write-plan
description: |
  MANUAL INVOCATION ONLY. The second half of Storyboard, then Write-Plan, then
  Virtuoso: turns an approved storyboard into dispatch-ready specifications for ad hoc
  work that has no plan yet. It always starts from the storyboard. With none, it runs
  /storyboard first. With one, it re-anchors on it, checks for drift, and returns
  there whenever something agreed is in question. It writes each item in
  roadmap-review's D.5.2 format against the shared readiness rubric and the live
  lessons, then runs next-pointer's readiness audit, pre-flight, and repository
  reconciliation against it. It holds the plan in the registered holding bay, never
  the roadmap or the register, which the next /roadmap-review reconciles. It then asks
  whether to execute now with the virtuoso skill, execute from another session, or hold
  for roadmap review. Triggered by "/write-plan", "write the plan", or "plan this out".
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
- **Effort levels** — low / medium / high / max. A property of the task's difficulty, never a ranking of whoever performs it.

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

# Write Plan

The second half of the ad hoc path: **Storyboard → Write-Plan → Virtuoso**
(`references/execution-paths.md`). This skill turns an approved storyboard into
dispatch-ready specifications for work that has no plan yet.

It applies the same standards as the roadmap path. Specifications are written in
roadmap-review's D.5.2 format, walk the shared rubric, apply the live lessons, pass
next-pointer's readiness audit and pre-flight, and carry a filled
repository-reconciliation recipe. What reaches the executor is the same thing a
roadmap dispatch delivers. The one difference is **where the plan waits**: in the
registered holding bay, not on the roadmap. Nothing here is roadmapping. The next
`/roadmap-review` reconciles the held entry, whether it has run or not.

**It is a continuation, not a fresh start.** Calling `/write-plan` always begins with
the storyboard. With no approved storyboard, it runs `/storyboard` first. With one, it
re-anchors on it, and it returns there whenever something that was agreed comes into
question.

**Announce at start:** "Using write-plan to turn the storyboard into a dispatch-ready
plan."

## Preflight — read-only registry check (run first)

Resolve the plugin through its launcher, then run the **read-only** check. It performs
discovery and validation with zero project writes.

**Unix-like shell**

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check

**Windows PowerShell**

    & "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check

Read the `virtuoso-status:` line and branch:

- `ready` — continue.
- `warning` — surface the findings and continue.
- `repair-needed` — **STOP.** Run `--mode repair` to produce the preview, show it, and
  apply it only with `--apply` after the user approves.
- `adoptable` — offer `--mode adopt`, which registers what exists in place.
- `none` — no registry, so there is no holding bay and no register to check
  prerequisites against. Offer `/virtuoso-init` and stop.
- `failed` — report the error verbatim and stop.

Then resolve what this skill reads and writes:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . holding --open
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor write-plan provider
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor write-plan items --all --json

Exit 3 naming `holdingBay` means the role is not registered. Show the entry the
message prints, and stop until the user registers it.

**This skill writes exactly one thing:** its held-plan file in the holding bay, meaning
the `## Plan` section and trail rows added through `holding --record`, plus that file's
persistence under `policy.git`. It **never** writes the roadmap, the live register, a
specification store, a sequence, a specification link, or the terminal ledger. The
register is read for prerequisites and impact, never written. If a step seems to need
one of those writes, it belongs to `/roadmap-review`.

## When to use

- Straight after `/storyboard` approves a dispatch-sized storyboard. This is the usual
  way in.
- `/write-plan <entry>` for a held entry: to plan one that was only storyboarded, to
  re-plan one after it was reopened, or to resume a planned entry from another session
  and execute it.

## Route instead

| Signal | Route |
|---|---|
| No approved storyboard for this work | `/storyboard`. This skill runs it for you (Step 0). |
| The entry is epic-scale | It stays held. The next `/roadmap-review` places it as `Path: epic`, then `/epic` charters it. |
| The entry reads `absorbed` | It is a roadmap item now. Use `/next-pointer`. |
| The work is already a roadmap item | `/next-pointer` if it is the head, otherwise `/roadmap-review` |
| The entry reads `in-flight` | Another session is executing it. Do not plan over it. |

## Operating principles

1. **The storyboard is the only record of what was agreed.** Every decision this skill
   needs goes into the storyboard's alignment record: a new decision, a correction, or an
   answer to a structural gap. The plan follows from that record, and never the other
   way round.
2. **Same bar as the roadmap path.** The rubric lives in
   `references/readiness-rubric.md`, and the format is roadmap-review's D.5.2. Readiness
   is next-pointer's five findings and its pre-flight resolution. No part of this skill
   restates or relaxes any of them.
3. **No roadmapping.** The holding bay only. Recommendations for placement, sequencing,
   and stale downstream items go in the held entry, for the review to act on.
4. **Hard gates.** You do not execute until the user approves the plan, and then only if
   they choose execution. Each approval covers the stage the user actually saw.
5. **Verify from primary evidence.** Read the code at every edit site, and read the git
   output. Never accept a summary.
6. **Bounded questions only.** Follow `references/actors-and-interaction.md`.

---

## Step 0 — Pull back into the storyboard (always first)

**No approved storyboard for this work** (none from this session, and no held entry)
→ run `/storyboard` from its first step. Continue here once it records `storyboarded`.

**A held entry**, the one just approved or one named with `/write-plan <entry>`:

1. Check it, and read its state:

       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . holding --check <entry>

   Route per the table above for `absorbed`, `in-flight`, `withdrawn`, `executed`, and
   epic-scale. For `planned`, go on to 2 (a re-plan, or a resume from another session).
2. **Re-anchor.** Restate the alignment record in three to five lines: outcome, frames,
   approach, and items. Then look for **drift** since the verdict's date:
   - commits at the expected edit sites (`git log --since=<date> -- <paths>`)
   - live lessons recorded since then
   - changes to the register items in the impact map
   - new held entries that overlap this one
3. **Confirm.** Straight after `/storyboard` in the same session, with no drift, a
   one-line restatement is enough. Otherwise, whenever the storyboard is from an earlier
   session or drift was found, ask: *"Is this still what we agreed?"* **(a)** Yes, plan
   it. **(b)** Something changed. Name it, and it goes back into `/storyboard` at the
   step it affects.
4. **Resuming a `planned` entry to execute it** (another session, or a later day): after
   the confirmation, walk the rubric again (Step 3) and rerun readiness (Step 5) against
   the current code. Enrich the plan in place, record `planned` again if it changed, and
   go to Step 8. If the plan no longer passes, it is re-planned from Step 1.

**Back to the storyboard, mid-plan.** At any later step, a question about intent,
scope, approach, or what done means is an alignment question. Reopen the storyboard at
the step it belongs to, record the answer there, and have the user re-approve the
storyboard (it is recorded as `storyboarded` again). Then resume the plan. Answering it
only inside the plan leaves the record of what was agreed behind.

## Step 1 — Gather what the plan answers to

- One provisional identifier per skeleton item:
  `"$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . holding --next-id`. Take
  consecutive numbers for an item set.
- The live lessons (`lessons --open`) and the standing rules at
  `policy.standingRules.source`.
- `policy.git` (read `references/git-policy.md`), `policy.rubric.extensions`,
  `policy.dependencies`.
- The code at every expected edit site. A site that does not exist, or does not match
  the storyboard, is either a closable gap or an alignment question. Decide which before
  you write anything.

## Step 2 — Write each specification

Write one specification per skeleton item, in prerequisite order, in roadmap-review's
**D.5.2 format**, headed `#### HB-<n> — Title`. On top of that format:

- **Done when** is derived from the confirmed frames. Each frame gives at least one
  mechanically verifiable row, with its command written in.
- **Prerequisites** name roadmap items by title and identifier, and held items by
  `HB-<n>`.
- **Source** cites the held entry's alignment record and the code references you read.
- **Origin:** `held plan — <entry> (HB-<n>), not yet on the roadmap`.
- **Review focus:** at most five inputs or conditions that the outcome implies but no
  test exercises yet, ordered by how likely each is to hurt someone. Each one gets a
  *Done when* row and its test, or an explicit out-of-scope line. An empty list means
  you checked and found nothing.
- **Interfaces** (item sets only): what each item consumes from an earlier one and
  produces for a later one, by exact name.
- **Lessons applied**, under the heading U9 reads.

Plan at item altitude. The task-by-task plan is built at execution time, in the
virtuoso skill's Phase 2, with the repository in front of it. Pre-written code steps go
stale, and the rubric does not require them.

## Step 3 — Walk the shared rubric

Walk `references/readiness-rubric.md` at its current version, plus the project's
declared extensions, exactly as roadmap-review's D.3.2 and next-pointer's Phase 2 do:

- **PASS** → record it.
- **CLOSABLE GAP** → close it by investigation, using the gap table those two share:
  stale location, vague test, unverified constant, non-mechanical criterion, missing
  branch plan, failure handling, rollback, source citation, extension detail, or
  lessons applied.
- **STRUCTURAL GAP** → this is a decision nobody has made. It goes back into the
  storyboard (Step 0). Never invent it here.

Run U9's mechanical half on each item:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --check <held plan> --item HB-<n>

Allow at most two enrichment passes. An item that still fails after two cannot be
planned. Tell the user which checks block it, and offer to reopen the storyboard or to
leave the entry `storyboarded` for the review.

## Step 4 — Self-review, as a stranger would read it

Fix what you find in place:

1. **Coverage.** Every confirmed frame appears as a *Done when* row or a *Review focus*
   line. Every skeleton outcome has a specification.
2. **Placeholders.** No "TBD", no "handle edge cases", no "similar to above", and no
   "add validation" without the actual content.
3. **Consistency.** Names, paths, and interfaces agree across sections and across
   sibling items.
4. **Ambiguity.** No requirement a reader could reasonably take two ways. Pick one
   reading and state it.

## Step 5 — Readiness, pre-flight, and the pointer

Run next-pointer's readiness audit (its Phase 2), its pre-flight resolution (its Phase
3.6), and its repository reconciliation against this held plan. Report readiness as the
five separate findings, never blended:

| Finding | For a held plan |
|---|---|
| **Specification** | The rubric result from Step 3 |
| **Prerequisites** | Roadmap prerequisites are terminal, through the provider. A prerequisite in another held entry reads `executed`. One inside this entry is met by running the set in prerequisite order. |
| **Repository** | Detected state; no in-flight branch or worktree on these edit sites; the held plan is reachable from the execution base |
| **External register** | Whether it could be read for prerequisites and impact. Say plainly that nothing is written to it. |
| **Execution environment** | Declared dependencies, tooling, credentials, and access |

Drive every pre-flight check to **satisfied**, **completed now**, **decided** (by a
bounded question), or **externally blocked**. Only the last may remain open, and it
makes the plan *not executable now*.

Fill next-pointer's reconciliation recipe with detected values: the remote, the default
branch, and the branch name from `policy.git.branchNameTemplate`. Include only steps
the project's git policy permits, and leave no placeholders. Then compose the pointer.
It carries the origin line, and the filled recipe sits inside the same fenced block, as
next-pointer's does, so one copy hands an executing session all of it:

```
[Item title]  (HB-<n>)
Origin: held plan — [entry] (HB-<n>), not yet on the roadmap
Effort: [size]
Branch: [branch] from [default branch] @ [sha that carries the held plan, or "uncommitted — see git status"]
Specification: [holding bay path]/[entry].md#HB-<n>
Status: planned — held | Prerequisites: [descriptive names, met/pending]
Readiness: specification ✓ · prerequisites ✓ · repository ✓ · register ✓ · environment ✓

[the filled recipe, from its Step 0 header down]

# Halt on any STOP and report the git output. A halt is a dispatch blocker,
# not something to improvise around.
```

## Step 6 — The plan gate

Show the user the plan: a two-line summary per item, the five findings, and the pointer.
Ask them to **approve**, **revise**, or **stop**. A revision that changes what was
agreed goes back to the storyboard first.

## Step 7 — Hold the plan

1. Write the `## Plan` section into the held entry: **Readiness** (the five findings),
   **Pointer** (one fenced block that carries the repository-reconciliation recipe to
   run first), then the **Specifications**, one `#### HB-<n> — Title` per item.
2. Check the entry, then record it (preview first, then `--apply`):

       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . holding --check <entry>
       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor write-plan holding --record <entry> --state planned --note "<HB ids; rubric passed>" --apply

3. Persist the file as `policy.git` permits, using the five-level table from
   next-pointer's Phase 3.5, with the exact path staged. If the work will run on a
   branch cut from the default branch, and the held plan is not yet on that base,
   repository readiness is **BLOCKED** until it is. State that, as next-pointer does.

## Step 8 — Ask how to proceed

Offer execution **only** when all five findings pass and nothing is externally blocked.
Otherwise, name the blocker by its descriptive name, and hold the plan.

> **[Title]** is planned and nothing blocks it. How do you want to run it?
> - **(a) Execute now, here, with Virtuoso** *(recommended when [the reason: e.g. it is
>   small, the context is warm, and the branch base already carries the plan])*
> - **(b) Execute from another session.** You might use a command-line session, a fresh
>   session, or a cloud session. I'll print a kickoff prompt, and the plan stays held
>   until that session picks it up.
> - **(c) Hold for roadmap review.** The next `/roadmap-review` absorbs it onto the master
>   roadmap, and `/next-pointer` dispatches it from there.
> - **(d) Withdraw it**, with a reason.

Recommend (b) over (a) when this session is heavy with context the executor does not
need, or when `policy.git.separationOfDuties` means the planner must not also implement.

An item set runs as one unit: every item, in prerequisite order, in one run. If the
user wants only part of it now, the rest waits for the review. Offering "run HB-3 now,
hold HB-4" would split one entry across two paths.

### (a) Execute now

1. Record the start of execution:
   `--actor write-plan holding --record <entry> --state in-flight --note "executing here: <branch>" --apply`.
2. Run the pointer's repository-reconciliation recipe. Halt on any STOP it contains, and
   report the git output.
3. Load the **virtuoso** skill, and hand it the pointer and the specifications as the
   dispatch spec. The sprint identifier is the `HB-<n>`.
4. Close out with `/pointer-closeout`. It sees the held-plan origin, writes the close-out
   report and the lessons, and records the entry `executed`. The register and the
   terminal ledger are written when the review absorbs the entry.
5. If execution stops without completing, return the entry to the bay with
   `--state planned --note "stopped: <why>; <what is preserved, where>"`. Name any item
   of a set that did close out, so the review absorbs it as completed.

### (b) Another session

Print one fenced block the next session can start from. That session has no memory of
this one:

```
Run /write-plan [entry] to resume the held plan at [holding bay path]/[entry].md.
It re-anchors on the storyboard, re-runs the readiness gate against the current code,
and then executes [HB ids] under the virtuoso skill if you choose to.
Close out with /pointer-closeout.
If a roadmap review has absorbed the entry in the meantime, it is a roadmap item now:
use /next-pointer instead.
```

The entry stays `planned`. The session that resumes it records `in-flight` when it
starts.

### (c) Hold for roadmap review

Nothing more to write. End with the entry's path and state, and tell the user that the
next `/roadmap-review` reconciles it.

### (d) Withdraw

`--actor write-plan holding --record <entry> --state withdrawn --note "<reason>" --apply`.

---

## Output — the summary

```
# Write Plan — [Title]

**[One-to-two-sentence plain-language summary.]** *(held as [entry] · [HB ids])*

| | |
|---|---|
| Storyboard | aligned YYYY-MM-DD[; re-anchored — no drift / drift folded in] |
| Specifications | [HB-n — title: rubric PASS], … |
| Readiness | specification ✓ · prerequisites ✓ · repository ✓ · register ✓ · environment ✓ |
| Lessons applied | [ids, or none apply — N read] |
| Held | [entry] — planned |
| Decision | execute now / another session / hold for review / withdrawn |

*Source: [register] via [provider], snapshot [timestamp] — read only.*
```

## Red flags

| Thought | Reality |
|---|---|
| "The storyboard is from yesterday, so I'll just write the plan" | Re-anchor first. Code moves, and so do lessons. |
| "This gap is small, so I'll decide it in the spec" | A decision nobody made is an alignment question. It goes back to the storyboard. |
| "I'll add the item to the register so next-pointer can see it" | That is roadmapping. The review absorbs the held entry. |
| "The downstream spec is stale, so I'll fix it" | Another item's specification is not yours to edit. The held entry records it for the review. |
| "Ad hoc work doesn't need lessons applied" | U9 applies to every specification. The ad hoc path has the same bar. |
| "It passed, so I'll start executing" | Execution needs the user's choice (Step 8), and the in-flight record. |

## Integration

- `references/execution-paths.md` — the destination this plan must reach, shared with
  `/next-pointer` and `/epic`.
- `/storyboard` — where every plan starts, and where every alignment question returns.
- `virtuoso` — the execution framework.
- `/pointer-closeout` — closes the run in held-plan mode.
- `/roadmap-review` — absorbs the held entry onto the master roadmap, or withdraws it.
