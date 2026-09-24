---
name: plan-now
description: |
  MANUAL INVOCATION ONLY. Ad hoc planning intake for work the user wants to
  plan now, outside the roadmap-review cycle. Brainstorms the work with the
  user (intent, placement, touchpoints, externalities, upstream and
  downstream impact), drafts a skeleton for approval, authors dispatch-ready
  specifications against the shared readiness rubric, brings them into the
  roadmap and the live work register, runs the dispatch gate on them, and
  then asks whether to execute now with the virtuoso skill or leave the work
  queued for another session, host, or date. Triggered by "/plan-now",
  "plan this now", "I want to do X now", or "write a plan for X and slot it
  in". Does NOT re-sequence other items or recalibrate the roadmap; that is
  /roadmap-review.
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

# Plan Now

The roadmap is the spine: `/roadmap-review` decides what exists and in what order, and
`/next-pointer` finalizes the head of that order. This skill is the side door for work
that arrives **between** reviews — "I want to do X now." It takes the work from an idea
to a dispatch-ready item that the roadmap and the register both know about. The user then
chooses to execute it here, or to leave it for another session.

Work planned here is **held to the same standards** as work planned in a review. It
uses the same rubric, the same specification format, the same lessons check, and the
same dispatch gate. The side door is faster, but it does not lower the bar. It also
leaves a trace. Every item carries its origin, so the next review can see what came in
this way and judge whether it belonged.

**Announce at start:** "Using plan-now to take this from idea to a dispatch-ready item."

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
- `none` — no registry. Brainstorming and a specification in chat are still possible,
  but nothing can be ingested. Say so, and offer `/virtuoso-init` first.
- `failed` — report the error verbatim and stop.

Read the `roadmap-integrity:` line. On `fail`, STOP: a corrupt roadmap is not written
to. On `warn`, confirm with the user before any write that comes later.

### Resolve the register and negotiate capabilities

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor plan-now provider
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor plan-now items --all --json

| To do this | You need |
|---|---|
| read the pipeline for the impact map | `list-active`, `read-status`, `read-prerequisites` |
| bring a new item into existence | `create-item`, and `policy.workRegister.creators` naming `plan-now` (or unset) |
| link a specification stored outside the roadmap | `store-spec-link` |
| seat the item in the sequence | `read-sequence`, and a writable sequence field |
| mark the item in flight when executing now | `write-status` |

Then check write permission. This skill writes to the `roadmap` role (the
specification), to the `workRegister` role (the new row and its own status), and to the
`issues` role (a blocker). Each write needs that role's `allowedWriters` to name
`plan-now`.

**Say what is missing before you start, not halfway through.** If a capability or a
permission is missing, tell the user which one, and give the choices up front:

- (a) *Recommended when only the permission is missing:* show the exact registry change,
  which adds `"plan-now"` to the role's `allowedWriters` in
  `Virtuoso/workspace-layout.json`. Apply it only on approval, then re-run
  `--mode check` to confirm the registry still validates.
- (b) Plan in full here, but hand the approved specification to `/roadmap-review` to
  ingest. This skill writes nothing to the roadmap or the register.
- (c) Stop.

A read-only register means (b) or (c). Never write a row into a register file by hand
to work around a missing capability.

## When to use

- The user names a specific piece of work and wants it planned now, not at the next
  review.
- Something urgent arrived (a bug, a request, an opportunity) and must go into the
  pipeline properly rather than be done off the books.
- The user wants to do the work immediately but still wants it specified, recorded, and
  closed out like everything else.

## Route instead

| Signal | Route |
|---|---|
| "What's next?" and the head item is already specified | `/next-pointer` |
| The whole roadmap needs re-sequencing, or many items are stale | `/roadmap-review` |
| The outcome spans many sessions and the user wants to walk away | `/epic` |
| A feasibility question whose answer is information, not shipped work | Answer it directly. No item. |
| A one-line fix the project's policy lets you make without an item | Do it directly |
| A running dispatch has hit a decision | `/mid-dispatch-decision` |

When a route applies, say so in one sentence and hand off. Do not open a planning
ceremony for an afternoon's typo.

## Operating principles

1. **Hard gates.** You may investigate freely, because reading is always allowed. But
   you do not write a specification until the user approves the skeleton. You do not
   ingest anything until the user approves the specification. You do not execute until
   the user chooses to execute. Each approval covers only the stage you actually showed
   the user. It does not cover the next stage, which does not exist yet.
2. **Investigate before you ask.** Read the code, the roadmap, the register, the
   lessons, and the standing rules first. Ask the user only about things investigation
   cannot settle: intent, priority, trade-offs, and permission.
3. **One question per message, and keep it bounded.** Follow
   `references/actors-and-interaction.md`: 2–4 concrete options, one recommended, and an
   escape hatch.
4. **Keep what was said separate from what you assumed.** Every write-back of your
   understanding shows the two apart, so the user can correct an assumption before it
   turns into a requirement.
5. **Sizing is a one-way ratchet.** Announce the size out loud before your first
   question. If you uncover hidden complexity, stop, say so, and move to the heavier path.
   Nothing moves to a lighter path mid-ceremony, and a label is never used to skip work.
6. **Write only your own rows.** This skill creates its own items and edits only their
   rows and specifications. It never re-sequences, rewrites, or re-scopes another item.
   When the new work affects another item, the impact map records it and routes it to
   `/roadmap-review`.
7. **One rubric, one format.** Specifications use roadmap-review's D.5.2 format and must
   pass `references/readiness-rubric.md`. No skill writes its own version of either.
8. **Record the origin.** Every item this skill creates says it entered through
   `plan-now`, on which date, and why it could not wait for a review.
9. **Descriptive names first.** Every reference to an item leads with its title, and the
   identifier comes second.

---

## Phase 1 — INTAKE AND SIZE

### 1.1 Restate the request

Restate the work in one sentence, in the user's own terms. If the request does not say
why the work matters or who it is for, ask that first, as a single question. Everything
else depends on the answer.

### 1.2 Size it, out loud

Classify the work and **say the classification** so the user can override it:

| Size | Signal | Path |
|---|---|---|
| **Single item** | One outcome, one change unit, fits one dispatch | The full path below, one item |
| **Item set** | Several separable outcomes, or one outcome needing more than one dispatch | The full path below, decomposed into items with explicit prerequisites between them |
| **Epic-scale** | Outcome-stated, multi-phase, spans sessions, walk-away | Route to `/epic` |
| **Not an item** | A feasibility answer, or a change policy lets you make without an item | Route per the table above |

> "This looks like a single item: one change to the export path, one dispatch. I'll
> plan it as one item unless you see more to it."

If the request covers several independent subsystems, say so **before** you refine any
detail. Help the user split it into items first. There is no point polishing the details
of work that has to be split anyway.

## Phase 2 — BRAINSTORM (investigate, then ask)

The goal is to understand the work completely, **including where it sits in the
project**, and not only what it does.

### 2.1 Investigate first

Before your first substantive question, read:

- the code, configuration, and documents the work will plausibly touch
- the live register, through the provider: every active item, and whether any of them
  already covers, overlaps, blocks, or depends on this work
- the roadmap's active section and its non-blocking follow-up queue, because the work
  may already exist there as a stub
- the live lessons: `"$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --open`
- the standing rules at `policy.standingRules.source`
- the declared deadlines and pace: the `pace` block of
  `"$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . kpis --json`
- in-flight branches and worktrees, using read-only git inspection
  (`GIT_OPTIONAL_LOCKS=0 git --no-optional-locks …`)

**If the work already exists as an item, stop and say so.** An existing stub is
specified where it is, through `/roadmap-review` or by finalizing it with
`/next-pointer`. It is never duplicated under a new identifier. Offer (a) finalize the
existing item now with `/next-pointer` (recommended when it is the head), (b) take the
existing item through this skill's Phases 3–6 without creating a new row, or (c) the
user confirms it is genuinely different work, and you record why.

### 2.2 Ask through six lenses

Ask one question per message, and only where investigation left a real gap. Put the
highest-leverage lens first. You do not have to ask about every lens; skip a lens that
investigation already answered, and say that you skipped it.

| Lens | What you need to know |
|---|---|
| **Outcome** | What does done look like, observably? What must never happen? What is explicitly out of scope? |
| **Placement** | Where does this sit in the roadmap: which group, lane, or finish line? Does it count toward a declared deadline's scope? Is it more urgent than the current head? |
| **Touchpoints** | Which modules, interfaces, data, documents, and tests does it change directly? |
| **Externalities** | Services, credentials, data owners, users, other teams, or other repositories it reaches outside the codebase |
| **Upstream** | What must be true first? Which items, decisions, or dependencies does it wait on, directly or indirectly? |
| **Downstream** | Which items, specifications, consumers, generated reports, or documents change because this lands? Which dispatch-ready specifications cite a location this will move? |

### 2.3 Write back your understanding

Before you draft anything, show a short note the user can check:

```
## Understanding — [working title]

**Outcome:** [one sentence]
**Why now:** [the reason it cannot wait for a review]

**You said:**
- …
**I am assuming (correct me):**
- …

**Impact map**
| Direction | Item / artifact | Relationship | Effect |
|---|---|---|---|
| Upstream   | [Title] ([ID]) | prerequisite / decision / dependency | must be terminal first |
| Downstream | [Title] ([ID]) | its spec cites [location] | spec goes stale → flag for review |
| Sideways   | [Title] ([ID]) | same edit sites, in flight | conflict risk → serialize |
| External   | [service / owner] | credential / data / approval | [what is needed] |
| Deadline   | [deadline id] | in / out of scope | [pace consequence, or not computable] |
```

Take in the corrections before you go on. Every row of the impact map comes from
something you read, and each row cites its source.

## Phase 3 — SKELETON (approval gate)

### 3.1 Propose approaches

When more than one reasonable approach exists, present 2–3 of them. Give the trade-offs
of each, lead with the one you recommend, and give your reason. Cut any feature the
outcome does not need. When only one approach is sensible, say so in one line and do not
invent alternatives.

### 3.2 Draft the skeleton

Draft the skeleton at item altitude, with no implementation detail yet:

```
## Skeleton — [working title]
Size: single item | item set (N items)
Approach: [chosen approach, one line]

### [Item title]  (proposed id: [next id in the project's scheme])
- What: …                        - Out of scope: …
- Why: …                         - Done when (draft): 1. … 2. …
- Edit sites (expected): …       - Effort: low / medium / high / max
- Prerequisites: [descriptive names]
- Interfaces: consumes … / produces …   (item sets only: what each item hands the next)

### Placement
- Recommended: execute now | next up (ahead of [head title]) | after [Title] | let /roadmap-review seat it
- Reason: …

### Impact actions
- [Downstream item] — spec cites [location]; flagged for /roadmap-review, not edited here
```

The new identifier follows the pattern the register's existing identifiers use. The
provider's creation step refuses any identifier already used, including retired ones.

### 3.3 Gate

Ask the user to approve the skeleton, revise it, or stop. **Nothing is written until
they approve.** If they ask for a revision, revise and present the skeleton again.

## Phase 4 — AUTHOR THE SPECIFICATIONS

For each item in the approved skeleton, in prerequisite order:

### 4.1 Draft in the D.5.2 format

Use roadmap-review's specification format (its section D.5.2): structural fields, then
implementation detail, then **Lessons applied**. Source the facts from the code you read
and from close-outs, decision records, and standing rules. Add these two blocks, which
item sets and ad hoc work in particular need:

- **Origin:** `plan-now YYYY-MM-DD — [why it could not wait for a review]`. Record it in
  the specification and in the register row's `notes`.
- **Review focus:** at most five inputs or conditions that the outcome implies but that
  no test in the specification exercises yet, ordered by how likely each is to hurt
  someone. For each one, either add a *Done when* row and its test, or state explicitly
  that it is out of scope. An empty list means you checked and found nothing. It does
  not mean you skipped the check.

Plan at item altitude. The implementation task list is built at execution time, by the
virtuoso skill's Phase 2, with the repository in front of it. Do not pre-write code
here. A pre-written step goes stale, and the rubric does not require one.

### 4.2 Apply the shared rubric

Walk `references/readiness-rubric.md` at its current version, plus the project's
declared extensions, exactly as roadmap-review's D.3.2 does:

- **PASS** → record it.
- **CLOSABLE GAP** → close it by investigation, using roadmap-review's gap table.
- **STRUCTURAL GAP** → ask a bounded question. Never invent the decision.

Run U9's mechanical half on each specification:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --check <spec> --item <ITEM-ID>

Make at most two enrichment passes. If a specification still fails after two, it is not
saved as dispatch-ready. Save it as a stub, with the failing checks named, and tell the
user.

### 4.3 Self-review before showing it

Read the specification again as a stranger would, and fix what you find in place:

1. **Coverage** — every outcome in the approved skeleton maps to a *Done when* row.
2. **Placeholders** — no "TBD", "handle edge cases", "similar to above", or "add
   validation" without the actual content. (U7 catches deferred decisions; this check
   also catches vague ones.)
3. **Consistency** — names, paths, and interfaces agree across sections, and across
   sibling items in an item set.
4. **Ambiguity** — no requirement a reader could reasonably take two ways. Pick one
   reading and state it.

### 4.4 Gate

Show the specifications, with each one's rubric result reported as the five separate
findings. Ask the user to approve, revise, or stop. **Nothing is ingested until they
approve.**

## Phase 5 — INGEST INTO THE ROADMAP AND THE REGISTER

### 5.1 Create the register rows

For each approved item, bring it into existence through `create-item`. Never hand-write
a row, and never call a connector's raw create:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor plan-now create-item --item <ITEM-ID> --fields-json '<JSON>'

Supply the canonical fields, and the register's column names and status words come from
`policy.workRegister.fieldMappings` and `statusMappings`. Include `title`, `status`
(`queued`), the specification state (`full-spec` if the specification passed the rubric,
`stub` if it did not), `prerequisites`, `effort`, `group` or `lane` if the project uses
them, `branch`, `description`, and `notes` carrying the origin.

For an **external** register, use the creation handshake that roadmap-review's D.5.3
describes: `mutation-plan --operation create-item`, then execute the returned instruction
with the host's connector, then `mutation-confirm`, then refresh the snapshot and check
that `recovery` is empty.

### 5.2 Seat the item without re-sequencing anyone else

Place the item where the user chose in Phase 3, **writing only the new item's own
sequence value**:

| Placement | What is written |
|---|---|
| Execute now | The item's sequence is set ahead of the current head (the head's value minus one). Status stays `queued` until Phase 6 marks it in flight. |
| Next up | Same as above: the item's sequence is set ahead of the current head. |
| After [Title] | A free sequence value between that item and the one after it, if one exists. |
| Let /roadmap-review seat it | No sequence is written. The item sorts last, and the recommendation goes in its notes. |

If the chosen placement needs any other item's sequence value to change (for example,
there is no free value in the gap), **do not renumber**. Record the intended placement in
the item's notes and in the roadmap entry, write no sequence, and say plainly that the
next `/roadmap-review` will seat it. The user can still dispatch it before that review:
Phase 6 targets it by identifier.

### 5.3 Save the specifications

Save each specification where `policy.roadmap.specStorage` says. That may be inline in the
roadmap's active section at the item's position, a file under
`policy.roadmap.specDirectory`, or the external system. For the last two, link it with
`store-spec-link`. Specifications that are not stored inline still get a one-line entry
in the roadmap's active section, so the roadmap and the register agree.

### 5.4 Record the downstream flags

For every downstream item in the impact map whose specification this work makes stale,
do **not** edit that specification. Add one line to the roadmap's non-blocking follow-up
queue:

```
- [Downstream title] ([ID]) — spec cites [location] which [New item title] ([NEW-ID]) changes; re-audit at next /roadmap-review. (plan-now YYYY-MM-DD)
```

If the new item **must** land before a dispatch-ready item can proceed, that is a
re-sequencing decision. Tell the user, and route it to `/roadmap-review`. Do not make the
decision yourself.

### 5.5 The ingestion change

What happens to the edited roadmap and specification files next is set by `policy.git`,
using the same table as next-pointer's Phase 3.5 (report, leave, stage, commit, or push),
including `separationOfDuties` if the project declares it. Check the result against
primary evidence (`git status -sb`, `git diff --stat`). If the work will run on a branch
cut from the default branch and the specification is not on that base yet, repository
readiness is BLOCKED until it is. State that clearly. Do not paper over it.

## Phase 6 — DISPATCH GATE AND THE EXECUTION CHOICE

### 6.1 Run the dispatch gate on this item

Run `/next-pointer` **targeted at the new item**: `/next-pointer <ITEM-ID>`. That runs its
readiness audit, enrichment, pre-flight resolution, and pointer against this item, not
against the head of the belt. You get the five readiness findings, the filled
repository-reconciliation recipe, and the pointer, exactly as a head-of-belt dispatch
would. For an item set, target the first item whose prerequisites are all met.

### 6.2 Can it run now?

It can run now **only** if all five readiness findings pass, the serialization check finds
no in-flight branch or worktree on the same edit sites, and every prerequisite is
terminal. If any of these fails, do not offer "execute now". Name the blocker by its
descriptive name, and offer to leave the work queued, to escalate per
`policy.issues.targets`, or to route to `/roadmap-review`.

### 6.3 Ask how to proceed

When the item can run now, ask one bounded question:

> **[Item title]** ([ID]) is dispatch-ready and nothing blocks it. How do you want to run it?
> - (a) **Execute now, here, with Virtuoso** *(recommended when [reason: e.g. small,
>   context is warm, and the branch base already carries the spec])*
> - (b) **Fresh session or another host** — I'll print the pointer and a kickoff prompt
>   you can paste into a new session, a command-line session, or a cloud session
> - (c) **Later** — it stays queued at [placement]; `/next-pointer` (or
>   `/next-pointer [ID]`) picks it up
> - (d) **It grew** — hand it to `/epic` for a long-horizon run

Recommend (b) over (a) when this session's context is heavy with brainstorming the
executor does not need, or when `policy.git.separationOfDuties` means the planner must not
also implement.

### 6.4 (a) Execute now

1. Mark the item `in-flight` through the provider (`write-status`, passing the
   `revision` you read). If the provider cannot write status, say so; the close-out will
   reconcile it.
2. Run the pointer's repository-reconciliation recipe. Halt on any STOP it contains.
3. Load the **virtuoso** skill and hand it the pointer and the specification as the
   dispatch spec. Virtuoso governs execution from here on: task plan, owners, execution,
   blockers, and close-out block.
4. Bookend with `/pointer-closeout` when the work is done, exactly as for any other
   dispatch.

### 6.5 (b) Hand-off to another session

Print the pointer and a self-contained kickoff prompt in one fenced block. The next
session starts with none of this conversation's memory:

```
Use the virtuoso skill to execute [Item title] ([ITEM-ID]).
Specification: [resolved location] @ [sha or "uncommitted — see git status"]
First run /next-pointer [ITEM-ID] to re-confirm readiness against current state,
then run its repository-reconciliation recipe, then execute.
Close out with /pointer-closeout.
```

Re-confirming is necessary because code moves between planning and execution, and the
dispatch gate is how drift gets caught.

### 6.6 (c) Later

End with the item's placement, its identifier, and the command that picks it up. For a
dated start in this same session, `delayed-start` can hold the run. For a date beyond this
session, record the date in the item's notes. It is a note, not a deadline: deadlines live
only in `policy.roadmap.deadlines`, which `/roadmap-review` owns.

---

## Output — the final summary

```
# Plan Now — [Item title]

**[One-to-two-sentence plain-language summary.]** *(item [ITEM-ID], origin plan-now YYYY-MM-DD)*

| | |
|---|---|
| Items created | [Title] ([ID]) — full-spec / stub |
| Placement | [what was written, or "awaiting /roadmap-review — reason"] |
| Readiness | specification ✓ · prerequisites ✓ · repository ✓ · register ✓ · environment ✓ |
| Downstream flags | [N] added to the follow-up queue |
| Deadline effect | [deadline id]: [verdict before → after] *(or: not computable — [inputs]; or: none declared)* |
| Decision | execute now / hand-off / later / epic |

*Source: [register] via [provider], snapshot [timestamp].*
```

## Red flags

| Thought | Reality |
|---|---|
| "It's small, so I'll skip the skeleton" | The skeleton is two minutes, and it is the one place the user can catch a wrong assumption cheaply. |
| "They approved the idea, so I'll write the spec and start" | Each approval covers the stage the user saw. The spec gate and the execution choice are still ahead. |
| "I'll bump the other items down to make room" | Renumbering others is re-sequencing, and re-sequencing is `/roadmap-review`'s job. Record the placement and flag it. |
| "The downstream spec is obviously stale, so I'll fix it" | Another item's specification is not yours to edit. Flag it in the follow-up queue. |
| "The register is read-only, so I'll just add a line to the CSV" | A hand-written row bypasses creation authority and idempotency. Hand the spec to `/roadmap-review`. |
| "It turned out bigger, but I'm nearly done planning" | Hidden complexity moves you to the heavier path. Stop, say so, and re-size. |
| "Ad hoc work doesn't need lessons applied" | U9 applies to every specification. The side door has the same bar. |

## Integration

- `/roadmap-review` — owns sequencing and recalibration. It reads `plan-now` origins in
  its scope-discipline assessment and seats unsequenced items.
- `/next-pointer <ITEM-ID>` — the dispatch gate this skill runs in Phase 6.
- `virtuoso` — the execution framework for "execute now".
- `/pointer-closeout` — closes the dispatch, whichever session ran it.
- `/epic` — where work goes when it outgrows a dispatch.
- `adversarial-review` — optional red-team of a skeleton before committing to it.
