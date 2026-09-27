---
name: write-plan
description: |
  MANUAL INVOCATION ONLY. PLANNING ONLY, never execution. Step two of the ad hoc path:
  Storyboard scopes, Write-Plan writes the full plan, and only the virtuoso skill
  executes. It turns storyboard's approved draft stub into full specifications, ready
  for implementation. It always starts from the storyboard: with none, it runs
  /storyboard first; with one, it re-anchors, checks for drift, and returns there
  whenever something agreed is in question. It writes each item in roadmap-review's
  D.5.2 format against the shared readiness rubric and the live lessons, runs
  next-pointer's readiness audit and pre-flight, fills in the reconciliation recipe,
  and works out each item's exact slot in roadmap order. It holds the plan in the
  registered holding bay, never the roadmap or the register; the next /roadmap-review
  applies the slot. It never executes: it hands the plan to the virtuoso skill, here or
  in another session, or holds it for review. Triggered by "/write-plan", "write the
  plan", "write the spec", or "plan this out".
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

Step two of the ad hoc path (`references/execution-paths.md`):

| Step | Skill | Produces |
|---|---|---|
| 1. Scope | `/storyboard` | a question-and-answer scoping conversation, ending in an approved draft stub |
| **2. Plan** | **`/write-plan` — this skill** | **the full specification, ready for implementation, with its exact slot in roadmap order** |
| 3. Execute | the `virtuoso` skill | the work, checked first against upstream, downstream, and in-flight work |

This skill turns the storyboard's approved draft stub into dispatch-ready specifications
for work that has no plan yet.

**Planning only.** This skill writes the full plan and stops there. It **never
executes**: it records no `in-flight`, runs no reconciliation recipe, creates no work
branch, edits no edit site, and starts no part of the change. All of that belongs to the
`virtuoso` skill, the only skill that executes, which picks the plan up from the
hand-off in Step 8.

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
  re-plan one after it was reopened, or to re-verify a planned entry whose code or
  roadmap has moved before handing it to the `virtuoso` skill.

## Route instead

| Signal | Route |
|---|---|
| No approved storyboard for this work | `/storyboard`. This skill runs it for you (Step 0). |
| The entry is epic-scale | It stays held. The next `/roadmap-review` places it as `Path: epic`, then `/epic` charters it. |
| The entry reads `absorbed` | It is a roadmap item now. Use `/next-pointer`. |
| The work is already a roadmap item | `/next-pointer` if it is the head, otherwise `/roadmap-review` |
| The entry reads `in-flight` | The `virtuoso` skill is executing it, in this session or another. Do not plan over it. |
| The user wants the planned work built | The `virtuoso` skill, from the held entry (Step 8). This skill does not build. |

## Operating principles

1. **The storyboard is the only record of what was agreed.** Every decision this skill
   needs goes into the storyboard's alignment record: a new decision, a correction, or an
   answer to a structural gap. The plan follows from that record, and never the other
   way round.
2. **Same bar as the roadmap path.** The rubric lives in
   `references/readiness-rubric.md`, and the format is roadmap-review's D.5.2. Readiness
   is next-pointer's five findings and its pre-flight resolution. No part of this skill
   restates or relaxes any of them.
3. **No roadmapping.** The holding bay only. The item's exact slot in roadmap order,
   its sequencing, and the stale downstream items go in the held entry, for the review
   to apply.
4. **Hard gates, and no execution.** Each approval covers the stage the user actually
   saw. Approving the plan approves the hand-off, not a start of work here: this skill
   never executes, and nothing runs until the `virtuoso` skill picks the plan up.
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
4. **Re-verifying a `planned` entry** (a later day, another session, or the `virtuoso`
   skill sent it back because the code or the roadmap moved): after the confirmation,
   walk the rubric again (Step 3) and rerun readiness and placement (Step 5) against the
   current code and roadmap. Enrich the plan in place, record `planned` again if it
   changed, and go to Step 8 to hand it off. If the plan no longer passes, it is
   re-planned from Step 1.

**Back to the storyboard, mid-plan.** At any later step, a question about intent,
scope, approach, or what done means is an alignment question. Reopen the storyboard at
the step it belongs to, record the answer there, and have the user re-approve the
storyboard (it is recorded as `storyboarded` again). Then resume the plan. Answering it
only inside the plan leaves the record of what was agreed behind.

## Step 1 — Gather what the plan answers to

- One provisional identifier per draft-stub item:
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

Write one specification per draft-stub item, in prerequisite order, in roadmap-review's
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
   line. Every draft-stub item has a specification.
2. **Placeholders.** No "TBD", no "handle edge cases", no "similar to above", and no
   "add validation" without the actual content.
3. **Consistency.** Names, paths, and interfaces agree across sections and across
   sibling items.
4. **Ambiguity.** No requirement a reader could reasonably take two ways. Pick one
   reading and state it.

## Step 5 — Readiness, pre-flight, roadmap placement, and the pointer

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
makes the plan *not executable now*. "Completed now" covers planning work only, such as
persisting the held plan. Nothing that starts the change is completed here.

**Roadmap placement.** Work out exactly where each item belongs in the current roadmap
order, from the sequence the provider returned in the preflight, so the review can place
it without re-deriving it and the `virtuoso` skill can see what it would run ahead of:

- **After:** the last item it must follow. That is each prerequisite, and any item ahead
  of it that changes the same edit sites.
- **Before:** the first item that must follow it. That is any item that depends on it,
  or whose specification cites a location this will move.
- **Group, lane, and finish line**, where the project uses them, and whether it counts
  toward a declared deadline (the `pace` block of `kpis --json`).
- **Against the head:** whether it has to run before the current head, and why. Running
  ahead of roadmap order is allowed only for a stated reason.

Write it as one line per item:
`Placement: after [Title] ([ID]), before [Title] ([ID]) — [group / lane]; [deadline or none]; [why]`.
When two orders are both defensible, ask a bounded question. The line is a decision for
the review to apply in its C.3 and C.4. This skill still writes nothing to the roadmap,
the register, or the sequence.

Fill next-pointer's reconciliation recipe with detected values: the remote, the default
branch, and the branch name from `policy.git.branchNameTemplate`. Include only steps
the project's git policy permits, and leave no placeholders. The recipe is text for the
executor. This skill never runs it, because creating the work branch is the first act of
execution. Then compose the pointer. It carries the origin line:

```
[Item title]  (HB-<n>)
Origin: held plan — [entry] (HB-<n>), not yet on the roadmap
Placement: after [Title] ([ID]), before [Title] ([ID]) — for the review to apply
Effort: [size]
Branch: [branch] from [default branch] @ [sha that carries the held plan, or "uncommitted — see git status"]
Specification: [holding bay path]/[entry].md#HB-<n>
Status: planned — held | Prerequisites: [descriptive names, met/pending]
Readiness: specification ✓ · prerequisites ✓ · repository ✓ · register ✓ · environment ✓
```

## Step 6 — The plan gate

Show the user the plan: a two-line summary per item, the five findings, the roadmap
placement, and the pointer. Ask them to **approve**, **revise**, or **stop**. A revision
that changes what was agreed goes back to the storyboard first. Approval covers the plan
and its hand-off. It does not start the work.

## Step 7 — Hold the plan

1. Write the `## Plan` section into the held entry: **Readiness** (the five findings),
   **Roadmap placement**, **Pointer**, **Repository reconciliation — run this FIRST**
   (for the `virtuoso` skill to run), then the **Specifications**, one
   `#### HB-<n> — Title` per item.
2. Check the entry, then record it (preview first, then `--apply`):

       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . holding --check <entry>
       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor write-plan holding --record <entry> --state planned --note "<HB ids; rubric passed>" --apply

3. Persist the file as `policy.git` permits, using the five-level table from
   next-pointer's Phase 3.5, with the exact path staged. If the work will run on a
   branch cut from the default branch, and the held plan is not yet on that base,
   repository readiness is **BLOCKED** until it is. State that, as next-pointer does.

## Step 8 — Hand off to Virtuoso

This is where the plan leaves this skill. Nothing in this step executes. The plan goes
to the **virtuoso** skill, the only skill that executes (`references/execution-paths.md`),
or it waits in the holding bay.

Offer the hand-off **only** when all five findings pass and nothing is externally
blocked. Otherwise, name the blocker by its descriptive name, and hold the plan.

> **[Title]** is planned and nothing blocks it. Where should it go next?
> - **(a) Hand off to Virtuoso here** *(recommended when [the reason: e.g. it is small,
>   the context is warm, and the branch base already carries the plan])*. This skill
>   ends, and the virtuoso skill starts from the held entry in this session.
> - **(b) Hand off to Virtuoso in another session.** You might use a command-line
>   session, a fresh session, or a cloud session. I'll print a kickoff prompt, and the
>   plan stays held until that session picks it up.
> - **(c) Hold for roadmap review.** The next `/roadmap-review` places it at the slot
>   this plan records, and `/next-pointer` dispatches it from there.
> - **(d) Withdraw it**, with a reason.

Recommend (b) over (a) when this session is heavy with context the executor does not
need, or when `policy.git.separationOfDuties` means the planner must not also implement.

An item set is handed off as one unit: every item, in prerequisite order, in one run. If
the user wants only part of it now, the rest waits for the review. Offering "run HB-3
now, hold HB-4" would split one entry across two paths.

### (a) Hand off here

Print the summary (below), which ends this skill. Then load the **virtuoso** skill and
give it the held entry: its pointer, its placement, its reconciliation recipe, and its
specifications, as the dispatch spec. From that moment the run belongs to the virtuoso
skill. It checks the plan against upstream, downstream, and in-flight work, records the
entry `in-flight`, runs the recipe, executes, returns the entry to `planned` if the run
stops, and hands a finished run to `/pointer-closeout`. This skill records nothing more.

### (b) Another session

Print one fenced block the next session can start from. That session has no memory of
this one:

```
Use the virtuoso skill to execute the held plan [entry] ([HB ids]) at
[holding bay path]/[entry].md. Its Plan section carries the pointer, the roadmap
placement, the repository-reconciliation recipe, and the specifications.
Before the first edit, run the skill's written-plan intake: the conflict check against
upstream, downstream, and in-flight work, then record the entry in-flight, then run the
recipe. Close out with /pointer-closeout.
If the conflict check finds that the code or the roadmap has moved since the plan was
recorded, stop and run /write-plan [entry] to re-verify it.
If a roadmap review has absorbed the entry in the meantime, it is a roadmap item now:
use /next-pointer instead.
```

The entry stays `planned`. The virtuoso skill records `in-flight` when that session
starts.

### (c) Hold for roadmap review

Nothing more to write. End with the entry's path and state, and tell the user that the
next `/roadmap-review` places it at the recorded slot.

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
| Placement | after [Title] ([ID]), before [Title] ([ID]) — for the review to apply |
| Held | [entry] — planned |
| Hand-off | virtuoso here / virtuoso in another session / hold for review / withdrawn |

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
| "It passed, so I'll start executing" | This skill never executes. The plan goes to the `virtuoso` skill (Step 8), and that skill records `in-flight` itself. |
| "I'll run the reconciliation recipe so the branch is ready" | The recipe is for the executor. Creating the work branch is the first act of execution, and it belongs to the `virtuoso` skill. |
| "It's one line, so I'll make the change while I write the spec" | Reading the edit sites is planning. Changing them is execution. Write it in the specification. |
| "Placement is the review's job, so I'll skip it" | Working out the slot is this skill's job. Applying it is the review's. The `virtuoso` skill reads it to see what the run would jump ahead of. |

## Integration

- `references/execution-paths.md` — the destination this plan must reach, shared with
  `/next-pointer` and `/epic`.
- `/storyboard` — where every plan starts, and where every alignment question returns.
- `virtuoso` — the only skill that executes. It takes the plan from Step 8's hand-off,
  checks it for conflicts, records `in-flight`, and runs it.
- `/pointer-closeout` — closes the run in held-plan mode.
- `/roadmap-review` — absorbs the held entry onto the master roadmap, or withdraws it.
