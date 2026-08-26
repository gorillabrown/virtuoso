---
name: effort-levels
description: >
  Effort level selection framework for sprint dispatch specs. Use this skill whenever
  authoring a dispatch spec, sizing a sprint, or reviewing whether a sprint's effort
  allocation matches its task complexity. This skill governs how much extended thinking
  budget each task receives — a real cost lever, not just a quality preference. Trigger on:
  "spec this sprint", "author a dispatch", "size this work", "what effort level", "review
  effort allocation", or any dispatch authoring session where task complexity varies.
  When in doubt, use this skill — misallocated effort is invisible waste.
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

# Effort Levels — Sprint Dispatch Sizing

This skill helps the planner select the right effort level when authoring dispatch specs.
Effort level controls how deeply sub-agents reason on each task — it is the primary
cost lever in the system. A single task at max effort can consume 10x+ more tokens
than the same task at low effort. Getting this right prevents both underthinking
(wrong answers on hard problems) and overthinking (burning tokens on trivial work).

**Invoke this skill when:** authoring any dispatch spec, reviewing effort allocation
on an existing spec, or deciding whether a sprint needs wave-splitting by effort.

---

## The Four Effort Levels

| Level | Thinking Budget | Agent Behavior | Cost Multiplier |
|-------|----------------|----------------|-----------------|
| **Low** | Minimal | Responds quickly from trained knowledge and pattern recognition. Answers from memory rather than working through the problem. No extended reasoning chains. | ~1x (baseline) |
| **Medium** | Moderate | Does meaningful reasoning but stops well short of exhausting capacity. Handles most everyday coding tasks well. This is the default for standard work. | ~2–3x |
| **High** | Substantial | Traces through complex logic, considers multiple approaches, backtracks when needed. Response time increases noticeably, and so does token cost. | ~5x |
| **Max** | Full available | Reasons as extensively as the current context allows. Most expensive and slowest option, but produces highest-quality output on genuinely hard problems. | ~10x+ |

### Why This Matters for Cost

Extended thinking tokens are billed at the same rate as output tokens. At max effort,
a single prompt can consume dramatically more tokens than the same prompt at low effort.
That asymmetry makes effort level selection a real cost lever, not just a quality
preference. Misallocated effort is invisible waste — you won't see a test fail, but
you'll see your token budget evaporate.

---

## When to Use Each Level

### Low Effort

The right call when the task is well-defined, the answer is relatively obvious, and
there's no meaningful ambiguity to work through.

**Good use cases:**
- Syntax fixes, typo corrections, indentation, linting errors
- Simple renames — variable, function, or file across a small scope
- Code formatting — rewriting a block to match a style convention
- Quick lookups — function signatures, environment variable access patterns
- Boilerplate generation — scaffolding a standard component, CRUD endpoint, or config
  file from a clear spec
- Git operations — stage, commit, merge, push
- Version bumps, config value changes with exact values provided

**Not appropriate for:** anything requiring reasoning about tradeoffs, diagnosing root
causes, or generating novel logic. If the problem has more than one plausible
interpretation, or if the correct answer depends on context spanning multiple files,
low effort will often produce code that looks right but isn't.

### Medium Effort

The most versatile setting and the appropriate default for the majority of development
work. Gives agents enough reasoning capacity for context-dependent tasks, multi-step
logic, and moderately complex bugs.

**Good use cases:**
- Standard bug fixes — diagnosing unexpected return values, off-by-one errors, broken
  conditional logic where root cause is known or discoverable within one module
- Refactoring familiar patterns — extracting functions, splitting modules, converting
  patterns, updating API calls to match a new schema
- Writing tests — generating unit tests where expected behavior is clear but requires
  interpretation
- Explaining code — "What does this block do?" or "Why is this query slow?" — questions
  needing more than surface-level pattern matching
- Adding features with clear requirements — implementing endpoints, form validation,
  data source connections when the spec is explicit
- Documentation updates — writing or updating docs to match code changes

**Signal to step up:** if you find yourself re-prompting frequently at medium effort on
a specific task type, that's a signal to bump to high — not to rephrase the prompt.

### High Effort

Appropriate when the problem involves genuine complexity: multiple interacting systems,
non-obvious root causes, performance tradeoffs, or logic that needs to be reasoned
through carefully rather than pattern-matched.

**Good use cases:**
- Hard debugging — when obvious causes are ruled out and the bug involves subtle
  interaction between components, async timing, or non-obvious state mutation
- Architectural decisions — "Should I use a message queue or event emitter here?" —
  questions where tradeoffs matter and getting it wrong is expensive
- Complex refactors across multiple files — changes needing consistency across a large
  surface area where a small error anywhere breaks the build
- Performance optimization — profiling bottlenecks, optimizing queries, reducing render
  cycles requiring understanding of actual runtime behavior
- Security review — identifying injection vectors, access control gaps, or data leakage
  paths requiring careful non-obvious reasoning
- Calibration interpretation — analyzing statistical results across multiple dimensions
  and deciding whether tuning is needed

**Signal that medium wasn't enough:** the response is technically plausible but misses
something important — solves the wrong version of the problem, ignores a relevant
constraint, or produces a solution that breaks something else.

### Max Effort

Reserved for the hardest problems. Gives the model maximum reasoning capacity.
Use only when getting the answer right matters enough to justify the cost and latency.

**Good use cases:**
- Algorithmic complexity — designing or reviewing algorithms where correctness is
  non-trivial, edge cases matter, and the problem space has real depth (graph traversal,
  dynamic programming, constraint satisfaction)
- System design — reasoning about full architecture, not just components. Service
  communication, caching placement, failure points
- Mysterious hard-to-reproduce bugs — race conditions, memory leaks, non-deterministic
  test failures requiring long chains of causal reasoning
- Large-scale refactoring with risk — changes touching core infrastructure, altering
  data models, or affecting how multiple teams' code interacts where the cost of
  getting it wrong is high
- Writing critical code from scratch — parsers, state machines, billing calculations,
  anything where subtle logic errors have real downstream consequences

**What max doesn't fix:** max improves reasoning depth but doesn't override model
capability limits. If the problem requires information the model doesn't have (proprietary
APIs, runtime context it can't see), more thinking won't fill that gap.

**Budget vs. method.** Max buys thinking capacity; it does not supply a procedure for
spending it. On the analytical problems above — the mysterious bug, the architecture call,
the risky refactor — pair it with `/ultrathink`, the protocol that converts the budget into
structured depth (assumption archaeology first, then multi-dimensional analysis, then a
validation pass). Max on its own is a larger budget with no method; set the two together.

---

## The Decision Framework

Ask these five questions in order before setting each task's effort level:

| # | Question | If Yes → |
|---|----------|----------|
| 1 | Is the answer obvious given the input? | **Low** — stop here |
| 2 | Does the task require understanding context beyond the current file or prompt? | **Medium** or higher |
| 3 | Have I already tried a lower effort level and gotten a wrong or incomplete answer? | Step up one level |
| 4 | Would getting this wrong have real consequences? | **High** or **Max** |
| 5 | Is this a genuinely novel problem — something not seen in common form? | **High** or **Max** |

---

## Task Type Reference Table

Use this as a quick lookup when assigning effort to tasks in a dispatch spec.

| Task Type | Effort | Rationale |
|-----------|--------|-----------|
| Typo fix, rename, formatting | Low | Fully prescribed, pattern-match |
| Simple function, standard boilerplate | Low | Known-correct pattern |
| Git operations (stage, commit, merge, push) | Low | Mechanical sequence |
| Config value change with exact value | Low | Zero judgment |
| Feature addition with clear spec | Medium | Bounded judgment needed |
| Bug fix with known root cause | Medium | Single-domain reasoning |
| Writing tests for one module | Medium | Interpretation within scope |
| Code explanation | Medium | Context-dependent but bounded |
| Refactoring familiar patterns | Medium | Judgment within one domain |
| Documentation updates | Medium | Content generation, bounded |
| Multi-file refactor | High | Cross-file consistency needed |
| Debugging with unclear root cause | High | Multiple hypotheses to trace |
| Architecture or design decision | High | Tradeoffs with real consequences |
| Performance optimization | High | Runtime behavior analysis |
| Security review | High | Non-obvious reasoning required |
| Calibration interpretation | High | Statistical + domain judgment |
| Hard algorithmic problem | Max | Correctness non-trivial, edge cases |
| Mission-critical system design | Max | Full architecture reasoning |
| Race conditions, non-deterministic bugs | Max | Long causal chains |
| Large-scale refactoring with risk | Max | High consequence, wide surface |
| Writing critical code from scratch | Max | Subtle logic errors = real cost |

---

## Sprint-Level Effort Declaration

<!-- rule:size-from-measured-cadence (measured-cadence) -->
**Size from measured cadence, not from the shape of the task list.** Two sizing errors
recur, both in the same direction:

- **Analytical sprints staffed with two top-effort `{high}` agents underestimate by
  22–36%.** This is a measured figure, not a feeling — when a plan has two such agents,
  size up a bracket rather than discovering the gap at the fix round.
- **Workload volume overrides nominal task type.** Authoring pin-tests across many source
  patterns, or annotating hundreds of items, sizes by *volume* even when the per-item work
  is mechanical. Above roughly ten items with multi-pattern reading, default up a tier;
  above a few hundred, decompose to parallel workers per logical section.

And the corollary for planning horizons: **a buffer counted in sprints is consumed in
time.** Read a dispatch-ready buffer as days of runway — count ÷ the trailing weekly
sprint rate — because a buffer of five at fifteen sprints a week is about two days.

Every dispatch spec declares a default effort level in its header. This is the baseline
for all tasks in the sprint. Individual tasks can override up or down.

### Format

```
Effort: Medium | Override: tasks #6, #8 → High
```

If all tasks share the same effort level, the override line is omitted:

```
Effort: Low
```

### Effort ↔ Model Tier Defaults

Effort and task tier are orthogonal but correlate. These defaults apply when effort
is not explicitly annotated on a task:

| Model Tier | Default Effort | Rationale |
|-----------|---------------|-----------|
| mechanical | Low | Mechanical tasks — pattern-match, no reasoning needed |
| bounded | Medium | Standard implementation — judgment within bounded scope |
| cross-cutting | High | Cross-system reasoning — multiple approaches, careful tracing |

**Only annotate effort when it differs from the model-tier default.** A `[bounded]` task
is implicitly `{medium}`. Write `[bounded] {high}` only when the task needs deeper
reasoning than bounded normally provides. This keeps the dispatch readable.

---

## Effort-Based Wave Splitting

If a sprint mixes effort levels significantly, **split into waves by effort** to avoid
paying max-effort prices for boilerplate work.

### Wave Structure

- **Wave A**: Low + Medium effort tasks (fast, cheap, mechanical + standard)
- **Wave B**: High + Max effort tasks (slow, expensive, analytical + critical)

### When to Split

Split when a sprint contains **3+ tasks at a higher effort tier than the sprint default**.
A single High task in an otherwise Medium sprint doesn't warrant splitting. But if
half the tasks need High and half need Low, split.

### This Is Additive

Effort-based wave splitting is additive to the existing wave-splitting rules (tool
budget ≤40, wall time ≤60 minutes). A sprint can be split for effort reasons even if
it fits within the tool and time budgets. The three splitting criteria are:

1. Tool budget exceeded → split
2. Wall time exceeded → split
3. Effort levels significantly mixed → split

If any criterion triggers, split.

---

## Anti-Rationalization

| What You'll Think | Why It's Wrong |
|---|---|
| "Everything should be Medium, it's the safe default" | Medium is a great default for standard work, but it underthinks hard problems and overthinks trivial ones. Both waste tokens. |
| "Max effort on everything ensures quality" | Max effort on a rename burns 10x tokens for zero quality improvement. Match effort to actual complexity. |
| "Low effort is fine, the agent can figure it out" | Low effort explicitly limits reasoning depth. Complex tasks at Low effort produce plausible-but-wrong output. |
| "I'll set effort during execution when I see the task" | Effort is a spec decision, not an execution decision. The spec author knows the task complexity. The implementation agent just executes. |
| "Effort doesn't matter, the task tier handles it" | The task tier says how wide the task reaches. Effort says how much deliberation to spend on it. The same bounded task run at `low` and at `high` produces materially different work. |
| "This sprint is all one effort level, no need to declare it" | Declare it anyway. The explicit declaration prevents drift and enables cost forecasting. |
| "Splitting by effort adds overhead, just run everything at High" | The cost difference between Low and High is ~5x per task. On a 10-task sprint with 6 Low tasks, that's wasting ~24x the tokens on those 6 tasks. |

---

## Runtime effort: the `/effort-levels` command

Effort declarations in the spec are **planning decisions**. The actual mechanism that
changes the deliberation budget at runtime is the host command:

```
/effort-levels [low | medium | high | max]
```

Run it inside the implementation agent's session before dispatching tasks at the
declared effort level. Without it, effort annotations in the spec are decorative —
the session will use whatever effort level happens to be active.

### How the implementation agent uses this

1. **At dispatch start:** the implementation agent reads the dispatch header's `Effort:` field and runs
   `/effort-levels [default]` to set the baseline for the sprint.

2. **Per-task override:** Before dispatching a task with an effort override (e.g.,
   `{max}`), it runs `/effort-levels [override]`. After the task completes, it
   reverts to the sprint default with `/effort-levels [default]`.

### Example Execution Sequence

```
Sprint header: Effort: Medium | Override: tasks #3, #7 → High, task #5 → Max

Execution:
  /effort-levels medium          ← set sprint default
  dispatch task #1               ← runs at medium (default)
  dispatch task #2               ← runs at medium (default)
  /effort-levels high            ← override for task #3
  dispatch task #3               ← runs at high
  /effort-levels medium          ← revert to default
  dispatch task #4               ← runs at medium (default)
  /effort-levels max             ← override for task #5
  dispatch task #5               ← runs at max
  /effort-levels medium          ← revert to default
  dispatch task #6               ← runs at medium (default)
  /effort-levels high            ← override for task #7
  dispatch task #7               ← runs at high
  /effort-levels medium          ← revert to default
```

### Important

- **The planner authors the specification.** Effort-level selection is a planner decision made
  during dispatch authoring — that's what this skill governs.
- **The implementation agent executes the specification.** It reads the effort
  declarations and runs the `/effort-levels` command at the right moments. It does not
  decide effort — it
  follows the spec.
- **If effort isn't changing, don't re-run the command.** Consecutive tasks at the
  same level don't need redundant `/effort-levels` calls.

---

## Spec Authoring Checklist

When authoring a dispatch spec, walk through these steps:

1. **Classify each task** using the Task Type Reference Table above
2. **Identify the sprint default** — the effort level that covers the majority of tasks
3. **Mark overrides** — tasks that need higher or lower effort than the default
4. **Check for wave-split triggers** — are 3+ tasks at a significantly different level?
5. **Declare in header** — `Effort: [Level] | Override: tasks #X, #Y → [Level]`
6. **Sanity check** — does the cost profile match the sprint's importance? A routine
   cleanup sprint at Max effort is waste. A mission-critical migration at Low is risk.
