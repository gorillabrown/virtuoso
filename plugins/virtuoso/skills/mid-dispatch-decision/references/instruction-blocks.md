Serves `mid-dispatch-decision` Step 6a: the formats of the implementation-agent instruction block.

# Implementation-Agent Instruction Blocks

The user pastes this block immediately. **Write in first person.** Keep it minimal: as short
as the implementation agent needs to act. Identifiers are appropriate here — dispatch IDs,
lesson and rule numbers, file paths, agent names — because the implementation agent knows
the codes. Name tasks, agents, files, metrics, and thresholds; "continue as you see fit" is
not an instruction.

When the decision changes what the implementation agent executes next (Types 3, 3a, 5), the
block flags: "Virtuoso task-plan reprint required after this change." When it changes scope
(Types 2, 3, 3a), size the changed tasks with the effort-levels Task Type Reference Table and
state every change in the task plan update. Every block opens with
`timing --dispatch <dispatch-id> --resume N` before the first action it directs.

## What each type's block carries

| Type | Fields |
|------|--------|
| 1a — Advance (Pre-Authorized) | Decision + constraints + why. Minimal — the spec already said what to do. |
| 1b — Advance (Planner-Originated) | Decision + direction + scope + constraints + why. Fuller than 1a: the implementation agent has no spec language to fall back on. |
| 2 — Advance with Narrowing | Decision + direction + what's narrowed + where deferred work goes (next dispatch, parking lot, dropped) + constraints. |
| 3 — Pivot Advance | Decision + what to skip + revised task plan (new task numbers, agent assignments, task tiers, effort levels, done-when) + constraints. |
| 3a — Revise Routing / Effort | Decision + which tasks change + new `[agent] {effort}` annotations. Task IDs and done-when unchanged. |
| 4 — Pivot Stop and Regroup | The stop instruction below, verbatim in substance. |
| 5 — Verify First | Decision + verification task (agent, what to check, done-when) + "pause remaining plan until verification lands, then come back for direction." |

## Conditional direction (when Step 2's rule fired)

Any per-type format below is wrapped in a check-then-act structure: the type's direction
becomes the action under the matching branch, and further branches enumerate the
alternatives.

```
**Decision:** Type [N] — [Name]

Before acting, verify [specific check]:
  - If [condition A]: proceed with [action A].
  - If [condition B]: proceed with [action B].
  - If neither / unclear: pause and report — I'll route the next decision
    from the planner.

[remaining instruction block fields...]
```

The branches must be exhaustive enough that the implementation agent does not have to invent
a third option. If the situation space is not enumerable, escalate to Type 5 (Verify First).

## Types 1a / 1b / 2

```
Here's my decision on the [pause point]:

**Decision:** Type [N] — [Name]

[Direction — 1-3 sentences. Name task numbers, agents, metrics.]

**Scope:** [Unchanged / narrowed — what and where deferred work goes]
**Constraints:** [Guardrails. "Do not X." "If Y, stop and ask."]
**Updated task plan:** [only if tasks changed]
**For the close-out:** [What to note]
**Why:** [1-2 sentences]
```

## Type 3 — Pivot Advance

```
Here's my decision — pivoting remaining work:

**Decision:** Type 3 — Pivot Advance

Replace remaining tasks with these:
  □ [N]. [agent]: [task] [model] {effort}
  □ [N+1]. [agent]: [task] [model] {effort}
  ...
**Done-when:** [revised criteria]
**Constraints:** [guardrails]
**For the close-out:** [scope change from original dispatch]
**Why:** [1-2 sentences]
```

## Type 3a — Revise Routing / Effort

```
Here's my decision — revising agent assignments:

**Decision:** Type 3a — Revise Routing

Change these task annotations (plan and done-when unchanged):
  Task #N: [old agent/effort] → [new agent/effort]
  Task #M: [old agent/effort] → [new agent/effort]
**Why:** [1-2 sentences]
```

## Type 4 — Pivot Stop

```
Stop the dispatch. Preserve completed work from tasks #1-N.
Cancel remaining tasks. I'll send a new dispatch from the planning side.

**For the close-out:** [what the partial close-out should capture]
**Why:** [1-2 sentences]
```

## Type 5 — Verify First

```
Here's my decision — verify before committing to a direction:

**Decision:** Type 5 — Verify First

Run this verification task:
  □ [agent]: [what to check] [model] {effort}
  **Done-when:** [verification criteria]

Pause remaining tasks until verification lands. Then come back for direction
on the strategic decision.

**Why:** [1-2 sentences explaining the measurement suspicion]
```

## Bundled pauses

One instruction block at the end, listing every decision's instructions in execution order.

The block's "Why" and "For the close-out" fields, with the Step 6b amendment, are the
permanent decision trail: a future planner session doing the close-out must be able to
reconstruct the reasoning from them alone.

Return to SKILL.md Step 6b.
