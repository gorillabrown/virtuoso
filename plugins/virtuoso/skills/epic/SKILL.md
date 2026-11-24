---
name: epic
description: >
  Produce the launch materials for a long-horizon autonomous run from the master roadmap: a
  multi-phase epic spanning hours or days of an agent working alone, across context loss and
  sessions, until a completion condition is verifiably met. Epics start only from the
  roadmap: one item a review placed with Path: epic ("/epic ITEM-ID", or routed here by
  next-dispatch), or a combination of dispatch-ready roadmap items run together, serialized
  where they share files ("/epic ID ID ID", "/epic --workstream checkout 11-15"). An outcome stated
  ad hoc ("keep working until it's done", "run this overnight") goes to /storyboard first.
  It goes on the belt as one epic row: /next-dispatch prints its kickoff, sessions run
  under the virtuoso skill, and /dispatch-closeout closes it.
  Trigger on: "epic", "/epic", "run the epic", "batch these items", "long-running goal",
  "autonomous run", "keep going until done". NOT for one dispatch-sized item (next-dispatch),
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

# Epic

Turn epic-scale work on the master roadmap into an **epic packet**: five files that let
any future agent session — with zero memory of this conversation — execute the goal
autonomously for hours or days, survive every context loss, and stop only when completion
is *proven* or a human decision is genuinely required.

The work has one of two shapes, both already on the roadmap:

- **One epic-scale item**, which a roadmap review placed with `Path: epic`.
- **A combination** of specified, placed roadmap items, none epic-scale alone, run
  together unattended. This skill alone judges whether they combine: their order, which
  share files and so serialize, which workstreams run side by side, and one Definition of
  Done across all. A combination needs no `Path` marker and no holding bay, because every
  piece is already placed.

**One of three paths, one destination.** This is the roadmap-epic path: like
`/next-dispatch`, it opens only on items placed on the master roadmap; only the ad hoc
path (`/storyboard` then `/write-plan`) may start from an idea. All three deliver the same
thing to execution under `references/execution-paths.md`: aligned, verifiable, aware of
the project, executed under the virtuoso skill, closed out by `/dispatch-closeout`.

**Core principle:** the goal is fixed and verifiable; the path belongs to the executor;
the files are the memory. You are producing the materials, not executing the goal.

**Announce at start:** "Using the epic skill to prepare a long-horizon run."

## When NOT to use — route instead

| Signal | Route |
|--------|-------|
| An outcome that is not on the master roadmap yet | `/virtuoso:storyboard`: it aligns the idea and holds it, and the next roadmap review places it as `Path: epic` |
| One dispatch-sized item on the roadmap | `/virtuoso:next-dispatch` |
| Fits in one sitting | Just do it (virtuoso skill if 3+ tool calls) |
| Recurring job on an interval ("check every 5 minutes") | loop / schedule tooling |
| An epic-scale item on the master roadmap (`Path: epic`) | **This skill**, Step 1a |
| Several roadmap items to run together, unattended, as one run | **This skill**, Step 1b |

Work that is not epic-scale: say so in one sentence; route a single item to
`/next-dispatch` (or `/roadmap-review` when it needs a path or specification), and a
one-sitting combination to `/next-dispatch`, item by item. This skill writes nothing to
the roadmap but its run's epic row (Step 5). Never scaffold a packet for an afternoon task.

## The packet

All five files live in one directory, `<yyyy-mm-dd>-<slug>/`, inside the project's
registered `epics` role. The packet's identifier names the run in the dispatch
identifier, the close-out, and its lessons: the item's own identifier for a `Path: epic`
item, `EPIC-` plus the slug in capitals for a combination (`EPIC-CHECKOUT-FOLLOW-UPS`),
which is not a register item.

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . resolve epics

Never fall back to a conventional path. A registered project with no `epics` role: stop
and show the entry to add to `Virtuoso/workspace-layout.json` (the user decides where
epics live):

```json
"epics": { "path": "<directory>", "provider": "directory", "authority": "reference",
           "mutability": "read-write", "owner": "epic", "allowedWriters": ["epic"] }
```

A project with no registry at all: ask the user for the directory and use exactly that.
Never seed a rival governance document.

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

**Exactly these five files.** No sixth file, no bespoke names, no "reference" split across
playbooks/runbooks/facts files: verified project facts live in state.md's Working set, and
how-to knowledge is the executor's to discover and journal. Every epic looks alike, so the
user, the resume prompt, and downstream tooling always know where to look.

## Workflow

### Step 1 — Pull the items from the master roadmap

An epic starts from items a roadmap review has placed, never from a stated outcome. Read
the register first; a register served from a snapshot must be fresh, so refresh a stale
one first (`references/registry-contract.md`, *Refreshing a connector-backed register's
snapshot*).

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor epic items --json

One item names Step 1a; several items, or a workstream, name Step 1b. One named item not
marked `Path: epic` that belongs with others ("run the retry worker overnight, and the two
cards it waits on") is Step 1b with those items.

#### Step 1a — One item marked `Path: epic`

`/epic <ITEM-ID>`, or the head item `/next-dispatch` routed here.

- The item is in the live register and not terminal, every prerequisite is terminal
  through the provider, and its roadmap entry declares `Path: epic`.
- Read its roadmap entry. When its origin names a held plan, read that entry's storyboard
  too (`holding --check <entry>`, then the file): its alignment record, frames, and
  decisions are the charter's first draft, and a question they already answer is not
  asked again.
- No such item: route to `/storyboard`. `Path` is dispatch or absent: the item is one
  dispatch, so route it to `/next-dispatch`, or run it in a combination (Step 1b) with the
  items it belongs with. A prerequisite is pending: name it and stop.
- A charter whose `item:` or `items:` already names this item means the packet exists: do
  not scaffold a second. Finish Step 5's items 3 and 4 if it is not yet on the default
  branch or the belt, then route to `/next-dispatch` for its kickoff.

#### Step 1b — A combination of roadmap items

`/epic <ITEM-ID> <ITEM-ID> …`, or a workstream and a range: `/epic --workstream <workstream> <from>-<to>`.
The mechanical half of the decision is one read-only command:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor epic combine --items <ITEM-ID> <ITEM-ID> ... --json
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor epic combine --workstream <workstream> --from <seq> --to <seq> --json

It checks each item is ready, unchartered, and has its prerequisites met inside the set
or already done, serializes items that share files, and returns the serial order, the
workstreams, and the reason for every ordering edge. Exit 0 means combinable; exit 1
means a blocking finding stands, and every error is a reason not to charter.

**Before acting on the result, read [references/combination.md](references/combination.md)**
— the full check table and its finding codes, where each error routes, the judgement the
command cannot make (readiness against lessons recorded since, hidden overlap, one
outcome), and the table to show the user before Step 2.

Epic scale = outcome-stated **and** multi-phase **and** multi-session-or-walk-away. State
the sizing verdict in one line (e.g. "Epic-scale: ~2 days, 4 phases, unattended
overnight", or "Epic-scale combination: 5 items, 1 workstream, ~14 points, overnight").

### Step 2 — Sharpen the charter (Definition of Done first)

Convert the item's outcome (its roadmap entry and, where it has one, the storyboard's
confirmed frames) into DoD rows: **condition | verify by | expected evidence**. For a
combination the outcome is what the items deliver together: its DoD carries every item's
*Done when* rows, each labelled with its item, plus a row only the whole proves: every
item's rows pass together on one integrated tree, in one session. Every row must be
checkable by a command or a concrete procedure; a row that cannot be verified is a wish,
not a condition, so tighten it or move it to non-goals.

Then write the charter's **Milestones** (rubric U11, in its charter form): a few named
stages from start to done, each with its outcome checkpoints and a checkable *Done when*,
often a DoD row. Checkpoints are outcomes a reader could see reached ("the importer reads
every fixture"), never tasks: they mark progress across sessions, not how to get there.
Check the table with
`"$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . progress --check-milestones <charter> --charter`
until it exits 0.

- **User present:** ask up to ~5 questions, highest-leverage first, one at a time: what
  done means, what must never happen, which calls the agent may make alone, where the
  access/credential edges are, who unblocks what.
- **Unattended already:** proceed on the stated text; record every gap as a charter
  Assumption with a guard (a cheap early verification, an escalation trigger, or both).

Autonomy grants and escalation triggers are the walk-away safety rails: write both, even
when short. Silence about a decision class means the executor will stall on it or take
it, and neither should happen by accident.

Then fold in the project's history: run
`"$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --open` and read every
live lesson against the outcome. Each that bears on it becomes a constraint, an
assumption's guard, or an escalation trigger, cited by identifier in the charter's
**Lessons applied** section; otherwise the section says no live lesson applies, with the
count read. A lesson paid for once must not be paid for again across an unattended run.

### Step 3 — Walk-away preflight (before the user leaves)

Verify **now**, while a human can still answer in five seconds, everything the run would
otherwise dead-end on unattended:

- paths in the goal exist and are absolute
- the canonical build/test/check commands actually run (capture baseline output)
- credentials are live (`gh auth status`, registry tokens, API keys)
- remotes/services in the DoD are reachable
- the runtime can act unattended: the permission mode / allowlist covers the run's tool
  needs, so no approval prompt stalls the run at hour two
- the repository, detected rather than assumed, as next-dispatch's *Repository
  reconciliation* detects it: the remote (or none), the default branch, the worktrees, the
  dirty paths, and `policy.git`. Settle network operations now: under
  `networkOperations: ask`, the user grants or denies fetch and push for the whole run,
  recorded as an autonomy grant, because an unattended session cannot answer an approval
  prompt. With no answer, the run treats network operations as denied.

Record results in state.md's Working set (verified facts) and launch.md's preflight
table, which reports the five readiness findings every path reports: specification (every
DoD row verifiable), prerequisites, repository, external register, and execution
environment. Anything unverifiable now becomes a **launch-blocking question** if the user
is still present, or an explicit charter Assumption + escalation trigger if not —
deliberately, never by omission. **Never defer a five-second question into the unattended
run.**

### Step 4 — Draft the phase map

3–7 phases in plan.md, each: intent, verifiable exit gate, rough size. Phase 1 is
discovery whenever any charter assumption is unverified: confirm reality before building
on it. For a combination, phases follow `combine`'s serial order and workstreams: a phase
takes one item, or several consecutive items of one workstream, and its exit gate is
those items' *Done when* rows. Record in plan.md why each item sits where it does (the
prerequisites and shared files the order honours), so the executor keeps the order when
it replans. Plan at phase altitude: no step lists, no pre-generated task backlogs, no
code. Steps belong to the run, where a capable executor plans them better with the repo
in front of it, and stale prescriptions poison later sessions. The charter's milestone
checkpoints are not such a list: they say what will be true along the way, never how.

### Step 5 — Scaffold and hand off

1. **Before filling the templates, read [references/run-rules.md](references/run-rules.md)**
   — the run rules they embed, which must survive intact. Copy the five templates into
   the epic directory; fill every bracket; delete unused optional sections. Seed
   journal.md with the S0 scaffold entry.
2. **Fill the run's git work** from `policy.git` and the repository state Step 3
   detected, the way `/next-dispatch` fills its reconciliation recipe: the remote (or
   none, which drops every network step), the default branch, the run's branch from
   `policy.git.branchNameTemplate` with the packet's identifier as `{item-id}`, the base
   commit it starts from, and only the steps the policy permits. Leave no placeholders.
   The git work stays inside the five files:
   - **launch.md** — the recipe, inside the kickoff prompt: the first session reconciles
     and creates the branch; every later session checks the branch, that the tree matches
     the last journal entry, and whether the base moved, halting on divergence instead of
     rebasing; each checkpoint stages exact paths, committing or pushing only as far as
     the policy allows. Its Completion only lines commit the record after the code merge
     and merge it into the default branch as a docs-only `--no-ff` merge, kept only where
     the run merges its own code and the policy commits.
   - **charter.md** — the branch and commit rules, under Constraints.
   - **state.md** — the run's branch, base, and remote, in the Working set.
3. **Land the packet on the default branch**, as one docs-only commit of the five files
   (exact paths), where `policy.git` commits; otherwise hand that commit to the repository
   operator. The run branch is cut from a base that carries its packet, and
   `/next-dispatch` reads it there: a packet only on a run branch, or in another clone,
   is invisible to it.
4. **Put the run on the belt as one row:**
   `"$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor epic epic-row --packet <packet>`
   previews it; `--apply` writes it. A combination gets one **epic row** (the packet's
   identifier, the charter's title, its earliest member's sequence slot, the
   prerequisites its members wait on outside the set, the charter as its specification)
   and every member nested under it, so the belt offers the run once, never item by
   item. A `Path: epic` item's own row already stands for the run. An external register
   gets one plan per connector call: execute each, `mutation-confirm` each, then refresh
   the snapshot. A refusal names its own fix (a parent column to nest in, or `epic` in the
   register's `allowedWriters`).
5. Print the walk-away readiness verdict: preflight table status + open assumptions.
6. Hand off to `/next-dispatch`. It gates the packet and prints the kickoff — launch.md's
   prompt, which carries the git work, and its goal line for the CLI's `/goal` — for the
   first session and every resume alike. This skill prints neither, and executes nothing.

## Scaffolding budget

Producing the packet is **minutes of document writing, not a mini-project**. Do not build
conversion pipelines, provision environments, write acceptance harnesses, or validate
toolchains against synthetic fixtures at scaffold time; that work belongs inside the run,
after discovery. The one exception: preflight *runs existing commands* to verify facts. A
DoD row that needs a check script that does not exist adds creating it to phase 1's gate.

## Execution discipline (rides inside the packet)

<!-- rule:claim-no-broader-than-evidence (evidence-scope) -->
**A claim may never be broader than the evidence actually checked, and the scope checked
must be stated.** This governs every Definition-of-Done claim an epic makes. "The greps
are clean" is a different claim from "the greps are clean on the surface I ran them
against" — and when a row says *both surfaces*, meeting it on one is not meeting it.

Three consequences, each observed:

- **A row met vacuously is not met.** If deleting a surface makes its check pass, record
  it as *"unreachable because the surface no longer exists"*, never as a clean result.
- **When an amendment makes any DoD row unmeetable as written, the epic stops and
  escalates.** It does not quietly continue on the remaining rows, nor loosen the row to
  fit what happened.
- **Scope narrowing is legitimate exactly when it is the owner's explicit recorded
  decision**, with the honest state documented. The same narrowing taken by the executor
  to fit a budget is scope creep in reverse.

The templates also embed the run rules (resume protocol, handoff-ready always, never idle,
fresh evidence, re-anchor at gates, context hygiene), listed in
[references/run-rules.md](references/run-rules.md), which Step 5 reads before filling them.

## Execution — the destination every path shares

Every session of the run executes under the **virtuoso** skill, with the packet as its
dispatch spec: the charter is the contract, plan.md the route, state.md the working set,
and the dispatch identifier `[PACKET-ID]-S<n>`. That brings an epic to the same place as
a roadmap dispatch and an ad hoc plan (`references/execution-paths.md`). The packet still
embeds its own run rules, so a session on a host without this plugin keeps them.

The run ends through `/dispatch-closeout [PACKET-ID]` once `done.md` exists on the default
branch, as launch.md's completion protocol says. That crossing retires the item on the
master roadmap, or every item of a combination and its epic row, and records what the
epic taught.

- `mid-dispatch-decision` — process a BLOCKER(USER) when the user returns to one.
- `adversarial-review` — red-team the charter before committing days to it.

## Anti-patterns (observed in baseline runs)

- Chartering an outcome not on the master roadmap (storyboard it; the review places it)
- Marking dispatch-sized items `Path: epic` to run them together (combine them, Step 1b)
- Unserialized shared files, or an order chosen by hand over `combine`'s without a
  recorded reason
- Pre-baked task backlogs or starter code for a project nobody has inspected yet
- A 9-or-22-file bespoke kit instead of the five-file contract
- Deferring "where is the repo?" / "is gh authenticated?" into the unattended run
- A packet left off the default branch, or a combination left on the belt item by item:
  `/next-dispatch` then offers the members as dispatches of their own
- Executor-only materials — no kickoff prompt, no monitoring guide, no completion protocol
- "Done" on stale or hearsay evidence; DoD rows nobody can execute
- state.md growing history (journal's job) or how-to lore (executor's job)
