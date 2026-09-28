---
name: epic
description: >
  Produce the launch materials for a long-horizon autonomous run from the master roadmap: a
  multi-phase epic spanning hours or days of Claude working alone, across context loss and
  sessions, until a completion condition is verifiably met. Epics start only from the
  roadmap: one item a review placed with Path: epic ("/epic ITEM-ID", or routed here by
  next-pointer), or a combination of dispatch-ready roadmap items run together, serialized
  where they share files ("/epic ID ID ID", "/epic --lane checkout 11-15"). An outcome stated
  ad hoc ("keep working until it's done", "run this overnight") goes to /storyboard first.
  Every session runs under the virtuoso skill, and the run closes through /pointer-closeout.
  Trigger on: "epic", "/epic", "run the epic", "batch these items", "long-running goal",
  "autonomous run", "keep going until done". NOT for one dispatch-sized item (next-pointer),
  single-session tasks (virtuoso skill), or interval jobs (loop/schedule).
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

# Epic

Turn epic-scale work on the master roadmap into an **epic packet**: five files that let
any future Claude session — with zero memory of this conversation — execute the goal
autonomously for hours or days, survive every context loss, and stop only when completion
is *proven* or a human decision is genuinely required.

The work is one of two shapes, and both are already on the roadmap:

- **One epic-scale item**, which a roadmap review placed with `Path: epic`.
- **A combination** of roadmap items a review already specified and placed, none of them
  epic-scale alone, run together unattended. This skill decides whether they combine:
  what order they run in, which of them share files and so run one after another, which
  lanes can run side by side, and the one Definition of Done across all of them. That
  judgement is the valuable part, and no other ceremony makes it. A combination needs no
  `Path` marker and no holding bay, because every piece is already placed.

**One of three paths, one destination.** This is the roadmap-epic path. Like
`/next-pointer`, it opens only on items a roadmap review has placed on the master
roadmap. The ad hoc path, `/storyboard` then `/write-plan`, is the only one that may
start from an idea. All three deliver the same thing to execution, under the contract in
`references/execution-paths.md`: aligned, verifiable, aware of the project, executed
under the virtuoso skill, and closed out by `/pointer-closeout`.

**Core principle:** the goal is fixed and verifiable; the path belongs to the executor;
the files are the memory. You are producing the materials, not executing the goal.

**Announce at start:** "Using the epic skill to prepare a long-horizon run."

## When NOT to use — route instead

| Signal | Route |
|--------|-------|
| An outcome that is not on the master roadmap yet | `/virtuoso:storyboard`: it aligns the idea and holds it, and the next roadmap review places it as `Path: epic` |
| One dispatch-sized item on the roadmap | `/virtuoso:next-pointer` |
| Fits in one sitting | Just do it (virtuoso skill if 3+ tool calls) |
| Recurring job on an interval ("check every 5 minutes") | loop / schedule tooling |
| An epic-scale item on the master roadmap (`Path: epic`) | **This skill**, Step 1a |
| Several roadmap items to run together, unattended, as one run | **This skill**, Step 1b |

When the work turns out not to be epic-scale, say so in one sentence. Route a single item
to `/next-pointer`, or to `/roadmap-review` when it needs a path or a specification, and
route a combination that is really one sitting to `/next-pointer`, one item at a time.
This skill does not edit the roadmap. Do not scaffold a packet for an afternoon task.

## The packet

All five files live in one directory, `<yyyy-mm-dd>-<slug>/`, inside the project's
registered `epics` role. The packet's identifier names the run in the sprint identifier,
the close-out, and the lessons it records: the item's own identifier for a `Path: epic`
item, and `EPIC-` plus the slug in capitals for a combination
(`EPIC-CHECKOUT-FOLLOW-UPS`). A combination's identifier is not a register item.

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . resolve epics

Never fall back to a conventional path. If the project is registered but declares no
`epics` role, stop and show the entry to add to `Virtuoso/workspace-layout.json` —
the user decides where epics live:

```json
"epics": { "path": "<directory>", "provider": "directory", "authority": "reference",
           "mutability": "read-write", "owner": "epic", "allowedWriters": ["epic"] }
```

If the project keeps no registry at all, ask the user for the directory and use exactly
that. Never seed a rival governance document.

| File | Role | Mutability during the run |
|------|------|---------------------------|
| `charter.md` | The contract: outcome, Definition of Done, constraints, non-goals, autonomy grants, escalation triggers, assumptions | **Frozen** — only the user amends |
| `plan.md` | The route: 3–7 phases, each intent + verifiable exit gate | Executor may replan phases (logged); gates only tighten |
| `state.md` | Current truth: resume protocol, where-we-are block, next actions, working set, blockers, decisions, evidence | Rewritten freely; always current |
| `journal.md` | History: append-only session log | Append only |
| `launch.md` | Human side: preflight, kickoff/resume prompt, completion protocol, monitoring guide | Static after scaffold |

Templates (copy, then fill every `[BRACKET]`):
[assets/charter.template.md](assets/charter.template.md) ·
[assets/plan.template.md](assets/plan.template.md) ·
[assets/state.template.md](assets/state.template.md) ·
[assets/journal.template.md](assets/journal.template.md) ·
[assets/launch.template.md](assets/launch.template.md)

**Exactly these five files.** No sixth file, no bespoke names, no split of "reference"
across playbooks/runbooks/facts files — verified project facts live in state.md's Working
set; how-to knowledge is the executor's to discover and journal. One epic looks like every
other epic, so the user, the resume prompt, and downstream tooling always know where to look.

## Workflow

### Step 1 — Pull the items from the master roadmap

An epic starts from items a roadmap review has placed, never from a stated outcome. Read
the register first. If it is served from a snapshot, the snapshot must be fresh: refresh a
stale one before going further (`references/registry-contract.md`, *Refreshing a
connector-backed register's snapshot*).

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor epic items --json

One item names Step 1a. Several items, or a lane, name Step 1b. When the user names one
item that is not marked `Path: epic` but belongs with others ("run the retry worker
overnight, and the two cards it waits on"), it is Step 1b with those items.

#### Step 1a — One item marked `Path: epic`

`/epic <ITEM-ID>`, or the head item `/next-pointer` routed here.

- The item is in the live register and not terminal. Every prerequisite is terminal,
  resolved through the provider. Its roadmap entry declares `Path: epic`.
- Read its roadmap entry. When its origin names a held plan, read that entry's
  storyboard too: `holding --check <entry>`, then the file itself. Its alignment record,
  frames, and decisions are the charter's first draft, and a question they already
  answer is not asked again.
- No such item: route the user to `/storyboard`. `Path` is dispatch, or absent: the item
  is one dispatch, so route it to `/next-pointer`, or run it in a combination (Step 1b)
  with the items it belongs with. A prerequisite is pending: name it and stop.
- A charter whose `item:` or `items:` already names this item means the run exists. Point
  to its launch file, and do not scaffold a second packet.

#### Step 1b — A combination of roadmap items

`/epic <ITEM-ID> <ITEM-ID> …`, or a lane and a range: `/epic --lane <lane> <from>-<to>`.
The mechanical half of the decision is one read-only command:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor epic combine --items <ITEM-ID> <ITEM-ID> ... --json
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor epic combine --lane <lane> --from <seq> --to <seq> --json

It reads the register and each item's specification, and reports:

| Check | Combinable when | Finding when not |
|---|---|---|
| Each item is on the roadmap and ready to run | in the register, not terminal, blocked, or in flight; its specification written (`full-spec`) | `combine-item-unknown`, `-terminal`, `-blocked`, `-in-flight`, `-stub` |
| Each item runs only here | no active charter's `item:` or `items:` names it, and its entry does not declare `Path: epic` | `combine-item-chartered`, `combine-item-epic` |
| Each prerequisite is met | done already, or another item in the set | `combine-prerequisite-outside`, `combine-cycle` |
| Shared files are serialized | two items whose *Edit sites* or *Staging plan* name the same file run one after the other; items with nothing between them may run in separate lanes | an item whose files cannot be read runs serially with everything (`combine-spec-unlocated`, `combine-files-unlisted`, warnings) |
| It is more than one item | two or more items | `combine-single` |
| The register is current | a fresh snapshot | `combine-snapshot-stale` |

The command also returns the **serial order** (prerequisites first, then shared files,
ties broken by register sequence), the **lanes**, every ordering edge with its reason
("shared files: src/checkout/gateway.py"), and the effort in points. Exit 0 means
combinable, and exit 1 means a blocking finding stands. Every error is a reason not to
charter. Say which one, and route it: a stub or a missing prerequisite to
`/roadmap-review`, an item in flight to its own close-out, and a stale snapshot to a
refresh.

Then make the judgement the command cannot:

- **Readiness.** Each item's specification already passed the rubric when a review made
  it dispatch-ready. Re-run its mechanical half now, because lessons may have been
  recorded since: `lessons --check <spec> --item <ITEM-ID>` for each. Walk the rest of
  `references/readiness-rubric.md` against each specification as `/next-pointer` would.
  A structural gap stops the combination, just as it stops a dispatch.
- **Hidden overlap.** The files come from the specifications. Read each item's edit
  sites against the code. Two items that change the same interface, schema, or fixture
  through different files still serialize. Record every ordering you add, and its
  reason, in the plan.
- **One outcome.** A combination is chartered because its items together make one
  outcome worth an unattended run. Items that merely share a lane do not make one: say
  so and chart only the set that does.

Present the combination to the user before Step 2, as one table in serial order: item by
title then identifier, lane, what it waits on, and the files it shares. Then state the
sizing verdict. A combination the user trims is re-checked with `combine`.

Epic scale = outcome-stated **and** multi-phase **and** multi-session-or-walk-away. State
the sizing verdict in one line (e.g. "Epic-scale: ~2 days, 4 phases, unattended
overnight", or "Epic-scale combination: 5 items, 1 lane, ~14 points, overnight").

### Step 2 — Sharpen the charter (Definition of Done first)

Convert the item's outcome, from its roadmap entry and, where it has one, from the
storyboard's confirmed frames, into DoD rows: **condition | verify by | expected
evidence**. For a combination, the outcome is what the items deliver together. Its DoD
carries every item's *Done when* rows, each labelled with its item, and adds a row for
what only the whole proves: every item's rows pass together on one integrated tree, in
one session.
Every row must be checkable by a command or a concrete procedure — a row that cannot be
verified is a wish, not a condition; tighten it or move it to non-goals.

- **User present:** ask up to ~5 questions, highest-leverage first — what does done mean,
  what must never happen, which calls may Claude make alone, where are the
  access/credential edges, who unblocks what. One question at a time.
- **Unattended already:** proceed on the stated text; record every gap as a charter
  Assumption with a guard (a cheap early verification, an escalation trigger, or both).

Autonomy grants and escalation triggers are the walk-away safety rails — write both, even
when short. Silence about a decision class means the executor will either stall on it or
take it; neither should happen by accident.

Then fold in the project's own history. Run
`"$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --open` and read every
live lesson against the outcome: each that bears on it becomes a constraint, an
assumption's guard, or an escalation trigger, and is cited by identifier in the charter's
**Lessons applied** section — or the section says no live lesson applies, with the count
read. A lesson the project paid for once must not be paid for again across an unattended
run, and the charter is the cheapest place to apply it.

### Step 3 — Walk-away preflight (before the user leaves)

Verify **now**, while a human can still answer in five seconds, everything the run would
otherwise dead-end on unattended:

- paths in the goal exist and are absolute
- the canonical build/test/check commands actually run (capture baseline output)
- credentials are live (`gh auth status`, registry tokens, API keys)
- remotes/services in the DoD are reachable
- the runtime can act unattended — permission mode / allowlist covers the run's tool
  needs, so no approval prompt stalls the run at hour two
- the repository, detected rather than assumed, as next-pointer's *Repository
  reconciliation* detects it: the remote (or that there is none), the default branch,
  the worktrees, the dirty paths, and `policy.git`. Settle network operations now. Under
  `networkOperations: ask`, the user grants or denies fetch and push for the whole run,
  recorded as an autonomy grant, because an unattended session cannot answer an approval
  prompt. With no answer, the run treats network operations as denied.

Record results in state.md's Working set (verified facts) and launch.md's preflight table.
The table reports the same five readiness findings every path reports: specification (every
DoD row verifiable), prerequisites, repository, external register, and execution
environment.
Anything unverifiable right now becomes a **launch-blocking question** if the user is still
present, or an explicit charter Assumption + escalation trigger if not — deliberately,
never by omission. **Never defer a five-second question into the unattended run.**

### Step 4 — Draft the phase map

3–7 phases in plan.md, each: intent, verifiable exit gate, rough size. Phase 1 is
discovery whenever any charter assumption is unverified — confirm reality before building
on it. For a combination, the phases follow `combine`'s serial order and lanes: a phase
takes one item, or several consecutive items of one lane, and its exit gate is those
items' *Done when* rows. Record in plan.md why each item sits where it does, the
prerequisites and shared files the order honours, so the executor keeps to the order
when it replans. Plan at phase altitude: no step lists, no pre-generated task backlogs,
no code. Steps belong to the run; a capable executor plans them better with the repo in front of it
than you can now, and stale prescriptions poison later sessions.

### Step 5 — Scaffold and hand off

1. Copy the five templates into the epic directory; fill every bracket; delete unused
   optional sections. Seed journal.md with the S0 scaffold entry.
2. **Fill the run's git work** from `policy.git` and the repository state Step 3
   detected, the way `/next-pointer` fills its reconciliation recipe: the remote (or
   none, which drops every network step), the default branch, the run's branch from
   `policy.git.branchNameTemplate` with the packet's identifier as `{item-id}`, the base
   commit it starts from, and only the steps the policy permits. Leave no placeholders.
   The git work stays inside the five files:
   - **launch.md** — the recipe, inside the kickoff prompt. The first session reconciles
     and creates the branch. Every later session checks that it is on that branch, that
     the tree matches the last journal entry, and whether the base has moved, and it
     halts on divergence instead of rebasing. Each checkpoint stages exact paths, and
     commits or pushes only as far as the policy allows.
   - **charter.md** — the branch and commit rules, under Constraints.
   - **state.md** — the run's branch, base, and remote, in the Working set.
3. Print the walk-away readiness verdict: preflight table status + open assumptions.
4. Print the kickoff/resume prompt from launch.md in a fenced code block. It carries the
   git work and the epic's instructions together, so one paste carries both. It is the
   same prompt for the first session and every later one.
5. Straight after it, print the **goal line** from launch.md in its own fenced block,
   ready for the CLI's `/goal` command. It is one line: what the epic must achieve,
   from the charter's outcome, and how completion is proven, meaning every
   Definition-of-Done row in the charter verified fresh and `done.md` written. It also
   names the one other clean stop, every front blocked on a recorded BLOCKER(USER).
   Without that, `/goal` would keep a blocked run going.
6. If the user is present, offer to hand off now: the first session starts under the
   virtuoso skill, the only skill that executes, from the kickoff prompt. This skill
   executes nothing itself. Otherwise, end with the packet path, the code-boxed prompt,
   and the goal line.

## Scaffolding budget

Producing the packet is **minutes of document writing, not a mini-project**. Do not build
conversion pipelines, provision environments, write acceptance harnesses, or validate
toolchains against synthetic fixtures at scaffold time — that work belongs inside the run,
after discovery, where reality can inform it. The one exception: preflight *runs existing
commands* to verify facts. If a DoD row needs a check script that doesn't exist, add
creating it to phase 1's gate instead of writing it now.

## Execution discipline (rides inside the packet)

<!-- rule:claim-no-broader-than-evidence (evidence-scope) -->
**A claim may never be broader than the evidence actually checked, and the scope checked
must be stated.** This governs every Definition-of-Done claim an epic makes. "The greps
are clean" is a different claim from "the greps are clean on the surface I ran them
against" — and when a row says *both surfaces*, meeting it on one is not meeting it.

Three consequences that have each been observed:

- **A row met vacuously is not met.** If deleting a surface makes its check pass, record
  it as *"unreachable because the surface no longer exists"*, never as a clean result.
- **When an amendment makes any DoD row unmeetable as written, the epic stops and
  escalates.** It does not quietly continue on the remaining rows, and it does not loosen
  the row to fit what happened.
- **Scope narrowing is legitimate exactly when it is the owner's explicit recorded
  decision**, with the honest state documented. The same narrowing taken by the executor
  to fit a budget is scope creep in reverse.

The templates embed the run rules so the executor gets them by reading the files it must
read anyway — the packet works even for an executor that has never seen this plugin:

- **Resume protocol** at the top of state.md: charter → plan → state → last journal entry;
  distrust-then-verify; files are memory, the repo is reality.
- **Handoff-ready always:** sessions die without warning; update state.md and journal.md
  before ending any work burst.
- **Never idle:** blocked on one front → advance another; blocked on all →
  BLOCKER(USER) with the exact question, clean journal exit.
- **Fresh evidence:** completion claims re-run every DoD verification in the claiming
  session; `done.md` is written once, by that session, and is the loop's stop signal.
- **Re-anchor at gates:** every phase gate re-reads the charter before the next phase
  opens — goal drift compounds silently across compaction and session boundaries.
- **Context hygiene:** raw tool output stays out of durable files and out of the
  long-lived session — record distilled conclusions and evidence pointers; where the
  runtime offers subagents, push noisy exploration into them and keep only their results.

## Execution — the destination every path shares

Every session of the run executes under the **virtuoso** skill, with the packet as its
dispatch spec. The charter is the contract, plan.md is the route, state.md is the working
set, and the sprint identifier is `[PACKET-ID]-S<n>`. That is what brings an epic to the
same place as a roadmap dispatch and an ad hoc plan (`references/execution-paths.md`).
The packet still embeds its own run rules, so a session on a host without this plugin
keeps them anyway.

The run ends through `/pointer-closeout [PACKET-ID]` once `done.md` exists, as launch.md's
completion protocol says. That crossing retires the item on the master roadmap, or every
item of a combination, and records what the epic taught.

- `mid-dispatch-decision` — process a BLOCKER(USER) when the user returns to one.
- `adversarial-review` — red-team the charter before committing days to it.

## Anti-patterns (observed in baseline runs)

- Chartering an outcome that is not on the master roadmap: storyboard it, and let the
  review place it
- Marking dispatch-sized items `Path: epic` so they can run together: combine them
  instead (Step 1b), and let each keep its own path
- A combination whose shared files were not serialized, or whose order was chosen by
  hand when `combine` reported another: record the reason for every ordering
- Pre-baked task backlogs or starter code for a project nobody has inspected yet
- A 9-or-22-file bespoke kit instead of the five-file contract
- Deferring "where is the repo?" / "is gh authenticated?" into the unattended run
- Executor-only materials — no kickoff prompt, no monitoring guide, no completion protocol
- "Done" on stale or hearsay evidence; DoD rows nobody can execute
- state.md growing history (journal's job) or how-to lore (executor's job)
