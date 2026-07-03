---
name: epic
description: >
  Produce the launch materials for a long-horizon autonomous run — a multi-phase epic spanning
  hours or days of Claude working alone, across context loss and multiple sessions, until a
  completion condition is verifiably met. Use when the user states an outcome and wants to
  walk away: "here's the goal, keep working until it's done", "run this overnight", "multi-day
  epic", "set this up so Claude finishes it without me", "prepare an epic", "work until the
  tests pass / coverage hits the target". Also use when a goal is too big for one sitting and
  the user does not want to spec the steps. Trigger on: "epic", "long-running goal",
  "autonomous run", "walk away", "keep going until done", "don't lose the thread", "completion
  condition", "give it the goal not the steps". NOT for fully-specified sprint dispatches
  (sprint machinery), single-session tasks (virtuoso skill), or interval jobs (loop/schedule).
---

# Epic

Turn a stated outcome into an **epic packet**: five files that let any future Claude
session — with zero memory of this conversation — execute the goal autonomously for hours
or days, survive every context loss, and stop only when completion is *proven* or a
human decision is genuinely required.

**Core principle:** the goal is fixed and verifiable; the path belongs to the executor;
the files are the memory. You are producing the materials, not executing the goal.

**Announce at start:** "Using the epic skill to prepare a long-horizon run."

## When NOT to use — route instead

| Signal | Route |
|--------|-------|
| Fits in one sitting | Just do it (virtuoso skill if 3+ tool calls) |
| A dispatch-ready spec already exists for a low-judgment implementer | Sprint machinery — `/virtuoso:next-pointer` |
| Recurring job on an interval ("check every 5 minutes") | loop / schedule tooling |
| Outcome-stated, multi-phase, multi-session or walk-away | **This skill** |

When sized below epic scale, say so in one sentence and route — do not scaffold a packet
for an afternoon task.

## The packet

All five files live in one directory. Resolution order for that directory:
(1) an `epics` path registered in `Virtuoso/workspace-layout.json`, if present;
(2) `<Project Documentation>/2 operational/Epics/` where that governance tree exists;
(3) `epics/` at the project root. Directory name: `<yyyy-mm-dd>-<slug>/`.
Never seed a rival governance document; if the project keeps a
`Virtuoso.Governance.Readme.md` registry, suggest (once) registering the epics directory —
the user decides.

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

### Step 1 — Size it

Epic scale = outcome-stated **and** multi-phase **and** multi-session-or-walk-away.
Anything less: route per the table above. State the sizing verdict in one line
(e.g. "Epic-scale: ~2 days, 4 phases, unattended overnight").

### Step 2 — Sharpen the charter (Definition of Done first)

Convert the stated outcome into DoD rows: **condition | verify by | expected evidence**.
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

### Step 3 — Walk-away preflight (before the user leaves)

Verify **now**, while a human can still answer in five seconds, everything the run would
otherwise dead-end on unattended:

- paths in the goal exist and are absolute
- the canonical build/test/check commands actually run (capture baseline output)
- credentials are live (`gh auth status`, registry tokens, API keys)
- remotes/services in the DoD are reachable
- the runtime can act unattended — permission mode / allowlist covers the run's tool
  needs, so no approval prompt stalls the run at hour two

Record results in state.md's Working set (verified facts) and launch.md's preflight table.
Anything unverifiable right now becomes a **launch-blocking question** if the user is still
present, or an explicit charter Assumption + escalation trigger if not — deliberately,
never by omission. **Never defer a five-second question into the unattended run.**

### Step 4 — Draft the phase map

3–7 phases in plan.md, each: intent, verifiable exit gate, rough size. Phase 1 is
discovery whenever any charter assumption is unverified — confirm reality before building
on it. Plan at phase altitude: no step lists, no pre-generated task backlogs, no code.
Steps belong to the run; a capable executor plans them better with the repo in front of it
than you can now, and stale prescriptions poison later sessions.

### Step 5 — Scaffold and hand off

1. Copy the five templates into the epic directory; fill every bracket; delete unused
   optional sections. Seed journal.md with the S0 scaffold entry.
2. Print the walk-away readiness verdict: preflight table status + open assumptions.
3. Print the kickoff/resume prompt from launch.md in a fenced code block — it is the
   same prompt for the first session and every later one.
4. If the user is present, offer to begin executing now; otherwise end with the packet
   path and the code-boxed prompt.

## Scaffolding budget

Producing the packet is **minutes of document writing, not a mini-project**. Do not build
conversion pipelines, provision environments, write acceptance harnesses, or validate
toolchains against synthetic fixtures at scaffold time — that work belongs inside the run,
after discovery, where reality can inform it. The one exception: preflight *runs existing
commands* to verify facts. If a DoD row needs a check script that doesn't exist, add
creating it to phase 1's gate instead of writing it now.

## Execution discipline (rides inside the packet)

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

## Integration (optional, never required)

- `virtuoso` — per-burst execution discipline when the executor runs inside this plugin.
- `mid-dispatch-decision` — process a BLOCKER(USER) when the user returns to one.
- `adversarial-review` — red-team the charter before committing days to it.

## Anti-patterns (observed in baseline runs)

- Pre-baked task backlogs or starter code for a project nobody has inspected yet
- A 9-or-22-file bespoke kit instead of the five-file contract
- Deferring "where is the repo?" / "is gh authenticated?" into the unattended run
- Executor-only materials — no kickoff prompt, no monitoring guide, no completion protocol
- "Done" on stale or hearsay evidence; DoD rows nobody can execute
- state.md growing history (journal's job) or how-to lore (executor's job)
