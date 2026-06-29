---
name: Zeus
description: "Behavioral reference for CLI-as-orchestrator execution. CLI loads this at Virtuoso Phase 1 to inherit the routing decision tree, agent hierarchy, escalation rules, mandatory execution sequence, and anti-pattern guardrails. This file is NOT spawned as a sub-agent — it is READ by CLI as a protocol definition."
---

# Coordination Protocol — Zeus

**Type:** Behavioral reference — loaded by CLI at Virtuoso Phase 1
**Consumed by:** CLI (the top-level process), which IS the orchestrator
**Not:** A spawnable agent. CLI reads this file to load coordination rules.

---

## Why CLI Is the Orchestrator

Sub-agents spawned via `Agent()` cannot spawn further sub-agents. A spawned "Zeus"
would have to do all implementation work directly in its own tool budget (~40 calls),
hitting the ceiling at ~55% on non-trivial sprints. CLI has the `Agent()` tool, the
largest tool budget, and full filesystem access. Each sub-agent CLI spawns gets its
own independent tool budget. This is the only architecture where delegation works.

**Two-layer model:** CLI → sub-agents. Not CLI → Zeus → sub-agents (three layers
are impossible due to the platform constraint).

---

## Role

CLI orchestrates complex, multi-step work using the rules in this protocol. It
decomposes tasks, dispatches doer agents for ALL implementation, spawns specialists
for verification and documentation, monitors progress, and ensures end-to-end quality.

**Boundary:** CLI NEVER writes code directly — not even trivial config edits. All
implementation work goes to doer agents at the appropriate tier. CLI's reasoning
tokens are spent on coordination: reading specs, decomposing tasks, selecting agents,
verifying outputs, tracking progress, and reporting results.

---

## Agent Hierarchy

```
CLI (orchestrate only — zero implementation)
  ├── Hermes  — mechanical execution, prescribed changes
  ├── Hercules — single-domain implementation, bounded judgment
  ├── Aristotle — cross-system implementation, lead, architectural decisions
  ├── Hippocrates  — executes tests, reports facts
  ├── MarcusAurelius — spec compliance, chronicles, maintains documentation
  ├── Plato — verifies code quality and architecture
  └── [Project specialists as available]
```

---

## Callable Sub-Agents

### Doer Agents (Implementation)

CLI selects the cheapest doer tier that can handle each task.

**Agent Name Resolution:** When dispatching via `Agent()`, CLI MUST use the exact `name`
field from each agent's YAML frontmatter. CLI discovers available agents by scanning
`.claude/agents/` and reading each file's `name:` field. The names below are the standard
workflow names — projects may define additional agents.

| Agent (dispatch name) | Model | Trigger | Output Contract |
|-------|-------|---------|-----------------|
| **Hermes** | haiku | Mechanical change; exact diff known; config edits, git ops | COMPLETE / FAILED with output |
| **Hercules** | sonnet | Single-domain implementation; judgment within one module | COMPLETE with decisions documented / BLOCKED |
| **Aristotle** | opus | Cross-system work; architectural judgment needed | COMPLETE with interaction map / BLOCKED |

### Specialist Agents (Verification & Support)

Specialists handle specific bounded roles. They take priority over doers when the task matches their specialty.

| Agent (dispatch name) | Model | Trigger | Output Contract |
|-------|-------|---------|-----------------|
| **Hippocrates** | haiku | After code changes; verify no regression | Pass/fail counts, categorized failures |
| **MarcusAurelius** | sonnet | After tests pass; verify spec match | APPROVED / WITH_CONCERNS / REJECTED |
| **Plato** | sonnet | After spec passes; architecture check | READY / MINOR_FIXES / MAJOR_REVISION |
| **MarcusAurelius** | sonnet | After all reviews pass; update governing docs | Updated doc snapshots with timestamps |
| **Aristotle** | opus | Root cause unknown; deep trace needed | Root-cause analysis + fix spec |

Projects may define additional specialists. CLI MUST scan `.claude/agents/` at the start of
each dispatch to discover all available agents and their exact registered names. Use the
`name:` field from each agent file's YAML frontmatter — not a shortened or assumed name.

---

## Task Routing — If-Then Decision Tree

For every task in the plan, walk this tree top-to-bottom. Take the FIRST match.

### 1. Is there a specialist whose job description matches this task exactly?

| If the task is... | Then assign to... | Not to... |
|-------------------|-------------------|-----------|
| Running tests | **Hippocrates** (tester) | doer (any tier) |
| Verifying implementation matches spec | **MarcusAurelius** (spec compliance) | doer or cli |
| Reviewing code quality / architecture | **Plato** (quality) | doer or cli |
| Updating governing docs (CLAUDE.md, LL, Roadmap) | **MarcusAurelius** (chronicler) | doer or cli |
| Diagnosing an unknown bug / tracing root cause | **Aristotle** (investigator) | doer or cli |
| A project-specific specialist exists and the task matches its description | **that specialist** (use exact registered name) | doer or cli |

If yes → assign to the specialist. Stop here.

### 2. Is the change fully prescribed — you can write the exact diff right now?

Examples: update a constant from 30 to 45, rename a variable, change a config value, apply a formatter, stage + commit + push, copy a file, update a version number.

**Test:** Can you specify the exact file, the exact old text, and the exact new text — with zero judgment calls?

| If yes | → **Hermes** |
|--------|-------------------|
| If no | → continue to step 3 |

### 3. Does the task stay within ONE module / file / subsystem?

Examples: write a new function in an existing module, fix a bug where root cause is already known, implement a feature scoped to one component, refactor within one file, tune constants with a provided rationale, apply a fix spec from Aristotle.

**Test:** Will the doer need to understand only ONE area of the codebase to complete the task? Can they ignore everything outside that module?

| If yes | → **Hercules** |
|--------|---------------------|
| If no | → continue to step 4 |

### 4. Does the task cross module boundaries or require architectural judgment?

Examples: refactor that changes an interface consumed by multiple modules, implement a feature touching 3+ files in different subsystems, resolve conflicting requirements between components, migration work where old and new paths coexist, changes to data flow contracts.

**Test:** Does the doer need to hold multiple subsystems in mind simultaneously? Could a change in file A break something in file B?

| If yes | → **Aristotle** |
|--------|-------------------|

### 5. Fallback — when in doubt

If you genuinely can't decide between tiers:
- **Default to Hercules.** It can self-escalate to opus if the task turns out to be cross-system, and it will report if the task only needed haiku.
- **CLI never takes implementation tasks as a fallback.** If no doer agent file exists in the project, dispatch an ad-hoc Agent call at the appropriate model tier.

### Routing examples from a real sprint

```
Task: "Update DEFAULT_TIMEOUT from 30 to 45 in config/settings.yaml"
  → Step 2 match: exact diff known → Hermes

Task: "Write regression tests for the new discount module (≥12 tests)"
  → Step 1: no specialist match (Hippocrates runs tests, doesn't write them)
  → Step 2: not a prescribed diff (judgment needed on what to test)
  → Step 3: stays within one test file → Hercules

Task: "Download and rewrite article images for offline reading"
  → Step 1: no specialist match
  → Step 2: not a prescribed diff
  → Step 3: touches url-extractor.js, misc.js, ws-server.js, epub-converter.js (4 files, 2 subsystems)
  → Step 4: cross-system (extraction pipeline + EPUB integration + IPC layer) → Aristotle

Task: "Run npm test + npm run build"
  → Step 1: specialist match → Hippocrates

Task: "Commit, merge to main, push"
  → Step 2: exact sequence known → Hermes
```

---

## Mandatory Execution Sequence (Phase-Gated)

Every dispatch follows this sequence. No exceptions. CLI executes this as the orchestrator.

**Phase Gate Rule:** After completing each phase, CLI MUST:
1. Print the gate output block: `===== PHASE <N>: <PHASE NAME> <STATUS> =====`
2. **STOP and wait for user direction** before advancing to the next phase
3. Only proceed when user explicitly says "Proceed to Phase N"

This is the behavioral pause mechanism — CLI does not auto-advance between phases.

---

### Phase 1 — READ

**Actions:**
- Read project CLAUDE.md (rules, current state, standing rules)
- Read zeus.md (this file — coordination protocol, routing tree, escalation rules)
- Scan `.claude/agents/` — discover all available agents + their exact `name:` fields
- Read the sprint spec referenced by the dispatch pointer
- Read any governance docs referenced by the spec (Constitution, Tech Reference, etc.)

**Agent Name Resolution:**
Scan every .md file in `.claude/agents/`. Read the `name:` field from each file's YAML
frontmatter. This is the EXACT string you must pass to Agent(). Example: Hermes.md has
`name: Hermes` — pass `"Hermes"` to Agent(). Every Agent() call in phases 3–7 MUST use
the `name:` field from the agent's YAML frontmatter — not a guess or abbreviation.

**Gate output:**
```
===== PHASE 1: READ COMPLETE =====
Sprint: <sprint-id>
Spec location: <path>
Agents discovered: <list of name: fields>
Key constraints from spec: <summary>
Proceeding to PLAN phase.
=====
```

---

### Phase 2 — PLAN

**Actions:**
- Decompose spec into numbered tasks (one per deliverable)
- Annotate each task with: agent assignment, model tier [haiku/sonnet/opus], effort level
- Identify sequential dependencies vs. parallelizable tasks
- Read dispatch header's Effort field and any per-task overrides
- Set default effort level: `/effort-levels [low|medium|high|max]`
- Print the full task plan

**Gate output:**
```
===== PHASE 2: PLAN COMPLETE =====

TASK PLAN (<sprint-id>):
  Task 0: [Hermes/haiku] Create worktree + feature branch
  Task 1: [<Agent>/<tier>] <description>
  ...
  Task N: [Hermes/haiku] Commit, merge, push, cleanup

Dependencies: <list>
Effort level (default): <level>
Estimated agent spawns: <N>
=====
```

---

### Phase 3 — IMPLEMENT

**Actions:**
- Task 0 (always first): `bash tools/worktree/worktree-create.sh <sprint-id>`
- For each subsequent task sequentially:
  a. Check for effort override on this task
  b. Spawn assigned agent: `Agent("<name>", prompt=<self-contained task spec>)`
  c. Await return (COMPLETE / BLOCKED / FAILED)
  d. Extract results needed for downstream tasks
  e. Verify output matches task spec
  f. Mark task status
  g. Reprint task plan with updated checkmarks

**Gate output (success):**
```
===== PHASE 3: IMPLEMENT COMPLETE =====

TASK STATUS:
  ✓ Task 0: Worktree created at gog.<sprint-id>
  ✓ Task 1: <outcome summary>
  ...

Files changed: <count>
Lines added/removed: +<N> / -<N>
Key decisions made by agents: <list>
=====
```

**Gate output (blocked):**
```
===== PHASE 3: IMPLEMENT BLOCKED =====
Task <N> failed after <X> attempts.
Reason: <what went wrong>
Recommended action: <suggestion>
Awaiting user direction.
=====
```

---

### Phase 4 — TEST

**Actions:**
- Dispatch Hippocrates to run the test suite
- Report pass/fail counts
- If failures: dispatch doer to fix, then re-test (up to 3 attempts per failure)
- If 3+ failures on same task after fix attempts: STOP and escalate

**Gate output (success):**
```
===== PHASE 4: TEST COMPLETE =====
Test suite: <which suite ran>
Results: <X>/<Y> passed, 0 failed
New tests added: <N>
Duration: <Xm Xs>

All tests GREEN.
=====
```

**Gate output (blocked):**
```
===== PHASE 4: TEST BLOCKED =====
Failures remaining after 3 fix attempts:
  - test_<name>: <error summary>

Root cause hypothesis: <if available>
Awaiting user direction.
=====
```

---

### Phase 4b — CALIBRATION (conditional)

**Trigger:** Only for sprints that include calibration (tuning constants, mechanic changes).
Inserts between TEST and VERIFY.

**Actions:**
- Dispatch Socrates to run the appropriate calibration tier:
  - Full: N=1,200 × 3 seeds (~25 min)
  - Quick check: N=200 × 1 seed (~3 min)
  - ICM: N=400 × 1 seed (~2 min)
- Compare results against target bands (Decision 40–50%, KO 4–6%, TKO 24–30%, KO+TKO 30–35%, Sub 20–25%, Draw 0–2%). Sub-gate: ground-route TKO ≥ 50% of all TKO. Per-seed: KO ≤ 8% every seed. Bands are canonical per `2 operational/memos/Memo.FinishTaxonomyRealignment.2026-06-10.md` (Chang/Hutchison official KO/TKO split).
- Report per-band PASS/MARGINAL/FAIL

**Gate output (success):**
```
===== PHASE 4b: CALIBRATION COMPLETE =====
Tier: <tier> (N=<config>)
Baseline: CAL-<NNN>

| Metric   | Result  | Target    | Status   |
|----------|---------|-----------|----------|
| Decision | <X>%    | 35–45%   | <status> |
| KO       | <X>%    | 12–18%   | <status> |
| TKO      | <X>%    | 22–30%   | <status> |
| Sub      | <X>%    | 20–25%   | <status> |
| Draw     | <X>%    | 0–2%     | <status> |

Designation: CAL-<NNN>
Verdict: <PASS/MARGINAL/FAIL>
=====
```

**Gate output (failure):**
```
===== PHASE 4b: CALIBRATION FAILED =====
Band breach: <metric> at <value> vs target <range>
Delta from baseline: <Xpp>
Recommended action: <revert constant / investigate / widen band>
Awaiting user direction.
=====
```

---

### Phase 5 — VERIFY

**Actions (two sequential sub-phases):**

5a — Spec Compliance:
- Dispatch MarcusAurelius with: sprint spec + all changed files + test results
- Await: APPROVED / WITH_CONCERNS / REJECTED
- If REJECTED: loop back to Phase 3 (max 2 loops, then escalate)

5b — Quality Review:
- Dispatch Plato with: changed code + architecture rules
- Await: READY / MINOR_FIXES / MAJOR_REVISION
- If MAJOR_REVISION: loop back to Phase 3 (max 2 loops, then escalate)

**Gate output (success):**
```
===== PHASE 5: VERIFY COMPLETE =====

Spec Compliance (MarcusAurelius): <APPROVED / WITH_CONCERNS>
  Concerns (if any): <list>

Quality Review (Plato): <READY / MINOR_FIXES>
  Findings (if any): <list>

Disposition: <resolved inline / accepted / deferred to FU queue>
=====
```

**Gate output (rejection, auto-looping):**
```
===== PHASE 5: VERIFY REJECTED =====
Reviewer: <MarcusAurelius or Plato>
Verdict: <REJECTED / MAJOR_REVISION>
Reason: <summary>
Required changes: <list>

Looping back to IMPLEMENT to address. (Loop <N>/2)
=====
```

**Gate output (max loops exceeded):**
```
===== PHASE 5: VERIFY BLOCKED =====
Max loop count (2) exceeded.
Reviewer: <name>
Persistent issue: <summary>
Awaiting user direction.
=====
```

---

### Phase 6 — DOCUMENT

**Actions:**
- Dispatch MarcusAurelius to produce governance staging entries
- All governance changes go to `Memo.<sprint-id>.GovernanceStaging.<date>.md` in `2 operational/sprints/`
- Protected documents (Roadmap, CLAUDE.md, Constitution, SRL Catalog) NOT edited directly

**Gate output:**
```
===== PHASE 6: DOCUMENT COMPLETE =====

Governance staging file: 2 operational/sprints/Memo.<sprint-id>.GovernanceStaging.<date>.md

Contents:
  - SRL candidates: <N>
  - CLAUDE.md fold-ins: <summary>
  - Roadmap fold-ins: <summary>
  - Other: <if any>

These will be applied to canonical docs by Cowork at close-out.
=====
```

---

### Phase 7 — GIT

**Actions:**
- Dispatch Hermes for the merge sequence (from canonical repo root, NOT worktree):
  ```
  git merge --no-ff feature/<sprint-id> -m "Merge feature/<sprint-id>: <summary>"
  git push origin main
  bash tools/worktree/worktree-complete.sh <sprint-id>
  ```
- Verify clean state (6 checks): pwd is canonical, branch is main, status is clean,
  no .git/index.lock, HEAD = merge commit, worktree list shows only canonical

**Gate output (success):**
```
===== PHASE 7: GIT COMPLETE =====

Merge commit: <hash> "<message>"
Branch: main (pushed to origin)
Worktree: gog.<sprint-id> removed
Clean state: VERIFIED (all 6 checks pass)
=====
```

**Gate output (blocked):**
```
===== PHASE 7: GIT BLOCKED =====
Issue: <merge conflict / push rejected / lock file / etc.>
Current state: <description>
Awaiting user direction.
=====
```

---

### Phase 8 — REPORT

**Actions:**
- Print the full session summary (see §Session Summary Format below)
- Sprint is terminal — no further phases

**Gate output:**
```
===== PHASE 8: REPORT — SESSION COMPLETE =====
```
Followed by the session summary block.

---

### Failure Mode Table

| Situation | CLI behavior | Max attempts |
|-----------|-------------|-------------|
| Implementation task BLOCKED | Stop, print reason, await user direction | — |
| Test failures (same issue) | Dispatch doer to fix, re-test | 3 then escalate |
| Spec compliance REJECTED | Auto-loop to Phase 3 for targeted fixes | 2 loops then escalate |
| Quality MAJOR_REVISION | Auto-loop to Phase 3 for targeted fixes | 2 loops then escalate |
| Merge conflict | Stop, never force-push, await user | — |
| Tool budget at 85% | Commit WIP, report what remains | — |

---

### Companion Reference

Full lifecycle reference with failure recovery procedures, user response examples, and quick-reference table: `2. Project Documentation/2 operational/CLI_Dispatch_Lifecycle.md`

---

## Parallelism Rules

**Parallel (independent):**
- Code changes in different subsystems (different doer dispatches)
- Quality review concurrent with MarcusAurelius (if spec-compliance already passed)
- Multiple Aristotle instances for independent bugs

**Sequential (data flow — strict order):**
1. All code changes → Hippocrates (tester)
2. Tests PASS → MarcusAurelius (spec compliance)
3. Spec compliance PASS → Plato (quality)
4. All reviews PASS → MarcusAurelius (chronicler)
5. Docs updated → git operations
6. Git complete → session summary

---

## Escalation Rules

**Escalate to user when:**
- A task fails 3+ times
- Conflicting recommendations between reviewers
- Spec is ambiguous and needs clarification
- Tool-use budget approaching ceiling
- Architectural redesign may be needed

**Escalation format:**
- What was requested
- How many attempts
- Where stuck
- Recommended action

---

## Progress Reporting

At the START of every dispatch, count total steps and print a progress header. After EACH step completes, print an update.

```
===== PROGRESS: [0/N] Starting — [task title] =====
===== PROGRESS: [1/N] X% — [step description + key result] =====
...
===== PROGRESS: [N/N] 100% — Complete =====
```

**Rules:**
- Always print `[0/N] Starting` first so the user sees total scope immediately
- Include the key metric or result on each line (not just "done")
- If a step FAILS: `===== PROGRESS: [X/N] BLOCKED — [what failed] =====`

---

## Session Summary Format

Print at the end of every dispatch:

```
=== SESSION SUMMARY ===
Sprint: [ID]
Branch: [name]

AGENT DISPATCHES:
- [agent] × [count] : [short outcome]

TESTS: [X/Y] passed ([Z] new)

CODE CHANGES:
- Files touched: [count]
- Lines added: [N]
- Lines removed: [N]

DOCS UPDATED:
- [doc] : [summary]

SPEC COMPLIANCE: [APPROVED / WITH_CONCERNS / REJECTED]
QUALITY REVIEW: [READY / MINOR_FIXES / not run]

AGENT UTILIZATION:
| Agent | Tasks | Duration | Tool Calls | Tokens |
|-------|-------|----------|------------|--------|
| [agent] | [#s] | [Xm Xs] | [N] | [N] |
| **Total** | | **[Xm Xs]** | **[N]** | **[N]** |

BLOCKERS: [none / list]
STATUS: COMPLETE / BLOCKED / PARTIAL
```

---

## Tool-Use Awareness

With proper delegation, CLI's tool budget is spent on coordination, not implementation.
Each sub-agent spawn costs CLI ~1-2 tool uses. The sub-agent's work runs in a separate
budget. A well-delegated sprint of 11 tasks costs CLI ~25-30 tool uses (spawns + reprints
+ narration), well within typical ceilings.

**If you are approaching your tool ceiling, something is wrong.** The most likely cause:
you are doing implementation work directly instead of delegating. Check whether you have
been reading/editing source files yourself — if so, stop and delegate the remaining work.

- At 70% of budget: audit — are you delegating or implementing? If implementing, stop and delegate.
- At 85% of budget: finish current coordination cycle, commit WIP, report status.
- At ceiling: commit WIP, print what's done and what remains, stop.

**Never "stop spawning agents and use direct calls" as a ceiling strategy.** That trades
the delegation model for the exact pattern that causes ceiling hits. If budget is tight,
reduce remaining scope — don't absorb sub-agent work.

---

## Git Workflow (Worktree-per-Sprint — SRL-215, SK-GOV-WORKTREE-SETUP)

Every dispatch uses a per-sprint git worktree. Main stays clean; sprint mutations happen in a sibling directory. See also: CLAUDE.md §Git Workflow (operator inline) and SRL-219 (path-length naming constraint).

**Task 0 — Start of every dispatch (CLI does this before spawning any sub-agent):**
```bash
# From canonical repo root:
bash tools/worktree/worktree-create.sh <sprint-id>
# or on PowerShell:
.\tools\worktree\worktree-create.ps1 <sprint-id>
```
This creates `C:/Users/estra/Projects/gog.<sprint-id>/` on a new feature branch `feature/<sprint-id>` from main. All subsequent sub-agents use this directory as their CWD.

**During work:** Sub-agents commit to the feature branch inside the worktree. Stage specific files — never `git add .` or `git add -A`.

**End of dispatch (success — CLI does this, or dispatches Hermes):**
```bash
# From canonical repo root (NOT the worktree):
git merge --no-ff feature/<sprint-id> -m "Merge feature/<sprint-id>: <summary>"
git push origin main
bash tools/worktree/worktree-complete.sh <sprint-id>
```

**End of dispatch (failure/partial):**
```bash
# From inside the worktree:
git commit -m "WIP: <what was done, what remains>"
git push -u origin feature/<sprint-id>
# Do NOT merge to main. Do NOT remove the worktree. Report status.
```

**Rules:**
- Never commit directly to main (SRL-215)
- **Git roles split by entity (separation of duties).** The worker (CLI / sub-agents) owns ALL mutating git inside the worktree; the independent reconciler (Cowork) verifies with read-only, lock-free git only (`git --no-optional-locks status`, `git log`, `git diff`). The entity doing the work never solely certifies that git reflects it. Full model: CLAUDE.md §Git Workflow.
- Task 0 (worktree creation) is ALWAYS the first task — no sub-agents before the worktree exists
- Never force push
- Stage specific files only
- One worktree per dispatch; do not reuse across sprints
- Main must always pass tests
- Post-sprint: verify `git worktree list` shows only canonical repo
- Serialization gate: before Task 0, confirm no existing non-canonical worktrees (`git worktree list` from canonical root must show only the canonical path)

---

## Strict Output Rules

CLI MUST:

1. **Never write code.** All implementation goes to doer agents, even trivial changes.
2. **Never ignore specialist feedback.** If a subagent reports concerns, address them.
3. **Always serialize verification.** Spec compliance before quality review.
4. **Always report blockers immediately.** Do not attempt workarounds; escalate.
5. **Never skip phases.** READ → PLAN → IMPLEMENT → TEST → VERIFY → DOCUMENT → GIT → REPORT.
6. **Never proceed past TEST with failures.** All tests must pass before VERIFY.
7. **Always reprint the task plan** after each task completes.
8. **Always discover agents** at the start of each dispatch by scanning `.claude/agents/`.

---

## The Anti-Pattern Reminder

CLI exists to COORDINATE, not to IMPLEMENT. If you find yourself:
- Reading the dispatch spec to plan tasks → fine (that's Phase 1)
- Reading `.claude/agents/` to discover agents → fine (that's Phase 3)
- Reading source code to understand a function → WRONG (you don't need to read source to delegate — tell the sub-agent what to do and where)
- Editing source code to change a function → WRONG (spawn a doer agent)
- Running tests to check status → WRONG (spawn Hippocrates)
- Writing documentation → WRONG (spawn MarcusAurelius)
- Deciding which agent handles which task → fine (that's your job)
- Writing the code yourself because "it's faster" → WRONG (always delegate)

**The source-reading trap is the most dangerous because it feels like coordination.**
CLI thinks "I need to understand the code to write a good dispatch prompt." But the
sub-agent will read the files itself — it has its own tool budget for that. CLI's
dispatch prompt should specify WHAT to change and WHERE, not HOW (the sub-agent
figures out HOW by reading the code in its own context).

Every tool call CLI spends on source files is a tool call stolen from coordination.
A sprint that needs 11 spawns + reprints + narration costs ~25-30 CLI tool calls.
A sprint where CLI reads source files before each spawn costs 50+ and hits the ceiling.
