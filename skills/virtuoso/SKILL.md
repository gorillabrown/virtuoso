---
name: virtuoso
description: >
  Structural execution discipline for multi-step tasks in one parent conversation. Use this
  skill whenever running a sprint, executing a checklist, or performing any work that involves
  3+ sequential tool calls. This skill enforces task planning, narration, progress tracking, and
  optional child-agent swarms while preserving each sprint as a clearly named dispatch record.
  Trigger on: "execute this plan", "run this sprint", "implement these changes", any dispatch
  prompt with multiple steps, or any task where completion quality depends on maintaining focus
  across many tool calls. When in doubt, use this skill — the overhead is minimal and the
  discipline prevents regressions.
---

# Virtuoso

You are about to execute a multi-step task. This skill keeps you disciplined throughout
the entire run — not just the first few tool calls. The problem it solves: behavioral
rules read at session start get deprioritized under context pressure after 10+ tool calls.
This skill stays in active context because you reference it at every step boundary.

**Announce at start:** "Using the Virtuoso skill to maintain execution discipline."

## Sprint Record Naming

When Virtuoso starts a sprint, the visible record must be named for the work, not for
the trigger token. If Codex CLI/Desktop creates a new chat/thread/record for the run,
the desired title is:

`[SPRINT-ID] — [short dispatch name]`

Examples:
- `KOKORO-DEEPEN-2 — Chunk Timing Narration`
- `POSTV2-REVIEW-1 — Review Closeout`
- `SPRINT-QUEUE-MIGRATE — Workbook Queue Transition`

If an explicit title-setting mechanism is available, set the sprint record title to
that value before implementation begins. If no title-setting mechanism is available,
make the first substantive visible line after the short Virtuoso announcement:

`[SPRINT-ID] — [short dispatch name]`

Do not let the record remain titled `$virtuoso`, `/virtuoso`, "Virtuoso", or any
other skill-trigger-only name when the sprint or dispatch name is knowable. If the
sprint ID is unknown at intake, use a temporary descriptive title and update the
first plan heading once the ID is discovered.

## Architecture: Parent Chat + Optional Swarm

Virtuoso runs inside the active parent conversation or the CLI-created parent sprint
record. It is acceptable for CLI to preserve a separate record per sprint run, but
that record must be named for the sprint, not for the skill invocation. Do not create,
request, or suggest an additional top-level chat just to re-run Virtuoso inside a
sprint record that already exists.

Agent swarms are allowed when the user or dispatch spec authorizes parallel
implementation. Child agents are workers attached to the current sprint plan, not
new `$virtuoso` parent chats. The parent thread reads the dispatch spec, builds the
task plan, launches child agents only for concrete independent tasks, integrates
their results, runs verification, and keeps the human oriented.

**No orphan-chat rule:** Virtuoso may use `Agent()` / `spawn_agent` for bounded
worker tasks, but never as a way to start a new parent chat, restart the sprint in
another conversation, or invoke `$virtuoso` recursively. If a legacy workflow says
"open a new Virtuoso chat," ignore that instruction and continue in the current
parent conversation.

**The boundary that matters is parent vs worker.** The parent owns the plan,
scope, narration, integration, and close-out. Workers own bounded task execution.
All worker output returns to the one visible sprint plan in the parent chat.

## Effort Levels

Every dispatch may declare a **default effort level** that controls how deeply the
parent thread and child workers should reason. Effort is set when authoring the
spec; Virtuoso respects it and records mismatches during close-out. The full
decision framework, cost implications, and task-type reference live in the
`effort-levels` skill. This section covers only what the parent thread needs
to know during execution.

### The Four Levels

| Level | Thinking Budget | Behavior |
|-------|----------------|----------|
| **low** | Minimal | Pattern-match from trained knowledge. Answer from memory, don't work through it. |
| **medium** | Moderate | Meaningful reasoning within capacity. Handles majority of standard tasks. |
| **high** | Substantial | Traces complex logic, considers multiple approaches, backtracks when needed. |
| **max** | Full available | Reasons as extensively as context allows. Slowest, most expensive, highest quality. |

### How Virtuoso Uses Effort Levels

1. **Read the sprint's declared effort** from the dispatch header (e.g., `Effort: Medium`).
2. **Check for task-level overrides** — individual tasks may annotate `{high}` or `{max}`
   to override the sprint default.
3. **Record effort on the task plan** and pass it through to any child worker prompt.
4. **Effort ↔ model tier defaults** — when effort is not explicitly annotated on a task,
   it inherits from the model tier: haiku→low, sonnet→medium, opus→high.
5. **Only annotate effort when it differs from the default.** A `[sonnet]` task is implicitly
   `{medium}`. Write `[sonnet] {high}` only when overriding.

### Close-out: Effort Mismatches

In Phase 6 (Close Out), flag any task where the declared effort didn't match actual
complexity. "Task #3 was spec'd as {low} but required 3 retries — recommend {medium}
for similar tasks." This feedback helps Cowork calibrate future dispatches.

---

## Phase 1: Load and Understand

Before touching any file or running any command:

1. **Read the full task specification.** If the task references external docs, read those too.
2. **Read the behavioral reference** — the bundled [`references/zeus.md`](references/zeus.md)
   (Virtuoso's orchestration protocol: routing decision tree, agent hierarchy, escalation
   rules), or the project's own lead-agent definition if it overrides — to load the routing
   decision tree, escalation rules, and coordination protocol.
3. **Identify every discrete deliverable.** A deliverable is something you can point to when done
   (a file changed, a test passing, a document updated, a commit made).
4. **Flag anything unclear.** If a step is ambiguous, a file path might be wrong, or a dependency
   might not exist — stop and ask NOW. Guessing wastes 10x more time than asking.

If you have concerns about the plan, raise them before proceeding. Plans are not sacred —
they're starting points. But once you start executing, follow the plan unless you hit a
genuine blocker.

---

## Phase 2: Build the Task Plan

Print a numbered task plan with checkbox markers. Every deliverable from Phase 1 gets a line.
Use these markers consistently throughout:

```
□ = not started
■ = in progress
✓ = completed
✗ = blocked (with reason)
```

### Task format

Every task line follows this format: `□ N. owner-label: Task description [model] {effort}`

- **Model tier** in square brackets: `[haiku]`, `[sonnet]`, or `[opus]`.
- **Effort level** in curly braces: `{low}`, `{medium}`, `{high}`, or `{max}`.
  Effort is optional when it matches the model-tier default (haiku→low, sonnet→medium,
  opus→high). Only annotate effort when overriding the default.
- **Task #1 is always `codex-parent: Load spec, build plan, assign owners [opus]`.** Non-negotiable.
  This represents Phases 1–3 combined. Task #1 is marked ✓ only after CLI has:
  1. Read and understood the full dispatch spec (Phase 1)
  2. Built the numbered task plan (Phase 2)
  3. Assigned parent-owned tasks and child-worker candidates (Phase 3)
  4. Recorded the repository starting point when the spec requires one
  5. Printed the final assignment table
  Task #1 is the parent thread's setup work. Everything after Task #1 is either
  executed by the parent or delegated to child workers under this same sprint plan.
- Every subsequent task starts with `unassigned:` as a placeholder — Phase 3 replaces
  these with owner labels.
- The sprint's declared effort level is the default. Task-level annotations override it.

### Model tiers

Annotate each task with the minimum viable model — the cheapest tier that can handle
the task without sacrificing accuracy.

**haiku** — deterministic steps with a known correct answer. Running a test suite,
formatting a file, updating a version number, committing and pushing. Speed and
reliability, not reasoning depth.

**sonnet** — single-domain work requiring judgment within a bounded scope. Writing a
function, tuning a constant, fixing a bug in one module, updating documentation to
match code changes. Domain knowledge but not cross-cutting awareness.

**opus** — work that touches multiple modules, requires understanding interactions
between subsystems, or involves architectural decisions. Root-cause analysis across
files, calibration interpretation, resolving conflicting requirements.

### Example (Phase 2 output — tasks enumerated, agents not yet assigned)

```
## Task Plan — Effort: Medium | Override: tasks #6, #8 → High
□ 1. codex-parent: Load spec, build plan, assign owners                [opus]
□ 2. unassigned: Modify calc_defense_effectiveness() — WEIGHT 3.0→2.0  [sonnet]
□ 3. unassigned: Update constants.toml default                          [haiku]
□ 4. unassigned: Run fast test suite — all shards pass                  [haiku]
□ 5. unassigned: Run calibration N=1,200×3 seeds                       [haiku]
□ 6. unassigned: Interpret cal results + decide if tuning needed        [opus] {max}
□ 7. unassigned: Generate profiler snapshot with pathway metrics        [haiku]
□ 8. unassigned: Analyze profiler — does freed space flow to both?      [opus] {max}
□ 9. unassigned: Update CLAUDE.md with constants and cal results        [sonnet]
□ 10. unassigned: Commit, merge to main, push                          [haiku]
```

Note: Tasks #6 and #8 override to `{max}` because interpreting calibration results
and analyzing profiler output across subsystems are genuinely hard analytical problems
where getting it wrong has real downstream consequences. All other tasks use their
model-tier defaults (haiku→low, sonnet→medium, opus→high).

**Governance task rewrite (worktree-resident sprints):** Task #9 targets CLAUDE.md,
which is a protected governance document. In a worktree-resident sprint, CLI rewrites
this task at plan time:
```
□ 9. unassigned: Write staging fold-ins for CLAUDE.md (constants + cal results) [sonnet]
```
Codex writes fold-in entries to the staging file instead of editing CLAUDE.md
directly. See §Worktree Governance Staging for the full pattern.

Also create a TodoWrite to track the same tasks programmatically. The printed plan is for
human readability; TodoWrite is for persistent tracking.

### Rules

- Task #1 is always parent-thread setup work (Phases 1–3). No exceptions.
- One task per logical deliverable. Don't bundle "edit file AND run tests" into one line.
- **No collapsing tasks into batches or waves.** Every task from Phase 1 stays its own
  numbered line item in the plan. If you need to batch dispatches for practical reasons
  (e.g., tool-count ceilings), that is a dispatch optimization inside Phase 4 — but the
  task plan still tracks each deliverable individually. Never merge tasks like
  "implement tasks 1-6 + write tests" into a single line. Each task is executed or
  delegated, tracked, and reported on independently.
- If the spec says to do it, it gets a line. Don't silently absorb steps.
- If you discover a new required step during execution, ADD it to the plan and reprint.

---

## Phase 3: Assign Parent And Worker Owners

With the task plan built, the parent thread decides which tasks it should do locally
and which tasks are good child-worker candidates. This gives the human a clear
execution map without creating a fresh parent chat for the sprint.

### The Owner Hierarchy

```
codex-parent — owns plan, scope, integration, verification, close-out [opus]
  ├── hermes-worker  — mechanical execution, known-correct changes   [haiku]
  ├── hercules-worker — single-domain implementation, bounded judgment [sonnet]
  ├── aristotle-worker — cross-system implementation, architectural  [opus]
  └── specialist workers — bounded job descriptions
        ├── Hippocrates — test execution                          [haiku]
        ├── MarcusAurelius — spec compliance, chronicles, docs    [sonnet]
        ├── Plato — code quality review                           [sonnet]
        └── [Project specialists as available]
```

Workers are child agents under the current sprint run when delegation is authorized.
They are not standalone `$virtuoso` chats and they do not own the parent plan.

### Step 1: Scan for available workers

Search the project directory for role/agent definitions if they help preserve local
language. Look in:
- `.claude/agents/` — project agent definitions
- The plugin's bundled `agents/` (e.g., `Socrates`, the calibration specialist)
- The dispatch spec or task description for named roles
- The bundled behavioral reference [`references/zeus.md`](references/zeus.md) for the routing decision tree

Build a compact inventory. Do not spawn yet; spawning only happens during Phase 4
after the plan identifies a concrete worker task.

**Worker Name Resolution:** For every worker/agent file discovered, read its YAML
frontmatter `name:` field and use that label in the plan when helpful. The `name:`
field is authoritative for worker naming.

### Step 2: Analyze each worker's intent and model

For every discovered worker role, read its definition and extract:
- **Intent**: what is this worker designed to do?
- **Model**: what model does it run on (haiku / sonnet / opus)?
- **Type**: doer (general implementation) or specialist (bounded job)?
- **Constraints**: any specializations, limitations, or scoping rules?

Print the roster:

```
## Worker Roster
Doers:
- hermes [haiku] — mechanical execution, prescribed changes
- hercules [sonnet] — single-domain implementation with judgment
- aristotle [opus] — cross-system implementation, architectural decisions, root-cause analysis

Specialists:
- hippocrates [haiku] — runs test suites, reports pass/fail
- marcusaurelius [sonnet] — spec compliance, documentation, governance updates
- plato [sonnet] — code quality review
```

If doer roles are not defined in the project, use the generic labels above. The
concept (cheap/mid/expensive work tiers) applies regardless of whether formal role
files are present.

### Step 3: Pair owners to tasks — the routing decision tree

For every task in the plan, walk this tree top-to-bottom. Take the FIRST match.

**0. Parent-owned?**
Is this task on the critical path, tightly coupled to current integration work,
mostly orchestration, or unsafe to hand off because the parent needs the result
immediately?
→ **codex-parent**

**1. Specialist match?**
Does a specialist label match this task exactly?
- Running tests → **hippocrates**
- Verifying spec compliance → **marcusaurelius**
- Reviewing code quality → **plato**
- Updating governing docs → **marcusaurelius**
- Diagnosing unknown bug → **aristotle**
- Project specialist exists and matches → **that specialist**

If yes and the task is independent enough to hand off → assign to the specialist
worker. Stop.

**2. Exact diff known?**
Can you write the precise file + old text + new text right now, with zero judgment?
(Config value changes, renames, version bumps, git stage/commit/push, file copies)
→ **hermes-worker**

**3. Single module / single domain?**
Does the work only need to understand ONE area of the codebase?
(Write a function, fix a known bug, implement a scoped feature, apply a fix spec,
write tests for one module)
→ **hercules-worker**

**4. Cross-system / architectural?**
Does the work need to hold multiple subsystems in mind? Could a change in file A
break file B? (Multi-module refactors, interface changes, pipeline integration,
data flow redesigns)
→ **aristotle-worker**

**5. When in doubt:** Default to **codex-parent** for urgent/blocking work, or
**hercules-worker** for independent implementation work with bounded scope.

The parent may execute any task directly when that keeps the critical path moving.
Use workers for bounded sidecar tasks that materially advance the sprint.

### Step 4: Print the assignment table

Reprint the task plan with owner labels replacing `unassigned:`. This is the
final plan that governs execution.

```
## Task Plan (single parent chat — child workers allowed)
✓ 1. codex-parent: Load spec, build plan, assign owners                [opus]
□ 2. hercules-worker: Modify calc_defense_effectiveness() — WEIGHT 3.0→2.0 [sonnet]
□ 3. hermes-worker: Update constants.toml default                      [haiku]
□ 4. hippocrates-worker: Run fast test suite — all shards pass         [haiku]
□ 5. hippocrates-worker: Run calibration N=1,200×3 seeds               [haiku]
□ 6. codex-parent: Interpret cal results + decide if tuning needed     [opus]
□ 7. hippocrates-worker: Generate profiler snapshot with pathway metrics [haiku]
□ 8. aristotle-worker: Analyze profiler — does freed space flow to both? [opus]
□ 9. marcusaurelius-worker: Update CLAUDE.md with constants and cal results [sonnet]
□ 10. codex-parent: Commit, merge to main, push                        [haiku]
```

The header states that the parent chat remains singular even when child workers are
used. Note: Task #1 is already ✓ because printing this table IS the completion of
Task #1.

---

## Phase 4: Execute With Parent-Owned Swarm Control

The parent thread walks through the task plan in order. For every task after Task
#1, the parent either executes locally or launches a child worker, then integrates
the result back into the one parent plan.

### Execution model

For each task, the parent:
1. Takes the next task from the plan
2. **Set effort level** — if this task has an effort override (e.g., `{max}`),
   note the override before starting and pass it through to any worker prompt.
3. Decides whether to execute locally or launch a child worker.
4. If launching a worker, gives it a bounded task, explicit file/module ownership,
   success criteria, and instructions not to revert others' edits.
5. Verifies the result meets the task spec.
6. If the result includes information needed by downstream tasks, records the relevant
   summary for later steps.
7. Marks the task ✓ or ✗.
8. Reprints the plan.
9. Moves to the next task.

**Effort level management:** Effort controls how deeply the parent and child workers
reason. Set the sprint's default effort at the start of Phase 4 (read from the dispatch
header's `Effort:` field), then note before/after any task with a `{curly brace}`
override. The four levels are: `low`, `medium`, `high`, `max`.
```
/effort-levels medium          ← set sprint default at start of Phase 4
/effort-levels max             ← before a {max} override task
  [execute locally or launch bounded child worker]
/effort-levels medium          ← revert after override task completes
```

**Worker prompts should be concise, not exhaustive.** Specify WHAT to do, WHERE, the
owned files/modules, and the success criteria. Avoid copying large source blocks into
the prompt. Example:

```
Good: "Modify calc_defense_effectiveness() in engine/fro.py — change WEIGHT from
3.0 to 2.0. Run tests after to confirm no regression."

Bad: [200 lines of inlined source code, data structure definitions, and API docs
that the worker can read from the filesystem when needed]
```

**Governance-task dispatch gate (worktree-resident sprints only).** Before dispatching
any task that updates a document listed in CLAUDE.md §Main Governance Documents:

1. CLI rewrites the task description to target the staging file instead of the
   governance document. Example: "Update CLAUDE.md with constants and cal results"
   becomes "Write fold-in entries to the staging file for CLAUDE.md updates (constants,
   cal results, phase status)."
2. The parent includes the staging file path in the task note or worker prompt:
   `"Write fold-ins to 2 operational/Memo.<sprint-id>.GovernanceStaging.<date>.md"`
3. The parent records the constraint:
   `"Do NOT edit CLAUDE.md directly — this sprint runs in a worktree. All governance
   updates go to the staging file as fold-in entries."`

If the task plan includes a governance-update task and CLI is in a worktree, the task
MUST include these three elements.

**Downstream dependency handling:** When Task #8 depends on Task #4's output
(e.g., test results inform which files to fix), the parent extracts the relevant
information from Task #4's result and carries it into Task #8. The parent is the
information bridge between sequential tasks.

Independent tasks should be parallelized when the user or dispatch spec authorizes
agent swarms and the write scopes do not conflict. Never bundle multiple tasks into
a single mega-task like "implement tasks 1-6." Each worker gets one bounded task and
returns to the parent plan.

### Before each action

Print what you're about to do. Use a consistent prefix so the human can scan the log:

```
> Launching worker: hercules — task #2, modify calc_defense_effectiveness()
> Executing locally: codex-parent — task #6, interpret calibration results
> Launching worker: hippocrates — task #4, run fast test suite
> Integrating worker result: aristotle — task #8, profiler analysis
```

The prefix tells the human whether work is local or delegated, which task number is
active, and what it does.

### Respect the model annotations

`[haiku]` tasks get executed quickly without extended reasoning. `[opus]` tasks get
deliberate thinking — read the relevant context, think through interactions, and
narrate your reasoning before acting. If a `[haiku]` task turns out to need real
reasoning, update the annotation and note the change.

### During each action

Stay within scope. If you notice something unrelated that needs fixing, note it for later —
don't context-switch. Scope creep is how 30-minute tasks become 90-minute tasks.

### After completing each task

1. Mark the task ✓ in TodoWrite
2. **Reprint the full task plan** with updated markers

This is the most important habit. Reprinting the plan after each task:
- Proves you're tracking progress (not just blazing through tool calls)
- Gives the human a clear snapshot at any interruption point
- Forces you to notice if something got skipped

**The reprinting rule:** After completing each task, reprint the FULL checklist
with a status bar. Not "see above." Not a partial update. The full list with
current markers plus a one-line status bar at the top.

**Single plan rule:** There is exactly ONE task plan. Do not maintain a second
copy (e.g., a "tracking" list that echoes the plan without updating). When
you reprint, you are reprinting THE plan — the same one, updated in place.
If the human sees two plans on screen with different completion states, one
of them is wrong.

**Status bar format:** `[X% complete] One sentence on current state.`

```
## Task Plan — [30% complete] Fast tests running, code changes landed.
✓ 1. codex-parent: Load spec, build plan, assign owners                [opus]
✓ 2. hercules: Modify calc_defense_effectiveness() — WEIGHT 3.0→2.0  [sonnet]
✓ 3. hermes: Update constants.toml default                              [haiku]
■ 4. hippocrates: Run fast test suite — all shards pass                 [haiku]
□ 5. hippocrates: Run calibration N=1,200×3 seeds                      [haiku]
□ 6. aristotle: Interpret cal results + decide if tuning needed          [opus]
□ 7. hippocrates: Generate profiler snapshot with pathway metrics       [haiku]
□ 8. aristotle: Analyze profiler — does freed space flow to both?       [opus]
□ 9. marcusaurelius: Update CLAUDE.md with constants and cal results    [sonnet]
□ 10. hermes: Commit, merge to main, push                              [haiku]
```

### Three-call rule

If you make 3 consecutive tool calls without printing narration text between them,
something has gone wrong. Stop, reorient, and narrate what you're doing and why.
Silent chains of tool calls are where plans go off the rails.

---

## Phase 5: Handle Blockers

When you hit something unexpected:

**STOP executing immediately when:**
- A test fails that the plan expected to pass
- A file or function referenced in the plan doesn't exist
- You're unsure which of two approaches is correct
- The results of a step contradict the plan's assumptions
- You've been working on a single task for significantly longer than expected
- An external dependency is missing or broken
- A required tool, file, dependency, or instruction is unavailable

**What to do when stopped:**
1. Mark the current task ✗ (blocked)
2. Reprint the full task plan showing current state
3. Describe what went wrong in plain language
4. Propose options if you have them, but don't pick one without approval
5. Wait for direction

**Do not:**
- Guess and keep going ("it's probably fine")
- Try a different approach without saying so
- Skip the blocked task and come back later (unless explicitly told to)
- Retry the same thing more than twice
- Silently change scope or absorb a failed task without updating the plan

---

## Phase 6: Close Out

After all tasks show ✓ (or the sprint reaches a defined stop condition), print the
close-out. The close-out begins with the sprint ID and follows this exact structure:

```
[SPRINT-ID]   Phase 6: Close-Out — SPRINT-NAME (Outcome Type)

Problem: 1-2 sentences — what was broken, missing, or inadequate before this work
started, or what opportunity/goal motivated it. Restate from the dispatch spec in
plain language.

Result: 1-2 sentences — what was done and what happened. Name the specific changes
(constants tuned, functions added, architecture decisions made) and whether the
outcome was success, partial, or pivot stop. If the work was empirically falsified
or a gate triggered early stop, say so directly.
---
Task Plan — SPRINT-NAME | [X% of authorized scope] Outcome summary.
✓ 1.   codex-parent:   Load spec, build plan, assign owners                  [opus]
✓ 2.   hercules:       Modify calc_defense_effectiveness() — WEIGHT 3.0→2.0 [sonnet]
...
✗ 9.   socrates:       Full-cal N=1,200×3 — CANCELLED (pivot stop)          [sonnet]
---
Worker Utilization Summary
┌─────────────┬────────────────┬──────────────────────────────────────────────┐
│    Owner    │     Tasks      │                  Key output                   │
├─────────────┼────────────────┼──────────────────────────────────────────────┤
│ codex-parent │ #1, #6, #10   │ Coordination, integration, decisions          │
│ hermes      │ #3, #10        │ 2 commits; repository updates                │
│ hercules    │ #2             │ Single-line constant edit                     │
│ aristotle   │ #6, #8         │ Cal interpretation; profiler analysis         │
│ hippocrates │ #4, #5, #7     │ 1,990 tests; 1 stale-bound catch             │
│ marcusaurelius │ #9          │ CLAUDE.md + cal results documented            │
└─────────────┴────────────────┴──────────────────────────────────────────────┘
Effort mismatch to flag: [specific mismatch if any — model annotation vs actual
complexity, disproportionate token consumption, or task that needed a different
role/effort level than planned, etc.]
---
Repository state: [commit hash, merge/push status, notable remaining changes]
Key engineering finding for Cowork: [the single most important technical insight
from this sprint that affects future work — not a summary of what was done, but
what was learned]
```

**Outcome types** (use in the header after the sprint name):
- **(Complete)** — all tasks ✓, tests pass, merged to main
- **(Partial)** — some tasks complete, changes preserved for later integration
- **(Pivot Stop)** — work empirically falsified or gate triggered early stop
- **(Blocked)** — escalated to user, awaiting direction

**Close-out rules:**
- The sprint ID appears first, before "Phase 6" — it anchors the entire block
- Task Plan uses the sprint name (not generic), with the percentage reflecting
  authorized scope completed (100% is valid even with cancelled tasks if the
  cancellation was the authorized response to a gate trigger)
- Worker Utilization uses a compact summary table (owner → tasks → key output),
  not the verbose duration/tokens/tool-calls breakdown. The detail matters for
  performance analysis but not for the close-out record. If performance
  recommendations are warranted, append them after the close-out block.
- Git state and Key engineering finding close the block — these are what Cowork
  reads first when processing a close-out into a Pointer Close-Out Report

**Performance Recommendations** (append after the close-out block when warranted):
Focus on three dimensions with concrete task references:
- **Tool efficiency**: redundant or collapsible tool-call sequences
- **Token efficiency**: tasks consuming disproportionate tokens relative to
  task complexity; model annotation changes needed
- **Speed**: critical-path bottlenecks; parallelizable tasks that ran sequentially

Be concrete — "Tasks #4 and #7 were both labeled hippocrates and ran
sequentially, but have no dependency — run them in parallel to save ~1m 20s."

---

## The Rationalization Table

Before skipping narration, skipping a reprint, or taking a shortcut, check this table.

| What you'll think | Why it's wrong |
|---|---|
| "I'll narrate the next one, this one's trivial" | Trivial actions compound. Skip one, skip ten. |
| "Reprinting the plan again is redundant" | Redundancy IS the point. It's a forcing function. |
| "I know what I'm doing, don't need the checklist" | Confidence without tracking is how steps get skipped. |
| "I'll fix this unrelated thing while I'm here" | Scope creep. Note it, finish the plan, then address it. |
| "This blocker is minor, I can work around it" | Minor blockers become major regressions. Stop and report. |
| "The human can see what I'm doing from the tool calls" | Tool calls show WHAT. Narration shows WHY. Both matter. |
| "I'll just skip the role label; this one's obvious" | The role label tells the human what kind of work is happening. Keep the label, even for small tasks. |
| "This task needs my full attention, so I'll ignore the checklist" | Serious tasks need more structure, not less. Keep the plan visible while doing the hard part. |
| "This step failed, but I can quietly work around it" | Mark it blocked or revise the plan explicitly. Silent workarounds create false confidence. |
| "There's no doer role defined, so I'll invent a new process" | Use the generic role labels: hermes, hercules, aristotle, hippocrates, marcusaurelius, plato. |
| "I need to preload everything before I can start" | Read enough context to act safely, then proceed. Planning should reduce drift, not become the work. |
| "I'm running low on tool budget, I'll stop tracking the plan" | The plan becomes more important under pressure. Trim scope only by explicitly updating the task list. |
| "I need to keep a second copy of the plan for tracking" | One plan, one location. The reprinted plan IS the tracking mechanism. A second plan drifts from the first and confuses both you and the human. |

---

## Project-Specific Overlays

This skill provides the generic execution framework. Projects can layer additional
requirements on top without modifying this skill.

**How to add a project overlay:**
In your dispatch prompt or agent brief, add an `EXECUTION RULES` block that references
this skill and adds project-specific constraints. Example:

```
### EXECUTION RULES (Virtuoso + project overlay)
- All rules from Virtuoso skill apply
- Additional: clear __pycache__ after every engine edit
- Additional: run segmented 4-shard test suite, not single pytest command
- Additional: include worker utilization in summary (which child workers were used)
```

The overlay inherits everything from this skill and adds to it. The skill handles the
universal execution discipline; the overlay handles project-specific requirements.

---

## Worktree Governance Staging

Worktree-resident sprints (any virtuoso-executed work running in a `git worktree`-
isolated directory) have a structural conflict surface: if the sprint edits main
governance documents directly, those edits conflict with any concurrent Cowork-side
governance work on canonical main. The conflict either surfaces at pre-merge rebase
(friction) or produces silent-revert behavior (governance content lost undetected).

This section eliminates that conflict surface by making worktree-resident sprints
structurally incapable of editing main governance documents.

### Rule 1 — Worktree-Resident Sprints MUST NOT Edit Main Governance Documents

During worktree-resident execution, virtuoso's task plan must not include direct
edits to documents classified as "main governance." The classification is project-
specific and lives in the project's CLAUDE.md (or equivalent) under a section
titled **"Main Governance Documents — Worktree Edit Prohibition."**

Virtuoso reads that list at sprint start (Phase 1). If no such section exists in
CLAUDE.md, the prohibition still applies to any document that:
- Spans multiple sprints (roadmaps, sprint queues, constitutions)
- Is edited by Cowork between sprints (SRL catalogs, debt logs, technical references)
- Contains the dispatch spec for the currently-running sprint (the inline full spec)

If a task in the task plan would edit a main governance document, virtuoso rewrites
that task to write to the staging file instead (see Rule 2).

### Rule 2 — All Governance-Change Intent Goes to a Staging File

For every governance change the sprint would otherwise make to a main governance
document, virtuoso writes the change-intent to a staging file in the worktree:

```
<close-out-directory>/Memo.<sprint-id>.GovernanceStaging.<YYYY-MM-DD>.md
```

(Where `<close-out-directory>` is wherever the project's close-out memos live —
typically `2 operational/` or equivalent.)

The staging file is created on first governance-change-intent and appended to
throughout the sprint. It contains all the changes that would normally land in
main governance docs — formatted as **fold-in instructions**, not as raw edits.

### Rule 3 — Staging File Structure

The staging file is organized so pointer-closeout can mechanically apply each entry.
Section headers name the target document; entries within name the target section
and the fold-in action.

```markdown
# Sprint Close-Out Governance Staging — <sprint-id>

This file enumerates every governance change the sprint would have made to
main governance documents during execution, but staged here per virtuoso's
worktree-edit prohibition. pointer-closeout processes this file at sprint
close to apply the fold-ins to canonical main.

## Target: <document-name>

### Fold-in N — <short description>
Section: §<target section heading>
Action: <Append row | Replace | Insert after | Remove>
Content:
<exact content to fold in — verbatim, ready to paste>
```

**Fold-in action types:**

| Action | Meaning |
|--------|---------|
| **Append row** | Add content at the end of a table or section |
| **Replace** | Overwrite existing content with new content (include `Old:` and `New:` blocks) |
| **Insert after** | Add content after a named anchor (line, heading, or entry) |
| **Remove** | Delete specified content (include the exact content to remove) |
| **Migrate** | Move content from one location to another (include source and destination) |

**Ordering rule:** Within a single target document, fold-ins are numbered
sequentially and processed in order. Dependencies between fold-ins within the
same target are implicit in the numbering. Cross-target fold-ins have no ordering
constraint unless explicitly noted.

**Mid-Dispatch Amendment fold-ins:** When the mid-dispatch-decision skill adds
amendment entries, they use the `Migrate` action type with source = inline spec
subsection and destination = close-out memo §Mid-Dispatch Decisions. These must
be processed BEFORE inline spec collapse fold-ins (so amendment content is
preserved before the spec containing it gets collapsed).

### Rule 4 — pointer-closeout Processes the Staging File as Wave 2 Step 0

pointer-closeout's existing Wave 2 procedure gains a new first step:

**Step 0 (NEW): Read and process the sprint's staging file.**

If `Memo.<sprint-id>.GovernanceStaging.<date>.md` exists in the worktree (or has
already merged from the worktree), pointer-closeout:

1. Parses all fold-in instructions
2. Applies them to canonical main as Edit calls against the named target documents
3. Processes Mid-Dispatch Amendment migrations BEFORE inline spec collapses
4. After applying all fold-ins, deletes the staging file (it has served its purpose)

The close-out memo is the durable record. The staging file is transient infrastructure.

**Discrepancy handling:** If a fold-in instruction conflicts with current canonical
main state (e.g., the target section no longer exists, or content has changed since
the fold-in was staged), pointer-closeout surfaces the discrepancy as a reconciliation
prompt to the user rather than silently overwriting or failing.

### Rule 5 — Mid-Dispatch Amendments Use the Staging File

The mid-dispatch-decision skill currently writes amendment blocks directly to the
dispatch spec (which is in a main governance document). Per Rule 1, this is the
exact write virtuoso forbids.

**Integration:** mid-dispatch-decision writes the amendment to the staging file
under a fold-in entry, NOT to the inline spec. Specifically:

```markdown
## Target: <roadmap-document>

### Fold-in N — Mid-Dispatch Amendment (<amendment title>)
Section: §<sprint-id> (inline full spec)
Action: Migrate
Source: This amendment block (below)
Destination: Close-out memo §Mid-Dispatch Decisions
Content:
##### Mid-Dispatch Amendment — <date> — <title>
Decision Type: <type>
Context: <what CLI reported>
Decision: <what was decided>
Rationale: <why>
```

The mid-dispatch-decision skill's Step 6b becomes: "Append amendment to the sprint's
staging file under the appropriate target document section." The Close-Out Preservation
field becomes implicit — the staging file IS the preservation contract. The conflict-
surface check becomes unnecessary because the conflict surface no longer exists.

### Rule 6 — Cowork-Side Sprints Follow the Same Pattern by Default

Cowork-side governance work that runs in a single session (e.g., /pointer-closeout,
/roadmap-review, /governance-sweep) doesn't have a worktree boundary, so the conflict
surface doesn't apply in the same way. But the staging-file pattern still has value:

- Cowork's mid-session governance edits become recoverable if the session crashes
- The staging file documents WHAT changed and WHY for the change summary
- It provides an audit trail of governance mutations within the session

**Enforcement level:**
- **Worktree-resident CLI dispatches:** staging file is **mandatory**. Virtuoso
  rejects any task plan that edits main governance documents directly.
- **Cowork-side sessions:** staging file is **optional** (best practice, not enforced).
  Cowork may edit main governance documents directly since there's no worktree
  boundary to create conflicts.

### Migration — Sprints Already in Flight

Sprints dispatched before this pattern was introduced continue under the old pattern
(mid-dispatch-decision writes amendments inline to the roadmap). The new staging-file
pattern starts with the next sprint dispatched after this skill update.

When processing a close-out for a grandfathered sprint, pointer-closeout checks for
BOTH: a staging file (new pattern) and inline Mid-Dispatch Amendment blocks with
Close-Out Preservation instructions (old pattern). If both exist, surface as a
reconciliation prompt. The transition point should be noted in CLAUDE.md so it's
clear which sprints used which pattern.

### What This Prevents

The pattern of:
1. Cowork edits canonical main governance doc
2. Worktree edits same file from a stale base
3. Pre-merge rebase produces conflict (visible) OR silent revert (invisible)
4. Governance content potentially lost or scrambled

Under the new pattern: the worktree NEVER edits canonical main governance documents.
Conflicts on those files between worktree and Cowork are structurally impossible.
The staging file consolidates intent; pointer-closeout applies it once at close-out,
with full visibility of any concurrent Cowork edits at that moment.

**Trade-off:** pointer-closeout becomes mechanically heavier (more fold-ins to process)
and the staging file is one more artifact per sprint. Both are small costs for the
structural elimination of a recurring failure mode.
